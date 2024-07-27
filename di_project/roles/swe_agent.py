#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024/05/13
@Author  : mannaandpoem
@File    : swe_agent.py
"""
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Literal, Optional, Dict, List

from datasets import load_dataset
from github.PullRequest import PullRequest
from pandas import DataFrame

from metagpt.const import DEFAULT_WORKSPACE_ROOT, METAGPT_ROOT, get_metagpt_package_root
from metagpt.logs import logger
from metagpt.roles.di.data_interpreter import DataInterpreter
from pydantic import Field

from di_project.roles.env_manager import EnvManager
from metagpt.schema import AIMessage, Message
from di_project.tools.libs.git import git_create_pull, git_push
from di_project.tools.libs.terminal import Terminal, Bash

# from metagpt.tools.swe_agent_commands.prompt import IMPORTANT_TIPS_V2 as IMPORTANT_TIPS
# from metagpt.tools.swe_agent_commands.prompt import EXAMPLE_V2 as EXAMPLE
from di_project.prompts.prompt import (
    IMPORTANT_TIPS,
    INSTANCE_TEMPLATE,
    INVALID_INPUT_MESSAGE,
    NEXT_STEP_NO_OUTPUT_TEMPLATE,
    NEXT_STEP_TEMPLATE,
    ONLY_LOCATE_ISSUE_THINK_PROMPT,
    OUTPUT_FORMAT,
    REFINE_EDIT_PROMPT,
    REFINE_EXAMPLES,
    SUMMARY_PROMPT,
    SWE_AGENT_SYSTEM_TEMPLATE, REPRODUCING_REQUIREMENT, TESTING_REQUIREMENT, TESTING_EXAMPLE, REPRODUCING_EXAMPLE,
    MINIMAL_EXAMPLE, SEPARATOR, TIP_FOR_REPRODUCING, TIP_FOR_TESTING,
)
from di_project.tools.swe_agent_commands.swe_agent_utils import (
    extract_patch,
    extract_repo_identifier,
    filter_and_get_repo_info,
    get_github_issue_description,
    parse_thought_and_action, load_hf_dataset, view_file_with_line_numbers_and_format,
)
from metagpt.utils.common import CodeParser
from di_project.utils.path_utils import converted_path, find_exist_repo_path_and_cp, converted_back_to_windows

# Specify by yourself
TEST_REPO_DIR = METAGPT_ROOT.parent / "data" / "test_repo"
DATA_DIR = METAGPT_ROOT.parent / "data/hugging_face"
SWE_CMD_WORK_DIR = DEFAULT_WORKSPACE_ROOT / "swe_agent_workdir"

CONSECUTIVE_LIMIT = 3
EDIT_CONSECUTIVE_LIMIT = 3

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
        return {"thought": self.thought, "action": self.action, "observation": self.observation}

    def __str__(self):
        return f"TrajectoryNode:\n{json.dumps(self.to_json(), indent=2)}"

    def __repr__(self):
        return self.__str__()


class SWEAgent(DataInterpreter):
    name: str = "Swen"
    profile: str = "Issue Solver"
    goal: str = "Resolve GitHub issue"
    max_react_loop: int = 30  # used for react mode
    react_mode: Literal["plan_and_act", "react"] = "react"
    user_requirement: str = ""
    _instruction: str = NEXT_STEP_TEMPLATE

    # The terminal to run the bash commands
    terminal: Bash = Field(default_factory=Bash, exclude=True)
    # Bash window is the number of lines that the bash command prompt can display
    _bash_window_size: int = 100
    # The memory window to restrict the number of messages in the working memory
    use_memory_window: bool = False
    memory_window: int = 4
    # Fetch the base commit and issue description from the dataset
    fetch_from_dataset: bool = False
    # git_push_and_create_pr_tag are used to determine if to push the changes to the repo and create a pull request
    git_push_and_create_pr_tag: bool = False
    # The issue description
    issue: str = ""
    # Path to the repository where the code is located
    repo_path: Path = SWE_CMD_WORK_DIR / "temp"
    # repo_info includes the base commit, issue description, repo identifier and hints text
    repo_info: Dict[str, Dict[str, str]] = {}
    # The instance_id of the SWE-bench dataset
    instance_ids: Optional[List[str]] = []
    cur_instance_id: str = ""
    # Trajectory of the agent
    trajectory: List[TrajectoryNode] = []
    dataset_path: str = ""
    # dataset is the filtered dataset based on the instance_ids
    dataset: Optional[DataFrame] = None
    exp_name: str = ""
    # Determine if the agent needs summarizing the trajectory
    need_summary: bool = False
    # Determine if the agent needs reproducing
    need_reproducing: bool = False
    # Determine if the agent needs testing
    need_testing: bool = False
    # Determine if the agent needs to ensemble the results
    need_ensemble: bool = False
    # The number of iterations for the ensemble
    ensemble_iterations: int = 2
    # If submit fails, can retry submission once
    can_retry_submission: bool = False

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        bash_window_size = self.terminal.run("echo $WINDOW").strip()
        self._bash_window_size = int(bash_window_size) if bash_window_size else self._bash_window_size
        self.llm.system_prompt = SWE_AGENT_SYSTEM_TEMPLATE.format(
            WINDOW=self._bash_window_size, output_format=OUTPUT_FORMAT
        )
        # bug fix
        self.user_requirement_and_issue = self.user_requirement
        # Based on the condition of need_reproducing and need_testing, adjust the user requirement
        if self.need_reproducing and self.need_testing:
            self.user_requirement += REPRODUCING_REQUIREMENT + TESTING_REQUIREMENT
        elif self.need_reproducing:
            self.user_requirement = REPRODUCING_REQUIREMENT
        elif self.need_testing:
            self.user_requirement += TESTING_REQUIREMENT

        self.swe_result_dir = (
            SWE_CMD_WORK_DIR / f"result_{self.config.llm.model}" / self.exp_name
        )  # for different process
        self.swe_result_dir.mkdir(parents=True, exist_ok=True)

        if self.fetch_from_dataset:
            logger.info(f"loading {self.dataset_path} dataset")
            dataset = load_dataset(self.dataset_path)

            # Filter the dataset based on the instance_ids
            self.dataset, self.repo_info = filter_and_get_repo_info(
                dataset["test"].to_pandas(), "instance_id", self.swe_result_dir, self.instance_ids
            )
            # Update the instance_ids with the filtered dataset
            self.instance_ids = self.dataset["instance_id"].tolist()
            logger.info(f"Instance IDs: {self.instance_ids}")
            # assert self.instance_ids
        self.env_manager: EnvManager
        self.edit_counter = 0
        self.last_edit_action = ""
        self.last_open_file = ""

    async def react(self) -> Message:
        """Entry to one of three strategies by which Role reacts to the observed Message"""
        rsp = None
        copy_can_retry_submission = self.can_retry_submission
        while self.instance_ids:
            # Initialize the next instance
            self._initialize_next_instance()

            all_traj = []
            all_patches = []
            if self.need_ensemble:
                # _react will be called multiple times by different ensemble parameters
                for ensemble_index in range(self.ensemble_iterations):
                    with self.ensemble_parameters(ensemble_index):
                        # Initialize the user requirement and issue
                        self._init_user_requirement_and_issue()
                        rsp = await self._react()
                        # Record the trajectory of each ensemble
                        all_traj.append(self.trajectory)
                        all_patches.append(self.repo_info[self.cur_instance_id]["submission"])
                        self._clear_for_next_instance()
                # TODO: Select the best trajectory
                # TODO: Save the best trajectory and the corresponding patch, then remove the others
            else:
                # Initialize the user requirement and issue
                self._init_user_requirement_and_issue()
                rsp = await self._react()
                all_traj.append(self.trajectory)
                all_patches.append(self.repo_info[self.cur_instance_id]["submission"])

            # Check if the user has submitted the changes to the repository, if so, try again
            if self.can_retry_submission and not all(all_patches):
                logger.error("Model patch is empty, please try once again.")
                # Summary the trajectory
                if self.need_summary:
                    summaries = []
                    for trajectory, model_patch in zip(all_traj, all_patches):
                        traj = "\n".join([str(node) for node in trajectory])
                        summary = await self.summarize_traj(traj, model_patch)
                        summaries.append(summary)

                    final_summary = "\n\n".join(
                        [f"Summary for ensemble {i + 1}:\n{summary}" for i, summary in enumerate(summaries)]
                    )

                    self.add_to_working_memory(
                        f"""\nSummary of the all complete trajectory as follows:\n{final_summary}\n
                        You need to review and fix the issues based on the summary.""",
                        "user",
                    )

                # Try again this instance
                self.instance_ids.insert(0, self.cur_instance_id)
                self.can_retry_submission = False
            else:
                # Clear the can_retry_submission flag
                self.can_retry_submission = copy_can_retry_submission

            # Clear the working memory, trajectory and so on for the next instance
            self._clear_for_next_instance()

        logger.info("All instances have been processed.")
        return rsp

    async def _react(self) -> Message:
        actions_taken = 0
        rsp = AIMessage(content="No actions taken yet")  # will be overwritten after Role _act
        submit_flag = True

        while actions_taken < self.rc.max_react_loop:
            # think
            has_todo = await self._think()
            if not has_todo:
                if self.only_locate_issue and self.instance_ids:
                    # make it to run other instance_ids
                    submit_flag = True
                    self.working_memory.clear()
                    continue
                else:
                    break

            # act
            logger.debug(f"{self._setting}: {self.rc.state=}, will do {self.rc.todo}")
            rsp = await self._act()

            # Check if the user has submitted the changes to the repository
            if rsp.content.startswith("submit"):
                submit_flag = True
                break
            else:
                submit_flag = False

            actions_taken += 1

        # Ensure final save operations if loop ends
        if not submit_flag:
            await self.save_traj_and_preds()

        return rsp

    def _initialize_next_instance(self):
        # Initialize the next instance from the dataset
        self.cur_instance_id = self.instance_ids.pop(0)
        logger.info(f"Resetting the virtual environment for the current instance: {self.cur_instance_id}")
        self._reset_env()

    def _init_user_requirement_and_issue(self):
        # Get the issue description from repo_info
        if self.repo_info:
            self.issue = self.repo_info[self.cur_instance_id]["issue_description"]
            self.user_requirement_and_issue = INSTANCE_TEMPLATE.format(
                user_requirement=self.user_requirement,
                issue=self.issue,
                hints_text=self.repo_info[self.cur_instance_id]["hints_text"],
            )
        # If the issue description is not provided, preprocess the repo information from the issue link of content
        elif not self.issue:
            self.user_requirement_and_issue = INSTANCE_TEMPLATE.format(
                user_requirement=self.user_requirement,
                issue=self.issue,
                hints_text=self.repo_info[self.cur_instance_id]["hints_text"],
            )
        logger.info(f"User Requirement:\n{self.user_requirement_and_issue}")

        # Add the user requirement and issue to the working memory and trajectory
        repo_path = converted_path(self.repo_path)
        self.terminal.run(f"cd {repo_path}")
        self.working_memory.add(Message(content=f'\nObservation:\nbash_command: "cd {repo_path}"', role="user"))
        self.trajectory.append(TrajectoryNode(thought="", action="", observation=self.user_requirement_and_issue))

    def _clear_for_next_instance(self):
        self.working_memory.clear()
        self.trajectory.clear()
        self._bash_window_size = 100

    async def save_traj_and_preds(self):
        logger.info("Submitting the changes to the repository.")
        await self.submit()
        if self.repo_info[self.cur_instance_id]["submission"]:
            self.repo_info[self.cur_instance_id]["exit_status"] = "submitted"
        self.save_trajectory()
        self.save_predictions()

    async def _think(self) -> bool:
        """Useful in 'react' mode."""
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

        logger.info(f"Current terminal directory: {self.terminal.run('pwd')}")

        # Calculate the remaining iterations
        remaining_iterations = self.rc.max_react_loop - len(self.trajectory) // 2

        state_output = self.terminal.run("state")
        bash_state = json.loads(state_output)

        examples = self._adjust_examples()
        important_tips = self._adjust_important_tips()
        prompt = self._instruction.format(
            user_requirement_and_issue=self.user_requirement_and_issue,
            context=context if context else None,
            WINDOW=self._bash_window_size,
            examples=examples,
            important_tips=important_tips,
            remaining_iterations=remaining_iterations,
            **bash_state,
        )

        response = await self.llm.aask(prompt)

        self.add_to_working_memory(f"\nThought and Action(bash_command):\n{response}", "assistant")

        # Parse the thought and action
        thought, action = parse_thought_and_action(response)

        # If submit is in the output, finish the task
        if action in ["submit", "exit"]:
            return await self._handle_submit_action(thought, action)

        logger.info(f"Action: {action}")
        # Execute the action
        observation = await self._execute_bash_action(action, bash_state)
        logger.info(observation)

        self.add_to_working_memory(observation, "user")
        self.trajectory.append(TrajectoryNode(thought=thought, action=action, observation=observation))

        return Message(content=observation, role="user")

    async def _handle_submit_action(self, thought, action):
        """Handle the submit action"""
        observation = "submit successful."
        self.add_to_working_memory(observation, "user")
        self.trajectory.append(TrajectoryNode(thought=thought, action=action, observation=observation))

        await self.save_traj_and_preds()

        return Message(content=observation, role="user")

    async def _execute_bash_action(self, action, bash_state, max_obs_len=6000):
        """Execute the given action and return the observation"""
        # If the action is invalid
        if not action:
            return INVALID_INPUT_MESSAGE

        # Execute the action
        if os.name == "nt":
            if action.startswith("python ") or "python " in action:
                python_executor = converted_path(self.env_manager.env_python_executor)
                action = action.replace("python ", f"{python_executor} ")
                logger.info(f"Replace action cmd {action}")

            elif action.startswith("pytest"):
                if "edit" in action or "open" in action:
                    action = action
                else:
                    action = action.replace("pytest", f"conda activate {self.env_manager.env_name} && pytest")
                logger.info(f"Replace action cmd {action}")

            elif action.startswith("pip "):
                pip_executor = converted_path(self.env_manager.env_pip_executor)
                action = action.replace("pip ", f"{pip_executor} ")
            observation = self.terminal.run(action)
        else:
            if action.startswith(("python", "pytest", "pip")):
                env_name = self.repo_info[self.cur_instance_id]["env_name"]
                # Avoid env lacking pytest package
                check_pytest_exist = self.terminal.execute_in_conda_env("pip list | grep pytest", env_name)
                if not check_pytest_exist:
                    install_cmd = "pip install pytest --trusted-host pypi.org --trusted-host pypi.python.org"
                    logger.info(f"Install pytest ...\n{self.terminal.execute_in_conda_env(install_cmd, env_name)}")
                # self.terminal.execute_in_conda_env("pip install pytest", env_name)
                observation = self.terminal.execute_in_conda_env(action, env_name)
            else:
                observation = self.terminal.run(action)

        # Check for a configurable number of consecutive edit actions in the trajectory
        last_actions = self.trajectory[-CONSECUTIVE_LIMIT:] if len(self.trajectory) >= CONSECUTIVE_LIMIT else []
        action_prefix = action.split(" ")[0]
        if len(last_actions) >= CONSECUTIVE_LIMIT and all(n.action.startswith(action_prefix) for n in last_actions):
            # Pop action to avoid the consecutive edit actions
            for _ in range(CONSECUTIVE_LIMIT - 1):
                self.working_memory.pop()

            edit_error_rst = observation.split(EDIT_DIVIDER)[0].strip()
            if action.startswith("edit") and edit_error_rst:
                observation = f"""{edit_error_rst}\nIMPORTANT: {EDIT_CONSECUTIVE_LIMIT} consecutive `edit` actions 
                are **not allowed**. Based on the recent error information, modify your actions accordingly instead 
                of repeating the previous command. For instance, use goto to jump to the specified line."""
            else:
                consecutive_action = action.split(" ")[0]
                observation = f"""{observation}\nIMPORTANT: {CONSECUTIVE_LIMIT} consecutive `{consecutive_action}` bash 
                command are **not allowed**. Please use other bash commands to fix the bug."""

            # Summary the previous actions and clear the working memory
            if self.need_summary:
                trajectory = "\n".join([str(node) for node in self.trajectory])
                summary = await self.summarize_traj(trajectory, code_change=self.terminal.run("git diff"))
                # Add summary to the observation
                observation = f"{observation}\n\nSummary for the previous actions:\n{summary}"

        # No output from the action
        if not observation:
            observation = NEXT_STEP_NO_OUTPUT_TEMPLATE.format(**bash_state)

        if len(observation) <= max_obs_len:
            return f"Observation:\n{observation}"
        # Truncate the observation if it is too long
        else:
            half_len = max_obs_len // 2
            return f"Observation:\n{observation[:half_len]}...\n[truncated due to length]\n...{observation[-half_len:]}"

    def save_trajectory(self):
        traj_path = self.swe_result_dir / f"{self.cur_instance_id}.traj"

        # Check if the traj_path already exists
        index = 1
        while traj_path.exists():
            traj_path = self.swe_result_dir / f"{self.cur_instance_id}_{index}.traj"
            index += 1

        # Converts the entire trajectory list to JSON.
        trajectory_list = [node.to_json() for node in self.trajectory]

        # Save the trajectory to a JSON file
        log_dict = {
            "trajectory": trajectory_list,
            "info": self.repo_info[self.cur_instance_id],
        }
        with open(traj_path, "w") as f:
            json.dump(log_dict, f, indent=2)

        trajectory_actions = "\n->\n".join([node.action for node in self.trajectory])
        logger.info(f"Actions of trajectory:\n{trajectory_actions}")
        logger.info(f"Saved trajectory of {self.cur_instance_id} to {str(traj_path)}")

    def save_predictions(self):
        output_file = self.swe_result_dir / "all_preds.jsonl"
        datum = self.dataset.set_index("instance_id").loc[self.cur_instance_id].to_dict()
        datum["instance_id"] = self.cur_instance_id
        datum["model_name_or_path"] = self.config.llm.model
        datum["model_patch"] = self.repo_info[self.cur_instance_id]["submission"]

        logger.info(f"Preparing to save predictions to {output_file}")

        # Save the predictions to a JSONL file
        with open(output_file, "a+") as fp:
            print(json.dumps(datum), file=fp, flush=True)

        logger.info(f"Saved prediction of {self.cur_instance_id} to {output_file}")

    def add_to_working_memory(self, content, role, use_memory_window=False) -> None:
        """Add the message to the working memory"""
        self.working_memory.add(Message(content=content, role=role))
        if self.working_memory.count() > self.memory_window and use_memory_window:
            self.working_memory.pop(0)

    async def submit(self):
        """Submit the modified file by git in the terminal."""
        try:
            repo_path = converted_path(self.repo_path)
            self.terminal.run(f"cd {repo_path}")
            # Generate patch by git diff
            diff_output = self.terminal.run("git diff")
            clear_diff = extract_patch(diff_output)
            logger.info(f"Diff output: {clear_diff}")

            # Add the patch and exit status to the repo_info
            self.repo_info[self.cur_instance_id]["submission"] = clear_diff

            if self.git_push_and_create_pr_tag:
                commit_message = "Fix the bug in the code"
                # Handle the commit and push changes to the repository
                self._handle_commit(commit_message)
                # Create and switch to a new branch
                await self._handle_push_and_create_pr(commit_message)
        except Exception as e:
            logger.error(f"Error during submission: {e}")

    def _handle_commit(self, commit_message):
        # Change to the repository path and add all files to staging
        add_output = self.terminal.run("git add .")
        logger.info(f"Add output: {add_output}")

        # Commit the changes with a specific message
        commit_command = f'git commit -m "{commit_message}"'
        commit_output = self.terminal.run(commit_command)
        logger.info(f"Commit output: {commit_output}")

    async def _handle_push_and_create_pr(self, commit_message):
        """Handle pushing changes and creating a pull request."""
        new_branch = "bugfix-branch"
        checkout_command = f"cd {self.repo_path} && git checkout -b {new_branch}"
        checkout_output = self.terminal.run(checkout_command)
        logger.info(f"Checkout output: {checkout_output}")

        # Push the changes to the new branch using git_push
        access_token = os.getenv("GITHUB_TOKEN")
        branch = await git_push(
            local_path=self.repo_path, access_token=access_token, comments=commit_message, new_branch=new_branch
        )
        logger.info(f"Pushed to branch: {branch.head}")

        # Create a pull request using git_create_pull
        pull_request = await git_create_pull(
            base=branch.base,
            head=branch.head,
            base_repo_name=branch.repo_name,
            access_token=access_token,
            title="Fix the bug in the code",
            body="This pull request fixes the bug in the code.",
        )
        if isinstance(pull_request, PullRequest):
            logger.info(f"Created pull request: {pull_request}")
        if isinstance(pull_request, str):
            logger.info(f"Visit this url to create a new pull request: '{pull_request}'")

    def _preprocess_repo_with_link(self, content: str) -> None:
        """Preprocess the repo information from the Github issue link."""
        repo_identifier = extract_repo_identifier(content)

        if repo_identifier:
            self.clone_and_checkout_repo(repo_identifier)
            owner, repo_name = repo_identifier.split("/")

            # todo: Extract issue URL, may need to modify
            issue_url_match = re.search(r"https://github\.com/[^/]+/[^/]+/issues/\d+", content)
            if issue_url_match:
                issue_url = issue_url_match.group(0)
                issue_number = int(issue_url.split("/")[-1])
                self.issue = get_github_issue_description(owner, repo_name, issue_number)

        repo_path = converted_path(self.repo_path)
        self.terminal.run(f"cd {repo_path}")

    def clone_and_checkout_repo(self, repo_identifier: str = "", base_commit: str = "") -> None:
        if base_commit:
            # self.repo_path = os.path.join(TEST_REPO_DIR.as_posix(), self.repo_info[self.cur_instance_id]["env_name"])
            self.repo_path = TEST_REPO_DIR / self.repo_info[self.cur_instance_id]["env_name"]
        else:
            # self.repo_path = os.path.join(TEST_REPO_DIR.as_posix(), repo_identifier.split("/")[-1])
            self.repo_path = TEST_REPO_DIR / repo_identifier.split("/")[-1]

        clone_command = f"git clone 'https://github.com/{repo_identifier}.git' {self.repo_path}"

        repo_path = converted_path(self.repo_path)

        checkout_command = f"cd {repo_path} && git checkout -f {base_commit}" if base_commit else ""

        if not self.repo_path.exists() or (not any(self.repo_path.rglob("*.py"))):
            # re-use an existed same repo_name repo
            new_dest_path = find_exist_repo_path_and_cp(self.repo_path)
            if not new_dest_path:
                clone_result = self.terminal.run(clone_command)
                logger.info(clone_result)
        else:
            logger.info(f"using a existing repo path: {self.repo_path}")
        checkout_result = self.terminal.run(checkout_command)
        logger.info(checkout_result)

    def _reset_env(self) -> None:
        """Reset the environment."""
        env_name = self.repo_info[self.cur_instance_id]["env_name"]

        repo_name = self.repo_info[self.cur_instance_id]["repo"].split("/")[-1]

        # preprocess_repo will clone the repo and checkout the base commit
        # If the repo information is provided, preprocess the repo information
        logger.info("Starting to preprocess the repo information.")
        if self.repo_info:
            self.clone_and_checkout_repo(
                repo_identifier=self.repo_info[self.cur_instance_id]["repo"],
                base_commit=self.repo_info[self.cur_instance_id]["base_commit"],
            )
        # If the issue description is not provided, preprocess the repo information from the issue link of content
        elif not self.issue:
            self._preprocess_repo_with_link(self.user_requirement)

        instance = self.dataset.set_index("instance_id").loc[self.cur_instance_id].to_dict()
        # Create the environment manager
        self.env_manager = EnvManager(
            env_name=env_name, repo_path=str(self.repo_path), instance=instance, repo_name=repo_name
        )
        self.env_manager.create_env()

    @property
    def bash_window_size(self):
        return self._bash_window_size

    @bash_window_size.setter
    def bash_window_size(self, value):
        self.terminal.run(f"export WINDOW={value}")
        self._bash_window_size = value

    def _adjust_examples(self):
        if self.need_reproducing and self.need_testing:
            examples = [TESTING_EXAMPLE, REPRODUCING_EXAMPLE, MINIMAL_EXAMPLE]
        elif self.need_reproducing:
            examples = [REPRODUCING_EXAMPLE, MINIMAL_EXAMPLE]
        elif self.need_testing:
            examples = [TESTING_EXAMPLE, MINIMAL_EXAMPLE]
        else:
            # Return the default example
            examples = [MINIMAL_EXAMPLE]
        return SEPARATOR.join(examples)

    def _adjust_important_tips(self):
        if self.need_reproducing and self.need_testing:
            return IMPORTANT_TIPS + TIP_FOR_REPRODUCING + TIP_FOR_TESTING
        elif self.need_reproducing:
            return IMPORTANT_TIPS + TIP_FOR_REPRODUCING
        elif self.need_testing:
            return IMPORTANT_TIPS + TIP_FOR_TESTING
        else:
            # Return the default important tips
            return IMPORTANT_TIPS

    def _set_ensemble_parameters(self, ensemble_index):
        if ensemble_index == 0:
            self.need_reproducing = False
            self.need_testing = False
        elif ensemble_index == 1:
            self.need_reproducing = True
            self.need_testing = False
        else:
            self.need_reproducing = True
            self.need_testing = True

        logger.info(
            f"Ensemble index: {ensemble_index}, need_reproducing: {self.need_reproducing}, need_testing: {self.need_testing}"
        )

    @contextmanager
    def ensemble_parameters(self, ensemble_index):
        original_need_reproducing = self.need_reproducing
        original_need_testing = self.need_testing
        self._set_ensemble_parameters(ensemble_index)
        yield
        # Reset the conditions
        self.need_reproducing = original_need_reproducing
        self.need_testing = original_need_testing

    async def summarize_traj(self, trajectory, code_change=""):
        prompt = SUMMARY_PROMPT.format(trajectory=trajectory, code_change=code_change)
        response = await self.llm.aask(prompt)
        summary_response = json.loads(CodeParser.parse_code(block=None, text=response))
        summary = summary_response.get("summary", "")

        logger.info(f"Summary of the trajectory:\n{summary}")
        # Clear the working memory
        self.working_memory.clear()
        return summary


if __name__ == "__main__":
    import asyncio

    dataset_path = "manna-ai/SWE-bench_Mini"  # "manna-ai/SWE-bench_Nano"  # "princeton-nlp/SWE-bench_Lite", "manna-ai/SWE-bench_Mini"
    # instance_ids = ["django__django-15996"]  # "django__django-11099", "django__django-12700"

    dataset = load_hf_dataset(dataset_name_or_path=dataset_path, cache_dir=DATA_DIR, split="test")
    instance_ids = [instance["instance_id"] for instance in dataset]

    # requirement = """Identify and resolve the specific bug in the repository. """

    requirement = """Fix the bug in the repo. Because the environment is not available, you DO NOT need to run and
    # modify any existing test case files or add new test case files to ensure that the bug is fixed."""

    swe_agent = SWEAgent(
        user_requirement=requirement,
        instance_ids=instance_ids,
        fetch_from_dataset=True,
        dataset_path=dataset_path,
        need_reproducing=True,  # For reproducing the bug
        need_testing=False,  # For executing the test suite
        need_ensemble=False,
        need_summary=False,
        can_retry_submission=False,
    )
    asyncio.run(swe_agent.run(requirement))
