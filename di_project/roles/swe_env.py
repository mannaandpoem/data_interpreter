from metagpt.const import METAGPT_ROOT
from pydantic import Field

from di_project.prompts.swe_agent import NEXT_STEP_NO_OUTPUT_TEMPLATE, INVALID_INPUT_MESSAGE
from di_project.tools.libs.terminal import Bash
from di_project.tools.swe_agent_commands.swe_agent_utils import replace_action_for_nt

import os
import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel, model_validator
from swebench import MAP_VERSION_TO_INSTALL
from swebench.harness.utils import get_environment_yml, get_requirements

from metagpt.logs import logger
from di_project.tools.swe_agent_commands.swe_agent_utils import get_conda_base_path

CONSECUTIVE_LIMIT = 3
EDIT_CONSECUTIVE_LIMIT = 3
EDIT_DIVIDER = "This is how your edit would have looked if applied"
SWE_SETUP_PATH = METAGPT_ROOT / "metagpt" / "tools" / "swe_agent_commands" / "setup_default.sh"


class SWEEnv:
    """
    The EnvManager class is responsible for managing the environment, including:

    - Parsing and processing commands for the current environment.
    - Initializing the environment.
    - Finding and setting the Python executor.
    - Installing packages using pip.

    Attributes:
        env_name (str): The name of the environment.
        repo_path (str): The path to the repository.
        repo_name (str): The name of the repository.
        version (str): The version of the repository.
        instance (dict): The instance details.
        conda_env_path (Path): The path to the conda environment.
        env_python_executor (str): The path to the Python executor in the environment.
        env_pip_executor (str): The path to the pip executor in the environment.
        install_req (dict): The installation requirements.
        python_version (str): The Python version to use in the environment.
        terminal (Bash): The terminal object to execute bash commands.
    """
    env_name: str = ""
    repo_path: str = ""  # The code path to be processed
    repo_name: str = ""
    version: str = ""
    instance: dict = {}
    conda_env_path: Path = Path(get_conda_base_path(sys.executable))
    env_python_executor: str = ""
    env_pip_executor: str = ""
    install_req: dict = {}
    python_version: str = ""
    terminal: Bash = Field(default_factory=Bash, exclude=True)

    @model_validator(mode="after")
    def set_env(self) -> "EnvManager":
        if os.name == "nt":  # Windows
            self.env_python_executor: str = os.path.join(self.conda_env_path, self.env_name, "python")
            self.env_pip_executor: str = os.path.join(self.conda_env_path, self.env_name, "python -m pip")
        else:  # POSIX (Linux, Unix, MacOS, etc.)
            self.env_python_executor: str = os.path.join(self.conda_env_path, self.env_name, "bin/python")
            self.env_pip_executor: str = os.path.join(self.conda_env_path, self.env_name, "bin/python -m pip")
        self.parse_install_cmd(self.instance)

    def check_conda_env_exists(self, env_name):
        # 使用 conda activate env 命令激活对应环境
        # command = f"source ~/.bashrc && conda activate {env_name}"  # for max/linux
        command = f"conda activate {env_name}"
        # 执行命令，并捕获输出
        result = subprocess.run(command, capture_output=True, text=True, shell=True, encoding="utf-8")
        # 检查是否执行成功
        if result.returncode == 0:
            return True
        logger.error(f"check_conda_env_exists failed, res: {result}")
        return False

    def create_env(self):
        # 检测是否存在环境，存在即退出，直接切换
        if self.check_conda_env_exists(self.env_name):
            logger.info(self.env_python_executor)
            return
        logger.info(f"Env {self.env_name} not exists, start to create it.")

        pkgs = self.install_req["packages"]
        extra_pkgs = self.install_req["pip_packages"]

        if pkgs not in ["environment.yml", "requirements.txt"]:
            cmd = f"conda create -n {self.env_name} python={self.python_version} {pkgs} -y"
            result = subprocess.run(cmd, shell=True)

            self.env_python_executor: str = os.path.join(self.conda_env_path, self.env_name, "python")
            self.env_pip_executor: str = os.path.join(self.conda_env_path, self.env_name, "bin/python -m pip")

        if pkgs == "requirements.txt":
            cmd = f"conda create -n {self.env_name} python={self.python_version} -y"
            result = subprocess.run(cmd, shell=True)

            self.env_python_executor: str = os.path.join(self.conda_env_path, self.env_name, "python")
            self.env_pip_executor: str = os.path.join(self.conda_env_path, self.env_name, "bin/python -m pip")

            path_to_reqs = get_requirements(self.instance, self.repo_path)
            logger.info(path_to_reqs)
            install_cmd = f"{self.env_pip_executor} install -r {path_to_reqs}"
            logger.info(install_cmd)
            result = subprocess.run(install_cmd, shell=True)

        if pkgs == "environment.yml":
            # fixme: in windows, requests.get(url) return 400, need: reqs_url = reqs_url.replace("\\", "/")
            path_to_reqs = get_environment_yml(
                self.instance, self.env_name, save_path=self.repo_path, python_version=self.python_version
            )

            if path_to_reqs is None:
                path_to_reqs = Path(self.repo_path) / pkgs

            install_cmd = f"conda env create --file {path_to_reqs}"
            result = subprocess.run(install_cmd, shell=True)

        if extra_pkgs:
            install_cmd = f"{self.env_pip_executor} {extra_pkgs}"
            result = subprocess.run(install_cmd, shell=True)
        return result.returncode

    def parse_install_cmd(self, instance: dict):
        # Get installation instructions by repo/version
        specifications = MAP_VERSION_TO_INSTALL[instance["repo"]][instance["version"]]

        install_cmd = specifications.get("install", "")
        if install_cmd:
            if "python -m pip " in install_cmd:
                install_cmd = install_cmd.replace("python -m pip", self.env_pip_executor)
            else:
                install_cmd = install_cmd.replace("pip", self.env_pip_executor)

        pre_install_cmd = specifications.get("pre_install", "")
        post_install_cmd = specifications.get("post_install", "")

        # todo: test on pre_install and post_install cases
        self.python_version = specifications["python"]
        self.install_req["packages"] = specifications.get("packages", "")
        self.install_req["pip_packages"] = specifications.get("pip_packages", "")
        self.install_req["install"] = install_cmd
        self.install_req["pre_install_cmd"] = pre_install_cmd
        self.install_req["post_install_cmd"] = post_install_cmd
        return install_cmd

    def step(self, action, bash_state, max_obs_len=6000, action_is_stuck=False):
        observation = self._execute_bash_action(action=action, bash_state=bash_state)
        if action_is_stuck:
            observation = self._post_observation(action, observation)

        if len(observation) <= max_obs_len:
            return f"Observation:\n{observation}"
        # Truncate the observation if it is too long
        else:
            half_len = max_obs_len // 2
            return f"Observation:\n{observation[:half_len]}...\n[truncated due to length]\n...{observation[-half_len:]}"

    @staticmethod
    def _post_observation(action, observation):
        edit_error_rst = observation.split(EDIT_DIVIDER)[0].strip()
        if action.startswith("edit") and edit_error_rst:
            observation = f"""{edit_error_rst}\nIMPORTANT: {EDIT_CONSECUTIVE_LIMIT} consecutive `edit` actions 
            are **not allowed**. Based on the recent error information, modify your actions accordingly instead 
            of repeating the previous command. For instance, use goto to jump to the specified line."""
        else:
            consecutive_action = action.split(" ")[0]
            observation = f"""{observation}\nIMPORTANT: {CONSECUTIVE_LIMIT} consecutive `{consecutive_action}` bash 
            command are **not allowed**. Please use other bash commands to fix the bug."""

        return observation

    def _execute_bash_action(self, action, bash_state):
        if action:
            if os.name == "nt":
                action = replace_action_for_nt(action, env_manager=self.env_manager)
                observation = self.terminal.run(action)
            else:
                if action.startswith(("python", "pytest", "pip")):
                    # env_name = self.repo_info[self.cur_instance_id]["env_name"]
                    env_name = self.env_manager.env_name
                    # Avoid env lacking pytest package
                    check_pytest_exist = self.terminal.execute_in_conda_env("pip list | grep pytest", env_name)
                    if not check_pytest_exist:
                        install_cmd = "pip install pytest --trusted-host pypi.org --trusted-host pypi.python.org"
                        install_obs = self.terminal.execute_in_conda_env(install_cmd, env_name)
                        logger.info(f"Install pytest ...\n{install_obs}")
                    # self.terminal.execute_in_conda_env("pip install pytest", env_name)
                    observation = self.terminal.execute_in_conda_env(action, env_name)
                else:
                    observation = self.terminal.run(action)

            # No output from the action
            if not observation:
                observation = NEXT_STEP_NO_OUTPUT_TEMPLATE.format(**bash_state)

        else:
            observation = INVALID_INPUT_MESSAGE

        return observation
