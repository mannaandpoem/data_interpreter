import asyncio
import json
from datetime import datetime

from metagpt.const import DEFAULT_WORKSPACE_ROOT, METAGPT_ROOT

from di_project.prompts.swe_agent import INSTANCE_TEMPLATE
from di_project.roles.swe_agent import SWEAgent
from di_project.tools.libs.terminal import Terminal
from di_project.tools.swe_agent_commands.swe_agent_utils import load_hf_dataset

# Specify by yourself
TEST_REPO_DIR = METAGPT_ROOT.parent / "data" / "test_repo"
DATA_DIR = METAGPT_ROOT.parent / "data/hugging_face"


def check_instance_status(instance, swe_result_dir):
    output_file = swe_result_dir / "all_preds.jsonl"
    res = True
    # 先检查all_preds.jsonl文件是否存在
    if not output_file.exists():
        return res
    with open(output_file, "r") as fp:
        for line in fp:
            existing_instance = json.loads(line.strip())
            if existing_instance["instance_id"] == instance["instance_id"]:
                return False
    return True


async def run(instance, swe_result_dir):
    if not check_instance_status(instance, swe_result_dir):
        print(f"Instance {instance['instance_id']} already exists, skipping execution.")
        return

    repo_path = TEST_REPO_DIR / (instance["repo"].replace("-", "_").replace("/", "__") + "_" + instance["version"])

    # 前处理
    terminal = Terminal()
    if not repo_path.exists():
        print("Repo not found, cloning...")
        clone_command = f"git clone 'https://github.com/{instance['repo']}.git' {repo_path}"
        print(terminal.run_command(clone_command))
    base_commit = instance["base_commit"]
    checkout_command = f"cd {repo_path} && git checkout -f {base_commit}" if base_commit else ""
    print(terminal.run_command(checkout_command))
    print(terminal.run_command("git branch"))

    user_requirement_and_issue = INSTANCE_TEMPLATE.format(
        issue=instance["problem_statement"],
        hints_text=instance["hints_text"],
        repo_path=repo_path,
        version=instance["version"],
        base_commit=instance["base_commit"],
    )
    print(f"**** Starting to run {instance['instance_id']}****")
    swe_agent = SWEAgent()
    swe_agent.cur_instance_id = instance["instance_id"]
    swe_agent.repo_path = repo_path
    await swe_agent.run(user_requirement_and_issue)
    save_predictions(swe_agent, instance, swe_result_dir)
    print(f"**** Finished running {instance['instance_id']}****")


def save_predictions(swe_agent: SWEAgent, instance, swe_result_dir):
    output_file = swe_result_dir / "all_preds.jsonl"
    instance["model_name_or_path"] = swe_agent.config.llm.model
    instance["model_patch"] = swe_agent.repo_info["submission"]

    print(f"Preparing to save predictions to {output_file}")

    # Save the predictions to a JSONL file
    with open(output_file, "a+") as fp:
        print(json.dumps(instance), file=fp, flush=True)

    print(f"Saved prediction of {instance['instance_id']} to {output_file}")


async def async_main():
    dataset_path = "manna-ai/SWE-bench_Nano"  # "princeton-nlp/SWE-bench_Lite"

    dataset = load_hf_dataset(dataset_name_or_path=dataset_path, cache_dir=DATA_DIR, split="test")
    date_time = datetime.now().strftime("%m%d")
    _round = "first"
    # _round = "second"
    exp_name = f"nano_mgx_{date_time}_{_round}"
    swe_result_dir = DEFAULT_WORKSPACE_ROOT / "result" / exp_name
    swe_result_dir.mkdir(parents=True, exist_ok=True)
    for instance in dataset:
        await run(instance, swe_result_dir)


if __name__ == "__main__":
    asyncio.run(async_main())
