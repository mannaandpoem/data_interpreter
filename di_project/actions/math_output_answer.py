from typing import List

from metagpt.actions import Action
from metagpt.schema import Message

OUTPUT_ANSWER_CONTEXT = """
## Context
{content}
-----
"""


class MathOutputAnswer(Action):
    async def run(
        self,
        context: List[Message],
    ):
        content = context[0].content
        prompt = OUTPUT_ANSWER_CONTEXT.format(
            content=content,
        )
        prompt += (
            "\nAccording to the above information and runtime answer, put the answer in \\boxed{}, in LaTex format."
        )
        rsp = await self._aask(prompt)
        return rsp
