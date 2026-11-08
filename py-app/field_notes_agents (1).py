# Field notes with subagents ------------------------------------------------------
# A small version of the "subagent architecture, registry/dispatch, structured
# output, and evaluation" pattern from the job description, applied to
# practice-facilitation field notes (all synthetic).
#
#   orchestrator -> router decides which optional subagents each note needs
#                -> extractor  (always)  : structured visit fields
#                -> coder      (always)  : codebook codes with verbatim excerpts
#                -> safety     (routed)  : possible adverse event or deviation
#   evaluation   -> compare against the human-coded gold standard
#
# Run from C:\periop-demo\py-app with:  uv run python field_notes_agents.py

import json
from dataclasses import dataclass
from datetime import date
from typing import Literal, get_args

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from field_notes_data import CODEBOOK, GOLD, NOTES

MODEL = "anthropic:claude-sonnet-5-5"
ROUTER_MODEL = "anthropic:claude-haiku-5-5"   # routing is a simple job: use a cheaper model

# Only codes from the codebook are valid. Type checkers need the values written
# out, so the assert below keeps this list in sync with CODEBOOK.
Code = Literal["LEADERSHIP_ENGAGEMENT", "AVAILABLE_RESOURCES", "EHR_TECHNOLOGY",
               "STAFF_KNOWLEDGE_BELIEFS", "PATIENT_NEEDS"]
assert set(get_args(Code)) == set(CODEBOOK), "Code list and CODEBOOK don't match"


# Output schemas: one per subagent -------------------------------------------------
class VisitExtract(BaseModel):
    visit_date: date | None = Field(description="Date of the visit, if stated")
    practice: str
    strategies_used: list[str] = Field(description="Implementation strategies or actions taken")
    barriers: list[str]
    follow_up_planned: bool = Field(description="True only if a specific next visit, call, or check is planned")


class CodedExcerpt(BaseModel):
    code: Code
    excerpt: str = Field(description="Exact quote from the note that supports the code")
    rationale: str = Field(description="One sentence")


class CodingResult(BaseModel):
    codes: list[CodedExcerpt] = Field(description="Empty if no code applies")


class SafetyFlag(BaseModel):
    possible_safety_event: bool
    event_type: Literal["adverse_event", "protocol_deviation", "none"]
    reason: str = Field(description="One sentence")


class RoutingDecision(BaseModel):
    run: list[str] = Field(description="Names of optional subagents to run; may be empty")
    reason: str


# Subagents ---------------------------------------------------------------------------
extractor = Agent(
    MODEL,
    output_type=VisitExtract,
    instructions="Extract structured fields from a practice-facilitation field note. "
                 "Use only what the note states; never infer facts it doesn't contain.",
)

codebook_text = "\n".join(f"- {code}: {definition}" for code, definition in CODEBOOK.items())
coder = Agent(
    MODEL,
    deps_type=str,                 # the note text, so the validator can check quotes
    output_type=CodingResult,
    retries=2,
    instructions="You are a qualitative coder. Apply codes from this codebook to the note. "
                 "Apply a code only when the note clearly supports it, and quote the exact "
                 f"supporting text.\n\nCodebook:\n{codebook_text}",
)


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


@coder.output_validator
def excerpts_must_be_verbatim(ctx: RunContext[str], output: CodingResult) -> CodingResult:
    """Grounding check: every excerpt must appear word for word in the note.
    A failed check goes back to the model as an error, and it retries."""
    note = _norm(ctx.deps)
    for item in output.codes:
        if _norm(item.excerpt) not in note:
            raise ModelRetry(f"The excerpt for {item.code} is not a verbatim quote "
                             f"from the note: {item.excerpt!r}")
    return output


safety_screener = Agent(
    MODEL,
    output_type=SafetyFlag,
    instructions="Screen a field note for a possible adverse event (harm or a medical event "
                 "affecting a patient) or protocol deviation (for example enrollment or consent "
                 "problems). Flag for human review; do not make a final determination.",
)


# Registry: what each subagent does, and whether it always runs ------------------------
@dataclass
class SubagentSpec:
    name: str
    description: str
    agent: Agent
    always_run: bool
    needs_deps: bool = False


