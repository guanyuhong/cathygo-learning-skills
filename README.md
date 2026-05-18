# CathyGO Learning Skills Marketplace

This repository is the official CathyGO Learning Skills marketplace. It is not a general software template repository: it is a curated collection of self-contained education Skills for AI Tutor and CathyGO Agent workflows.

## What is CathyGO Learning Skills

A CathyGO Learning Skill is a small, installable education capability. Each Skill lives in its own folder and contains at least a `SKILL.md` file. A Skill may also include structured learning references, assets, scripts, and eval cases.

CathyGO Learning Skills are designed to help an AI Tutor:

- explain concepts with age-appropriate language;
- generate clean-room practice questions;
- check learner answers with actionable feedback;
- diagnose learning barriers;
- keep only appropriate learning memory;
- deliver original comic-style lessons without copying textbook material.

## Repository structure

```text
cathygo-learning-skills/
  .claude-plugin/
    marketplace.json
  .github/
    workflows/
      validate.yml
  skills/
    common-concept-explain/
    common-quiz-generate/
    common-answer-check/
    math-grade7b-fraction-concept-explain/
    math-grade7b-fraction-domain-diagnosis/
    cathygo-skill-creator/
  spec/
    cathygo-learning-skill-spec.md
  template/
    learning-skill/
  tools/
    cathygo.py
```

Every Skill directory must be self-contained. A consumer should be able to install one Skill folder and understand its purpose, references, evals, and usage rules without reading unrelated folders.

## How to install plugins

Add this marketplace:

```bash
/plugin marketplace add guanyuhong/cathygo-learning-skills
```

Install a plugin:

```bash
/plugin install common-tutor-skills@cathygo-learning-skills
/plugin install math-grade7b-fraction@cathygo-learning-skills
/plugin install cathygo-authoring-skills@cathygo-learning-skills
```

Run local validation before publishing changes:

```bash
python -m pip install -r requirements.txt
python tools/cathygo.py list
python tools/cathygo.py validate
```

## Available plugins

| Plugin | Purpose | Skills |
| --- | --- | --- |
| `common-tutor-skills` | Common tutor behaviors that can be reused across subjects. | `common-concept-explain`, `common-quiz-generate`, `common-answer-check` |
| `math-grade7b-fraction` | First demo plugin for Grade 7B algebraic fraction learning. | `math-grade7b-fraction-concept-explain`, `math-grade7b-fraction-domain-diagnosis` |
| `cathygo-authoring-skills` | Authoring support for creating new CathyGO Learning Skills. | `cathygo-skill-creator` |

## How to create a learning skill

1. Copy `template/learning-skill/` to `skills/<new-skill-name>/`.
2. Rename the Skill folder with lowercase words separated by hyphens.
3. Edit `SKILL.md` frontmatter:
   - `name` must exactly match the parent folder name.
   - `description` must clearly say when to trigger the Skill and when not to trigger it.
4. Fill the reference files with original learning content, barriers, assessment items, memory rules, and optional comic lesson scripts.
5. Add `evals/eval_cases.jsonl` with representative tutor scenarios.
6. Add the Skill path to `.claude-plugin/marketplace.json` when it should be installable.
7. Run `python tools/cathygo.py validate`.

## Clean-room authoring policy

All public content in this repository must be clean-room authored.

Do not commit:

- textbook PDFs;
- textbook screenshots or scans;
- copied textbook prose;
- copied textbook examples;
- publisher images, page layouts, watermarks, or diagrams;
- copyrighted worksheet images or answer keys.

Allowed content includes original explanations, original assessment items, general mathematical or educational facts, and references written from scratch by contributors. When a Skill covers a textbook-aligned topic, express the concept in CathyGO's own words and use original examples.

## First demo: math-grade7b-fraction

The first demo plugin is `math-grade7b-fraction`. It focuses on Grade 7B algebraic fractions and includes:

- concept explanation for algebraic fractions;
- domain restriction guidance such as "a denominator cannot be zero";
- diagnosis of common barriers like invalid cancellation and missing domain checks;
- original comic lesson ideas using scenes such as "Denominator Gate" and "Variable Courier X".

Install it with:

```bash
/plugin install math-grade7b-fraction@cathygo-learning-skills
```
