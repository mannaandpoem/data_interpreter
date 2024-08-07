import json
from pathlib import Path
from typing import Dict, List, Literal, Union

from metagpt.const import DEFAULT_WORKSPACE_ROOT, METAGPT_ROOT
from metagpt.logs import logger
from metagpt.schema import AIMessage, Message
from metagpt.utils.common import CodeParser
from pydantic import Field

from di_project.actions.write_analysis_code import WriteAnalysisCode
from di_project.prompts.swe_agent import (
    IMPORTANT_TIPS,
    MINIMAL_EXAMPLE,
    NEXT_STEP_TEMPLATE,
    REFLECTION_TRAJ_PROMPT,
    SUMMARY_PROMPT,
    SWE_AGENT_SYSTEM_TEMPLATE,
)
from di_project.roles.data_interpreter import DataInterpreter
from di_project.roles.swe_env import SWEEnv
from di_project.schema import Task, TaskResult
from di_project.tools.libs.terminal import Bash
from di_project.tools.swe_agent_commands.swe_agent_utils import (
    extract_patch,
    parse_thought_and_action,
)
from di_project.tools.tool_recommend import ToolRecommender
from di_project.utils.path_utils import converted_path

# Specify by yourself
TEST_REPO_DIR = METAGPT_ROOT.parent / "data" / "test_repo"
DATA_DIR = METAGPT_ROOT.parent / "data/hugging_face"
SWE_CMD_WORK_DIR = DEFAULT_WORKSPACE_ROOT / "swe_agent_workdir"

CONSECUTIVE_LIMIT = 3
EDIT_CONSECUTIVE_LIMIT = 3
WINDOW_SIZE = 100
TEST_REPO_DIR.mkdir(parents=True, exist_ok=True)
SWE_CMD_WORK_DIR.mkdir(parents=True, exist_ok=True)

EDIT_DIVIDER = "This is how your edit would have looked if applied"
EDIT_FAILURE = (
    "Your proposed edit has introduced new syntax error(s). Please understand the fixes and retry your edit command."
)
BUFFER = 5


class TrajectoryNode:
    def __init__(self, observation, action, thought):
        self.thought = thought
        self.action = action
        self.observation = observation

    def to_json(self):
        return {
            "thought": self.thought,
            "action": self.action,
            "observation": self.observation,
        }

    def __str__(self):
        return f"TrajectoryNode:\n{json.dumps(self.to_json(), indent=2)}"

    def __repr__(self):
        return self.__str__()


