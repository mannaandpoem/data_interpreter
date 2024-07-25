import fire
from di_project.roles.data_interpreter import DataInterpreter


WINE_REQ = "Run data analysis on sklearn Wine recognition dataset, include a plot, and train a model to predict wine class (20% as validation), and show validation accuracy."


REQUIREMENTS = {"wine": WINE_REQ}


async def main(use_case: str = "wine"):
    di = DataInterpreter()
    requirement = REQUIREMENTS[use_case]
    await di.run(requirement)


if __name__ == "__main__":
    fire.Fire(main)
