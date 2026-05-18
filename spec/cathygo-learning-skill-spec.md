# CathyGO Learning Skill Specification

This document defines the minimum shape for a CathyGO Learning Skill.

## Skill folder

A Skill is a self-contained directory under `skills/`.

Minimum:

```text
skills/<skill-name>/
  SKILL.md
  evals/
    eval_cases.jsonl
```

Recommended:

```text
skills/<skill-name>/
  SKILL.md
  references/
  assets/
  scripts/
  evals/
    eval_cases.jsonl
```

The folder name must use lowercase words separated by hyphens. The folder should contain everything the Skill needs to explain its behavior and support evaluation.

## SKILL.md

`SKILL.md` is the Skill entry point. It must start with YAML frontmatter:

```yaml
---
name: example-learning-skill
description: Use when ... Do not use when ...
---
```

Requirements:

- `name` must exactly match the parent folder name.
- `description` must state when the Skill should trigger.
- `description` must state when the Skill should not trigger.
- The body should give concise operating instructions for the AI Tutor or CathyGO Agent.

## references/

`references/` contains structured knowledge used by the Skill. Common files include:

- `content-pack.yaml` for concepts, definitions, original explanations, and scope;
- `learning-barriers.yaml` for misconceptions, diagnostic signals, and interventions;
- `assessment-items.yaml` for original questions, rubrics, and answer expectations;
- `memory-policy.yaml` for what learner information may or may not be stored;
- `comic-lessons.yaml` for original comic lesson scripts.

References must be authored in original language. They may contain general facts, but not copied textbook expression.

## assets/

`assets/` is optional. It may contain original, rights-cleared assets only. Do not store textbook images, screenshots, scans, or publisher artwork.

The initial marketplace validator rejects common image file extensions to keep this repository clean until an explicit rights-cleared asset workflow is added.

## scripts/

`scripts/` is optional. Use it for small helper scripts that directly support the Skill, such as data normalization or eval generation. Do not add application services or CathyGO Agent runtime code here.

## evals/

Every public Skill must include:

```text
evals/eval_cases.jsonl
```

Each line should be a JSON object describing one evaluation case. Recommended fields:

- `id`
- `input`
- `expected_behavior`
- `must_not`

Eval cases should cover successful use, refusal or non-trigger boundaries, clean-room behavior, and common learner mistakes.

## Learning content

Learning content should be clear, age-appropriate, and aligned to the stated scope. It can include:

- concept goals;
- prerequisite knowledge;
- original explanations;
- original examples;
- tutor moves;
- language-level guidance.

## Assessment items

Assessment items must be original. They should include:

- prompt;
- intended skill target;
- expected answer or rubric;
- feedback guidance;
- difficulty level.

Do not copy textbook exercises, workbook prompts, test-bank questions, or publisher answer keys.

## Learning barriers

Learning barriers describe likely learner difficulties and how the tutor should respond. A barrier entry should include:

- learner signal;
- likely cause;
- diagnostic question;
- intervention;
- follow-up check.

## Memory policy

Memory policy defines what the tutor may remember about a learner. Recommended defaults:

- Store stable learning preferences only when useful.
- Store recurring misconceptions as learning support notes.
- Do not store private identity information, sensitive personal information, or unsupported psychological labels.
- Prefer short, updateable learning notes over permanent judgments.

## Comic lessons

Comic lessons are optional story-based learning scripts. They must use original characters, scenes, dialogue, and visual descriptions. They may explain general subject facts but must not recreate textbook illustrations or page layouts.

## Clean-room copyright policy

All content in a CathyGO Learning Skill must be clean-room authored.

Prohibited:

- textbook PDFs;
- textbook screenshots, scans, or photos;
- copied textbook prose;
- copied textbook examples;
- publisher diagrams, illustrations, mascots, or page layouts;
- copied answer keys or assessment banks.

Allowed:

- original explanations;
- original assessment items;
- general facts and standard terminology;
- rights-cleared or contributor-created assets after review;
- original comic scripts and original classroom scenarios.
