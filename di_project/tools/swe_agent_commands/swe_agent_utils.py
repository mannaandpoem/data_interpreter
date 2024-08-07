#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import load_dataset, load_from_disk
from github import Github
from metagpt.logs import logger
from metagpt.utils.common import CodeParser

from di_project.utils.path_utils import converted_path

OUTPUT_DIR = Path(__file__).parent


def extract_patch(command_output):
    patch_lines = []
    recording = False
    for line in command_output.split("\n"):
        if line.startswith("diff --git"):
            recording = True
        if recording:
            patch_lines.append(line)
    return "\n".join(patch_lines)


def load_hf_dataset(dataset_name_or_path: str, cache_dir, split: str = "test", existing_ids: list = []):
    data_dir = cache_dir / dataset_name_or_path
    if Path(data_dir).exists():
        dataset = load_from_disk(data_dir)
    else:
        dataset = load_dataset(dataset_name_or_path)
        dataset.save_to_disk(data_dir)
    print(dataset)
    if split not in dataset:
        raise ValueError(f"Invalid split {split} for dataset {dataset_name_or_path}")
    dataset = dataset[split]
    np.array(list(map(len, dataset["instance_id"])))

    if existing_ids:
        dataset = dataset.filter(
            lambda x: x["instance_id"] not in existing_ids,
            desc="Filtering out existing ids",
            load_from_cache_file=False,
        )

    return dataset


def extract_repo_identifier(requirement: str) -> str:
    """Extract the repository identifier from requirement."""
    match = re.search(r"github\.com/([^/]+/[^/]+)/issues/\d+", requirement)
    if match:
        return match.group(1)
    return ""


def get_github_issue_description(owner: str, repo_name: str, issue_number: int) -> str:
    """Get the description of a GitHub issue."""
    g = Github(os.getenv("GITHUB_TOKEN"))
    repo = g.get_repo(f"{owner}/{repo_name}")
    return repo.get_issue(number=issue_number).body


def filter_and_get_repo_info(
    dataset: pd.DataFrame,
    filter_column: str,
    result_dir: str = "",
    selected_ids: list[str] = None,
) -> tuple[pd.DataFrame, dict]:
    """Filter the dataset based on selected and finished IDs and get repository information.

    Args:
        dataset (pd.DataFrame): The dataset to filter.
        filter_column (str): The column name to filter by.
        result_dir (str, optional): The directory containing the results. Defaults to "".
        selected_ids (list[str], optional): List of IDs to include. Defaults to None.

    Returns:
        tuple[pd.DataFrame, dict]: A tuple containing the filtered dataset and a dictionary of repository information.
    """
    # 开始时，subset 是整个数据集
    subset = dataset.copy()

    # 如果all_preds.jsonl存在，则从中获取已完成的任务ID
    # check_existing_ids
    finished_ids = check_existing_ids(f"{result_dir}/all_preds.jsonl")

    subset = subset[~subset[filter_column].isin(finished_ids)]

    # 如果提供了 selected_ids，则只保留这些ID
    if selected_ids:
        subset = subset[subset[filter_column].isin(selected_ids)]

    # 打印筛选后的任务数量
    logger.info(f"Retained {subset.shape[0]} tasks after filtering")

    # Initialize an empty dictionary to store the repository information
    repo_info = {}

    # Iterate over the selected IDs to extract information for each instance
    for _, instance in subset.iterrows():
        instance_id = instance["instance_id"]
        base_commit = instance["base_commit"]
        problem_statement = instance["problem_statement"]
        hints_text = instance["hints_text"] if instance["hints_text"] else "None"
        repo = instance["repo"]
        patch = instance["patch"]

        # FIXME: ENV_INFO_DATA differs from env_name, it should be single _ separated strings
        # env_name = ENV_INFO_DATA.get(instance_id, "")
        env_name = ""
        if not env_name:
            repo_prefix = repo.replace("/", "__").replace("-", "_")
            version = instance["version"]
            # env_name = f"{repo_prefix}__{version}"
            env_name = f"{repo_prefix}_{version}"

        # Record the information of the repository for the current instance ID
        repo_info[instance_id] = {
            "instance_id": instance_id,
            "exit_status": "n/a",
            "base_commit": base_commit,
            "problem_statement": problem_statement,
            "hints_text": hints_text,
            "patch": patch,
            "repo": repo,
            "env_name": env_name,
            "submission": "",
        }

    return subset, repo_info


