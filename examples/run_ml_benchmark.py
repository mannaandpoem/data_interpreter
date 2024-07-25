import os
import fire

from examples.requirements_prompt import ML_BENCHMARK_REQUIREMENTS
from di_project.roles.data_interpreter import DataInterpreter

# Ensure ML-Benchmark dataset has been downloaded before using these example.
async def main(task_name="04_titanic", data_dir=".", use_reflection=True, use_experience=False):
    print(os.path.join(data_dir, "di_dataset/ml_benchmark"))
    if not os.path.exists(os.path.join(data_dir, "di_dataset/ml_benchmark")):
        raise FileNotFoundError(f"ML-Benchmark dataset not found in {data_dir}.")

    requirement = ML_BENCHMARK_REQUIREMENTS[task_name].format(data_dir=data_dir)
    di = DataInterpreter(use_reflection=use_reflection, tools=["<all>"], use_experience=use_experience)
    await di.run(requirement)


if __name__ == "__main__":
    fire.Fire(main)
