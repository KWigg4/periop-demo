# Step 2: structured output ---------------------------------------------------
# Same agent and tool as step 1, but the answer must come back as a validated
# Pydantic object instead of free text. Think of the classes below as a REDCap
# data dictionary: field names, types, and allowed ranges.
#
# Run from C:\periop-demo\py-app with:  uv run python agent_step2.py

import numpy as np
from pydantic import BaseModel, Field, model_validator
from pydantic_ai import Agent

from app import BLOCK_END, BLOCK_MINS, BLOCK_START, cases

TARGET = 0.75


# The output schema -------------------------------------------------------------
class RoomFinding(BaseModel):
    room: str = Field(description="Room name, e.g. OR-04")
    utilization: float = Field(ge=0, le=1, description="Proportion from 0 to 1, not a percent")
    meets_target: bool = Field(description="True if utilization is at least 0.75")

    # A validation rule, like a REDCap data-quality check: meets_target must
    # agree with the number. If the model gets this wrong, Pydantic rejects
    # the output and Pydantic AI sends the error back so the model can retry.
    @model_validator(mode="after")
    def target_flag_matches_value(self):
        if self.meets_target != (self.utilization >= TARGET):
            raise ValueError(f"meets_target is wrong for {self.room}: "
                             f"utilization {self.utilization} vs target {TARGET}")
        return self


class UtilizationAnswer(BaseModel):
    answerable: bool = Field(description="False if no tool provides the requested metric")
    months: list[int] = Field(default_factory=list,
                              description="Months used, 7 to 9 (2026)")
    rooms: list[RoomFinding] = Field(default_factory=list,
                                     description="Only the rooms the question is about")
    summary: str = Field(description="Two sentences or fewer, plain language")


# The agent: same as step 1, plus output_type --------------------------------------
agent = Agent(
    "anthropic:claude-sonnet-5-5",
    output_type=UtilizationAnswer,
    instructions=(
        "You answer questions about operating room performance. "
        "Never guess a number: get every figure from a tool. "
        "The block utilization target is 75%. "
        "If no tool provides what was asked, set answerable to false."
    ),
)


@agent.tool_plain
def room_utilization(month: int) -> dict[str, float]:
    """Average block utilization (0 to 1) for each operating room in a month.

    Args:
        month: Month number, 7 (July) through 9 (September) 2026.
    """
    df = cases[cases["date"].dt.month == month].copy()
    df["in_block"] = (np.minimum(df["end_min"], BLOCK_END)
                      - np.maximum(df["start_min"], BLOCK_START)).clip(lower=0)
    room_days = df.groupby(["date", "room"])["in_block"].sum() / BLOCK_MINS
    return room_days.groupby("room").mean().round(3).to_dict()


# Run a few questions -----------------------------------------------------------
if __name__ == "__main__":
    questions = [
        "Which room had the lowest utilization in August, and was it below target?",
        "Did any room meet the utilization target in September?",
        "What was first-case on-time performance in August?",
    ]

    for question in questions:
        answer = agent.run_sync(question).output   # a UtilizationAnswer object

        print(f"\nQUESTION: {question}")
        print(answer.model_dump_json(indent=2))     # the raw structured output

        # Because it's typed data, your code can use the fields directly,
        # the way the Shiny app would to draw a table or a value box:
        if answer.answerable:
            below = [r.room for r in answer.rooms if not r.meets_target]
            print(f"Rooms below target in this answer: {below}")
        else:
            print("Agent says it can't answer this with its tools.")
