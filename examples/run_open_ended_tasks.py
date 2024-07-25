import os
import fire

from examples.requirements_prompt import OPEN_ENDED_TASKS_REQUIREMENTS
from di_project.roles.data_interpreter import DataInterpreter
from di_project.tools.tool_recommend import TypeMatchToolRecommender


# Ensure Open-Ended Tasks dataset has been downloaded before using this example.
async def main(task_name="14_image_background_removal", data_dir=".", use_reflection=True):
    if not os.path.exists(os.path.join(data_dir, "di_dataset/open_ended_tasks")):
        raise FileNotFoundError(f"Open-ended task dataset not found in {data_dir}.")

    requirement = OPEN_ENDED_TASKS_REQUIREMENTS[task_name].format(data_dir=data_dir)
    di = DataInterpreter(use_reflection=use_reflection, tools=["<all>"])
    await di.run(requirement)


if __name__ == "__main__":
    fire.Fire(main)
