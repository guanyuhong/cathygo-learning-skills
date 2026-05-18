---
name: cathygo-skill-creator
description: Use when creating, reviewing, or refactoring a CathyGO Learning Skill with SKILL.md, references, evals, and marketplace metadata. Do not use for generic app development or for copying textbook material into a Skill.
---

# CathyGO Skill Creator

Use this Skill to help authors create new CathyGO Learning Skills.

## Workflow

1. Choose a lowercase hyphenated Skill name.
2. Copy `template/learning-skill/` into `skills/<skill-name>/`.
3. Write `SKILL.md` frontmatter with matching `name` and a trigger-focused `description`.
4. Fill references with original CathyGO-authored learning content.
5. Add eval cases that cover the target behavior and clean-room boundaries.
6. Add the Skill to `.claude-plugin/marketplace.json` only when it should be installable.
7. Run `python tools/cathygo.py validate`.

## Authoring rules

- Keep each Skill self-contained.
- Prefer structured YAML references for learning content.
- Keep examples short and original.
- Do not import textbook PDFs, screenshots, copied examples, or publisher images.
