# Step 1: one agent, one tool -------------------------------------------------
# The model never sees the data. It can only ask us to run
# room_utilization(), then it writes an answer from what that returns.
#
# Run from C:\periop-demo\py-app with:  uv run python agent_step1.py

import numpy as np
from pydantic_ai import Agent

from app import BLOCK_END, BLOCK_MINS, BLOCK_START, cases  # reuse the app's data

# The agent: a model + standing instructions (+ tools, added below) ------------
agent = Agent(
    "anthropic:claude-sonnet-5-5",
    instructions=(
        "You answer questions about operating room performance. "
        "Never guess a number: get every figure from a tool. "
        "The block utilization target is 75%. Answer in 2-3 sentences."
    ),
)


# The tool: a governed metric function the model is allowed to request --------
# The docstring and type hints matter: the model reads them to decide
# when to call this function and what arguments to pass.
@agent.tool_plain
def room_utilization(month: int) -> dict[str, float]:
    """Average block utilization (0 to 1) for each operating room in a month.

    Args:
        month: Month number, 7 (July) through 9 (September) 2026.
    """
    df = cases[cases["date"].dt.month == month].copy()
    df["in_block"] = (
        np.minimum(df["end_min"], BLOCK_END) - np.maximum(df["start_min"], BLOCK_START)
    ).clip(lower=0)
    room_days = df.groupby(["date", "room"])["in_block"].sum() / BLOCK_MINS
    return room_days.groupby("room").mean().round(3).to_dict()


# Run it, then print the loop so you can watch the agent work -----------------
if __name__ == "__main__":
    question = "What was first-case on-time performance in August?"
    result = agent.run_sync(question)

    print(f"QUESTION: {question}\n")
    for message in result.all_messages():
        for part in message.parts:
            if part.part_kind == "tool-call":
                print(f"-> model asks to run: {part.tool_name}({part.args})")
            elif part.part_kind == "tool-return":
                print(f"<- our code returns: {part.content}")
    print(f"\nANSWER: {result.output}")
