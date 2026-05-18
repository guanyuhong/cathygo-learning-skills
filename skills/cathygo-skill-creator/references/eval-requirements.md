# Eval Requirements

Every public Skill must include `evals/eval_cases.jsonl`.

Each line should be a JSON object. Recommended fields:

- `id`
- `input`
- `expected_behavior`
- `must_not`

Include cases for:

- normal trigger;
- boundary where the Skill should not trigger;
- clean-room compliance;
- at least one learner mistake or misconception.