REGISTRY = {
    spec.name: spec
    for spec in [
        SubagentSpec("extractor", "Extracts structured visit fields.", extractor, always_run=True),
        SubagentSpec("coder", "Applies the qualitative codebook.", coder, always_run=True, needs_deps=True),
        SubagentSpec("safety_screener",
                     "Screens for possible adverse events or protocol deviations. Run it when a "
                     "note mentions anything that happened to a patient, a consent or enrollment "
                     "problem, or any departure from the study protocol.",
                     safety_screener, always_run=False),
    ]
}

optional = [s for s in REGISTRY.values() if not s.always_run]
router = Agent(
    ROUTER_MODEL,
    output_type=RoutingDecision,
    instructions="Decide which optional subagents should process this field note.\n"
                 + "\n".join(f"- {s.name}: {s.description}" for s in optional),
)


@router.output_validator
def only_registered_names(output: RoutingDecision) -> RoutingDecision:
    unknown = [name for name in output.run if name not in REGISTRY]
    if unknown:
        raise ModelRetry(f"Unknown subagents {unknown}. Choose from: {[s.name for s in optional]}")
    return output


# Orchestrator: route, then dispatch ------------------------------------------------------
def process_note(note_id: str, text: str) -> dict:
    routing = router.run_sync(text).output
    to_run = [s for s in REGISTRY.values() if s.always_run or s.name in routing.run]

    outputs = {}
    for spec in to_run:
        kwargs = {"deps": text} if spec.needs_deps else {}
        outputs[spec.name] = spec.agent.run_sync(text, **kwargs).output

    return {"note_id": note_id, "routed": routing.run, "routing_reason": routing.reason, **outputs}


# Evaluation: agreement with the human coder -------------------------------------------------
def cohens_kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return float("nan") if expected == 1 else (observed - expected) / (1 - expected)


def evaluate(results: list[dict]) -> None:
    ids = [r["note_id"] for r in results]
    print("\n=== Evaluation against the gold standard ===")

    print("\nCoder: agreement per code (each note scored present/absent)")
    for code in CODEBOOK:
        human = [code in GOLD[i]["codes"] for i in ids]
        model = [any(c.code == code for c in r["coder"].codes) for r in results]
        agree = sum(h == m for h, m in zip(human, model)) / len(ids)
        print(f"  {code:<24} agreement {agree:5.0%}   kappa {cohens_kappa(human, model):5.2f}")

    human = [GOLD[i]["safety"] for i in ids]
    model = [bool(r.get("safety_screener") and r["safety_screener"].possible_safety_event)
             for r in results]
    caught = sum(h and m for h, m in zip(human, model))
    false_alarms = sum(m and not h for h, m in zip(human, model))
    print(f"\nSafety (router + screener): caught {caught} of {sum(human)} true events, "
          f"{false_alarms} false alarms")

    correct = sum(r["extractor"].follow_up_planned == GOLD[r["note_id"]]["follow_up"] for r in results)
    print(f"Extractor: follow_up_planned correct for {correct} of {len(results)} notes")


# Run ----------------------------------------------------------------------------------
if __name__ == "__main__":
    results = []
    for note_id, text in NOTES.items():
        result = process_note(note_id, text)
        results.append(result)

        codes = [c.code for c in result["coder"].codes]
        safety = result.get("safety_screener")
        print(f"\n{note_id}  routed to: {result['routed'] or 'no optional subagents'}")
        print(f"  codes: {codes}")
        print(f"  follow-up planned: {result['extractor'].follow_up_planned}")
        if safety:
            print(f"  safety: {safety.event_type} ({safety.reason})")

    evaluate(results)

    # Save everything so you can explore it in Positron (e.g. pd.read_json)
    serializable = [
        {k: (v.model_dump(mode="json") if isinstance(v, BaseModel) else v) for k, v in r.items()}
        for r in results
    ]
    with open("field_notes_results.json", "w") as f:
        json.dump(serializable, f, indent=2)
    print("\nFull results saved to field_notes_results.json")
