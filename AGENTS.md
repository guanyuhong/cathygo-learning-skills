# Repository Instructions for Codex

This repository is the CathyGO Learning Skills marketplace. Keep it focused on learning Skill packages, marketplace metadata, documentation, validation, and small helper scripts.

## Source & Rights Policy

- All public content must satisfy Source & Rights Policy.
- Do not commit unlicensed textbook PDFs.
- Do not commit unlicensed textbook screenshots, scans, page captures, or page-layout recreations.
- Do not commit copied textbook prose, copied textbook examples, answer keys, or publisher images without rights.
- Allowed sources include original CathyGO content, public subject facts, curriculum topic maps, public domain content, open licensed content, and licensed reference materials.

## Skill structure

- Every Skill directory must be self-contained.
- Every Skill directory must contain `SKILL.md`.
- `SKILL.md` frontmatter must contain `name` and `description`.
- `name` must exactly match the parent directory name.
- `description` must clearly explain when the Skill should trigger and when it should not trigger.
- Skill support files should live under the same Skill folder, commonly in `references/`, `assets/`, `scripts/`, and `evals/`.
- Every public Skill must include `evals/eval_cases.jsonl`.

## Evolution governance rules

- Do not create one-session-one-skill micro-skills.
- Default to class-level umbrella skills and broaden existing Skills before introducing new ones.
- Put new operational and knowledge content in `references/` first; keep `SKILL.md` concise.
- Any Skill update must include corresponding `evals/` updates.
- Official Skills are never directly mutated by agent runtime.
- Agent-generated changes must be represented as proposals first.

## Validation

After modifying Skill content, marketplace metadata, templates, specs, or validation code, run:

```bash
python tools/cathygo.py list
python tools/cathygo.py validate
python tools/cathygo.py eval
```
