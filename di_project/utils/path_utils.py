import shutil
from pathlib import Path
from typing import Union
from metagpt.logs import logger

import regex

def converted_path(windows_path):
    p = Path(windows_path)
    # 提取驱动器和路径部分
    drive = p.drive[:-1].lower()  # 移除冒号并转换为小写
    rest_of_path = p.parts[1:]  # 去掉驱动器部分
    # 生成WSL路径
    wsl_path = Path("/") / drive / "/".join(rest_of_path)
    return wsl_path.as_posix()


def converted_back_to_windows(wsl_path):
    p = Path(wsl_path)
    # 提取驱动器和路径部分
    drive = p.parts[1].upper() + ":"  # 恢复驱动器部分并转换为大写
    rest_of_path = p.parts[2:]  # 去掉驱动器部分
    # 生成Windows路径
    windows_path = Path(drive + "\\").joinpath(*rest_of_path)
    return windows_path.as_posix().replace("/", "\\")

def find_exist_repo_path_and_cp(repo_path: Path) -> Union[Path, None]:
    """find an first existed repo path with same repo name, no need to clone different version with same repo"""
    repo_path = Path(repo_path)
    if repo_path.exists() and any(Path(repo_path).rglob("*.py")):
        return repo_path

    new_repo_path = None
    repo_root_path = repo_path.parent
    for subfolder in repo_root_path.iterdir():
        if not subfolder.is_dir():
            continue

        version = regex.findall("[0-9]+\.[0-9]+", subfolder.name)
        subfolder.name.split("_")
        repo_fmt_name = (
            subfolder.name if not version else "_".join(subfolder.name.split("_")[:-1])
        )  # with `version` suffix
        if repo_fmt_name in str(repo_path):
            # find an existed same repo_name repo
            shutil.rmtree(str(repo_path), ignore_errors=True)
            shutil.copytree(str(subfolder), str(repo_path))
            logger.info(f"copy repo from existed {subfolder} to {repo_path}")
            new_repo_path = repo_path
            break
    return new_repo_path


if __name__ == "__main__":
    # Example usage
    windows_path_str = (
        "F:/deepWisdom/swe-bench/test_repo-abs-1/sympy__sympy_1.1/sympy/functions/combinatorial/numbers.py"
    )
    new_path = converted_back_to_windows(converted_path(windows_path_str))
    print("Converted Path:", new_path)