def get_conda_base_path(python_executable_path):
    # 使用正则表达式匹配 'envs' 前的部分
    envs_marker = os.sep.join(["", "envs", ""])
    envs_index = python_executable_path.find(envs_marker)
    # 如果找到 'envs'
    if envs_index != -1:
        # 返回包含 'envs' 的路径，即截取到 'envs' 之后的第一个路径分隔符
        return python_executable_path[: envs_index + len(envs_marker) - 1]
    else:
        # 如果路径中没有 'envs'，返回 Python 解释器所在的根目录
        return os.path.dirname(os.path.dirname(python_executable_path))


def check_existing_ids(output_file):
    existing_ids = set()
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            for line in f:
                data = json.loads(line)
                instance_id = data["instance_id"]
                existing_ids.add(instance_id)
    return existing_ids


def load_oracle_dataset(
    dataset_name_or_path: str = "",
    split: str = "test",
    existing_ids: list = None,
    selected_id: str = "",
):
    if Path(dataset_name_or_path).exists():
        dataset = load_from_disk(dataset_name_or_path)
    else:
        dataset = load_dataset(dataset_name_or_path)
    if split not in dataset:
        raise ValueError(f"Invalid split {split} for dataset {dataset_name_or_path}")
    dataset = dataset[split]
    lens = np.array(list(map(len, dataset["text"])))
    dataset = dataset.select(np.argsort(lens))

    if existing_ids:
        dataset = dataset.filter(
            lambda x: x["instance_id"] not in existing_ids,
            desc="Filtering out existing ids",
            load_from_cache_file=False,
        )
    if selected_id:
        dataset = dataset.filter(
            lambda x: x["instance_id"] in selected_id,
            desc="Filtering out subset_instance_ids",
            load_from_cache_file=False,
        )
    return dataset


def extract_patch(command_output):
    patch_lines = []
    recording = False
    for line in command_output.split("\n"):
        if line.startswith("diff --git"):
            recording = True
        if recording:
            patch_lines.append(line)
    return "\n".join(patch_lines)


def parse_thought_and_action(response: str) -> tuple[str, str]:
    """Parsing thought and action from the response."""
    try:
        if "```json" in response:
            response = json.loads(CodeParser.parse_code(text=response, block=None), strict=False)
        else:
            logger.warning("生成JSON格式错误，使用规则提取……")
            response = json.loads(re.search(".*?(\{.*\}).*", response, re.DOTALL).group(1), strict=False)
        thought, action = response.get("thought", ""), response.get("bash_command", "")
        if not action:
            raise ValueError("Invalid thought or action in response.")
    except Exception as e:
        logger.error(
            f"Error parsing response: {e}\n<----------Check The Response---------->\n{response}\n<----------Check The Response---------->"
        )
        thought, action = "", ""

    return thought, action


def replace_action_for_nt(action, env_manager):
    if action.startswith("python ") or "python " in action:
        python_executor = converted_path(env_manager.env_python_executor)
        action = action.replace("python ", f"{python_executor} ")
        logger.info(f"Replace action cmd {action}")

    elif action.startswith("pytest"):
        if "edit" in action or "open" in action:
            action = action
        else:
            action = action.replace("pytest", f"conda activate {env_manager.env_name} && pytest")
        logger.info(f"Replace action cmd {action}")

    elif action.startswith("pip "):
        pip_executor = converted_path(env_manager.env_pip_executor)
        action = action.replace("pip ", f"{pip_executor} ")
    return action


def save_trajectory(traj_dir: Path, name: str, repo_info: dict, trajectory: list):
    traj_path = traj_dir / f"{name}.traj"

    # Check if the traj_path already exists
    index = 1
    while traj_path.exists():
        traj_path = traj_dir / f"{name}_{index}.traj"
        index += 1

    # Converts the entire trajectory list to JSON.
    trajectory_list = [node.to_json() for node in trajectory]

    # Save the trajectory to a JSON file
    log_dict = {
        "trajectory": trajectory_list,
        "info": repo_info,
    }
    with open(traj_path, "w") as f:
        json.dump(log_dict, f, indent=2)

    trajectory_actions = "\n->\n".join([node.action for node in trajectory])
    logger.info(f"Actions of trajectory:\n{trajectory_actions}")
    logger.info(f"Saved trajectory of {name} to {str(traj_path)}")


def view_file_with_line_numbers_and_format(file_path):
    res = ""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                # 使用repr()来显示包括制表符和换行符在内的所有字符

                res += f"{line_number}: {repr(line)}" + "\n"
    except FileNotFoundError:
        res = "The file was not found."
    except Exception as e:
        res = f"An error occurred: {e}"
    return res