class SWEAgent(DataInterpreter):
    name: str = "Swen"
    auto_run: bool = True
    use_plan: bool = True
    use_reflection: bool = False
    use_experience: bool = False
    tools: list[str] = ["Bash"]
    tool_recommender: ToolRecommender = None
    max_react_loop: int = 30  # used for react mode
    react_mode: Literal["plan_and_act", "react"] = "react"
    user_requirement: str = ""
    _bash_window_size: int = WINDOW_SIZE
    _instruction: str = NEXT_STEP_TEMPLATE
    system_msg: List[str] = [SWE_AGENT_SYSTEM_TEMPLATE.format(WINDOW=100)]
    swe_env: SWEEnv = Field(default_factory=SWEEnv, exclude=True)
    # Path to the repository where the code is located
    repo_path: Path = SWE_CMD_WORK_DIR / "temp"
    # Repository information
    repo_info: Dict[str, str] = {}
    # Current instance id
    cur_instance_id: str = ""
    # Trajectory of the agent
    trajectory: List[TrajectoryNode] = []
    # The number of iterations for the agent to retry
    max_attempt: int = 2

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.swe_result_dir = SWE_CMD_WORK_DIR / f"result_{self.config.llm.model}"
        self.swe_result_dir.mkdir(parents=True, exist_ok=True)
        self.swe_env.terminal = Bash()
        self.set_actions([WriteAnalysisCode])  # Need Fix
        self._set_state(0)
        self._set_react_mode(
            react_mode=self.react_mode,
            max_react_loop=self.max_react_loop,
            auto_run=self.auto_run,
        )

    async def _react(self) -> Message:
        """Entry to one of three strategies by which Role reacts to the observed Message"""
        rsp = None
        reflection_plan = ""
        attempt = 0

        while self.cur_instance_id:  # it can retry on current instance
            # Initialize the user requirement and issue
            self._init_task(plan=reflection_plan)
            attempt += 1
            rsp = await self._react_on_task()

            # Check if the user has submitted the changes to the repository
            if attempt < self.max_attempt and rsp.content.startswith("submit"):
                # Reflect on the trajectory
                reflection_plan = await self.reflect_traj(code_change=self.swe_env.terminal.run("git diff"))
            else:
                self.cur_instance_id = ""
            # Clear the working memory and trajectory
            self._clear_for_next_instance()

        return rsp

    async def _react_on_task(self, current_task: Task = None) -> Union[Message, TaskResult]:
        actions_taken = 0
        rsp = AIMessage(content="No actions taken yet")  # will be overwritten after Role _act
        submit_flag = True

        while actions_taken < self.rc.max_react_loop:
            # think
            has_todo = await self._think()
            if not has_todo:
                if self.cur_instance_id:
                    # make it to run other instance
                    submit_flag = True
                    self.working_memory.clear()
                    continue
                else:
                    break

            # act
            logger.debug(f"{self._setting}: {self.rc.state=}, will do {self.rc.todo}")
            rsp = await self._act()

            # Check if the user has submitted the changes to the repository
            if isinstance(rsp, Message):
                if rsp.content.startswith("submit"):
                    submit_flag = True
                    break
                else:
                    submit_flag = False
            elif isinstance(rsp, TaskResult):
                if rsp.result.startswith("submit"):
                    submit_flag = True
                    break
                else:
                    submit_flag = False

            actions_taken += 1

        # Ensure final save operations if loop ends
        if not submit_flag:
            logger.info("Submitting the changes to the repository.")
            await self.submit()

        return rsp

    def _clear_for_next_instance(self):
        self.working_memory.clear()
        self.trajectory.clear()

    async def _think(self) -> bool:
        context = self.working_memory.get()
        if not context:
            self._set_state(0)
            return True

        # Check if the current instance_id is set
        if not self.rc.todo or not self.cur_instance_id:
            self._set_state(-1)
            return False

        need_action = True
        self._set_state(0)

        return need_action

    async def _act(self):
        """Perform an action in the environment"""
        messages = self.working_memory.get()
        context = ""
        for i, message in enumerate(messages, 1):
            message = str(message)
            role = message.split(":")[0]
            content = ":".join(message.split(":")[1:])
            context += f"{role} - Round {i // 2}: {content}\n\n"

        logger.info(f"Current terminal directory: {self.swe_env.terminal.run('pwd')}")

        # Calculate the remaining iterations
        remaining_iterations = self.rc.max_react_loop - len(self.trajectory) // 2
        bash_state = json.loads(self.swe_env.terminal.run("state"))

        prompt = self._instruction.format(
            user_requirement_and_issue=self.user_requirement_and_issue,
            context=context if context else None,
            examples=MINIMAL_EXAMPLE,
            important_tips=IMPORTANT_TIPS,
            remaining_iterations=remaining_iterations,
            **bash_state,
        )
        response = await self.llm.aask(prompt, self.system_msg)
        self.add_to_working_memory(f"\nThought and Action(bash_command):\n{response}", "assistant")
        # Parse the thought and action
        thought, action = parse_thought_and_action(response)
        logger.info(f"Action: {action}")

        # If submit is in the output, finish the task
        if action in ["submit", "exit"]:
            observation = "submit successful."
            await self.submit()
        else:
            # Execute the action
            observation = self.swe_env.step(action, bash_state, self.is_stuck(action))
        logger.info(observation)
        self.add_to_working_memory(observation, "user")
        self.trajectory.append(TrajectoryNode(thought=thought, action=action, observation=observation))
        if self.react_mode == "react":
            return Message(content=observation, role="user")
        else:
            return TaskResult(code=action, result=observation, is_success=True)

    async def _handle_submit_action(self, thought, action):
        """Handle the submit action"""
        observation = "submit successful."
        self.add_to_working_memory(observation, "user")
        self.trajectory.append(TrajectoryNode(thought=thought, action=action, observation=observation))
        await self.submit()
        # return Message(content=observation, role="user")
        return observation

    def add_to_working_memory(self, content, role, use_memory_window=False, memory_window=10) -> None:
        """Add the message to the working memory"""
        self.working_memory.add(Message(content=content, role=role))
        if self.working_memory.count() > memory_window and use_memory_window:
            self.working_memory.storage.pop()

    async def submit(self):
        """Submit the modified file by git in the terminal."""
        try:
            repo_path = converted_path(self.repo_path)
            self.swe_env.terminal.run(f"cd {repo_path}")
            # Generate patch by git diff
            diff_output = self.swe_env.terminal.run("git diff")
            clear_diff = extract_patch(diff_output)
            logger.info(f"Diff output: {clear_diff}")

            # Add the patch and exit status to the repo_info
            self.repo_info["submission"] = clear_diff
            self.repo_info["exit_status"] = "submitted"
        except Exception as e:
            logger.error(f"Error during submission: {e}")

    async def summarize_traj(self, trajectory, code_change=""):
        prompt = SUMMARY_PROMPT.format(trajectory=trajectory, code_change=code_change)
        response = await self.llm.aask(prompt, self.system_msg)
        summary_response = json.loads(CodeParser.parse_code(block=None, text=response))
        summary = summary_response.get("summary", "")
        logger.info(f"Summary of the trajectory:\n{summary}")
        # Clear the working memory
        self.working_memory.clear()
        return summary

    async def reflect_traj(self, code_change=""):
        trajectory_actions = "\n->\n".join([node.action for node in self.trajectory])
        prompt = REFLECTION_TRAJ_PROMPT.format(trajectory=trajectory_actions, code_change=code_change)
        response = await self.llm.aask(prompt, self.system_msg)
        response_dict = json.loads(CodeParser.parse_code(block=None, text=response))
        reflect_plan = response_dict.get("plan", "")
        logger.info(f"Reflection of the trajectory:\n{response}")
        return reflect_plan

    def _init_task(self, plan=""):
        # Get the issue description
        self.user_requirement_and_issue = f"{self.user_requirement}\n## Plan\n{plan}" if plan else self.user_requirement
        logger.info(f"User Requirement:\n{self.user_requirement_and_issue}")
        # Add the user requirement and issue to the working memory and trajectory
        repo_path = converted_path(self.repo_path)
        self.swe_env.terminal.run(f"cd {repo_path}")
        self.working_memory.add(Message(content=f'\nObservation:\nbash_command: "cd {repo_path}"', role="user"))
        self.trajectory.append(TrajectoryNode(thought="", action="", observation=self.user_requirement_and_issue))

    def is_stuck(self, action):
        last_actions = self.trajectory[-CONSECUTIVE_LIMIT:] if len(self.trajectory) >= CONSECUTIVE_LIMIT else []
        action_prefix = action.split(" ")[0]
        flag = False
        if len(last_actions) >= CONSECUTIVE_LIMIT and all(n.action.startswith(action_prefix) for n in last_actions):
            # Pop action to avoid the consecutive edit actions
            for _ in range(CONSECUTIVE_LIMIT - 1):
                self.working_memory.storage.pop()
            flag = True

        return flag

    async def _plan_and_act(self) -> Message:
        # create initial plan and update it until confirmation
        goal = self.rc.memory.get()[-1].content  # retreive latest user requirement
        await self.planner.update_plan(goal=goal)

        # take on tasks until all finished
        while self.planner.current_task:
            task = self.planner.current_task
            logger.info(f"ready to take on task {task}")
            self._init_task(plan=self.planner.get_plan_status())
            # take on current task
            task_result = await self._react_on_task(task)

            # process the result, such as reviewing, confirming, plan updating
            await self.planner.process_task_result(task_result)

        rsp = self.planner.get_useful_memories()[0]  # return the completed plan as a response

        self.rc.memory.add(rsp)  # add to persistent memory
        return rsp

    @property
    def working_memory(self):
        return self.rc.working_memory
