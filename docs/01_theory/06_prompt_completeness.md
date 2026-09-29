# Prompt Completeness Heuristic

## Purpose

The Speedometer may show whether an individual prompt explicitly covers four specification dimensions. This is an interaction-quality observation, not task progress, semantic correctness, or proof that Claude understood the request.

## Definition

For prompt `p`, evaluate four binary checklist indicators:

- `g(p)`: an explicit goal/action is present.
- `c(p)`: at least one constraint is present.
- `d(p)`: an expected deliverable/result is named.
- `a(p)`: acceptance criteria, tests, or checks are named.

```text
Q_prompt(p) = (g(p) + c(p) + d(p) + a(p)) / 4
```

Each indicator has weight `0.25`, so `Q_prompt ∈ {0, 0.25, 0.5, 0.75, 1}`. The UI should show the four flags alongside the score.

## Operational interpretation

The initial implementation uses a deterministic, transparent cue-word heuristic for Russian and English. It reports cue coverage only; it does not evaluate ambiguity, correctness, feasibility, tone, or whether the requirements conflict. A low score means that some rubric cues were not detected, not necessarily that the prompt was poor. Missing/empty text is `not assessable`, not a zero-quality judgment.

`Q_prompt` is stored with the conversation observation. It must not modify requirement `q_i`, verifier evidence, `D_completion`, `D_cost`, `U_D`, or `goal_reached`. Only the task's verifiers determine completion. No LLM judge or extra API call is used.

## Calibration

The cue dictionary and weights are a starting heuristic. Evaluate them against user-labeled prompts before using the score for recommendations. Keep the raw item flags and version the rubric if its cues/weights change, so historical scores remain interpretable.
