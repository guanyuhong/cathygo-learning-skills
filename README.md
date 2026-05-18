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
    math-grade7b-cn-zj-s2-course-guide/
    math-grade7b-cn-zj-s2-ch01-lines-and-parallels/
    math-grade7b-cn-zj-s2-ch02-equation-systems/
    math-grade7b-cn-zj-s2-ch03-polynomial-ops/
    math-grade7b-cn-zj-s2-ch04-factorization/
    math-grade7b-cn-zj-s2-ch05-fractions/
    math-grade7b-cn-zj-s2-ch06-data-statistics/
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
/plugin install math-grade7b-cn-zj-s2@cathygo-learning-skills
/plugin install math-grade7b-cn-zj-s2-ch05-fractions@cathygo-learning-skills
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
| `math-grade7b-cn-zj-s2` | Full Grade 7B CN-ZJ semester 2 math course skeleton. | course guide plus 6 chapter Skills |
| `math-grade7b-fraction` | First demo plugin for Grade 7B algebraic fraction learning. | `math-grade7b-fraction-concept-explain`, `math-grade7b-fraction-domain-diagnosis` |
| `cathygo-authoring-skills` | Authoring support for creating new CathyGO Learning Skills. | `cathygo-skill-creator` |

## Available Math Grade 7B plugins

| Plugin | Scope |
| --- | --- |
| `math-grade7b-cn-zj-s2` | Full semester 2 course skeleton with common tutor Skills, course guide, and all chapter Skills. |
| `math-grade7b-cn-zj-s2-ch01-lines` | Chapter 1: intersecting lines, angle relationships, parallel lines, and translation. |
| `math-grade7b-cn-zj-s2-ch02-equation-systems` | Chapter 2: two-variable and three-variable linear equation systems. |
| `math-grade7b-cn-zj-s2-ch03-polynomial-ops` | Chapter 3: multiplication, formulas, simplification, and division of polynomials. |
| `math-grade7b-cn-zj-s2-ch04-factorization` | Chapter 4: meaning of factorization, common factor extraction, and formula-based factorization. |
| `math-grade7b-cn-zj-s2-ch05-fractions` | Chapter 5: algebraic fractions and fraction equations. |
| `math-grade7b-cn-zj-s2-ch06-data-statistics` | Chapter 6: data collection, charts, frequency, and histograms. |

Install examples:

```bash
/plugin install math-grade7b-cn-zj-s2@cathygo-learning-skills
/plugin install math-grade7b-cn-zj-s2-ch05-fractions@cathygo-learning-skills
```

## Course structure

The Grade 7B CN-ZJ semester 2 course skeleton uses clean-room topic maps for six chapters:

1. Intersecting Lines and Parallel Lines
2. Systems of Linear Equations
3. Polynomial Operations
4. Factorization
5. Algebraic Fractions
6. Data and Statistical Charts

The chapter maps are topic-aligned skeletons only. They do not contain textbook pages, copied explanations, copied exercise prompts, or publisher images.

## Level ladder

Course and chapter Skills use four learning levels:

- `C`: foundation repair for missing prerequisites and basic recognition.
- `B`: standard mastery for core procedures and routine checks.
- `A`: stable improvement with mixed tasks and explanation of reasoning.
- `A_plus`: stretch challenges that combine ideas or require strategic choices.

## Comic learning design

The course guide defines an original CathyGO comic world for each chapter, such as Geometry Detective Street, Equation Twin Cities, Polynomial Energy Factory, Factorization Workshop, Fraction City, and Data Detective Bureau.

Every comic lesson follows the same learning beat:

```text
hook -> intuition -> rule -> guided_example -> common_trap -> student_check -> recap -> next_mission
```

Comic scripts must use original CathyGO characters, scenes, dialogue, and visual descriptions. They must not copy textbook illustrations, page layouts, or publisher settings.

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

## Self-Growing SkillRepo Architecture

Official skills in this repository are **seed skills**. They provide stable, reviewed starting points for CathyGO tutoring workflows.

The repository supports a controlled skill evolution loop:

`Use -> Trace -> Detect Failure -> Propose -> Patch via Codex -> Validate -> Eval -> Review -> Promote -> Release`

Key governance rules:

- Skills evolve through traces, proposals, evals, review, and staged promotion.
- `cathygo-agent` can produce learning traces and improvement proposals, but it does not directly mutate official Skills.
- Accepted proposals are turned into pull requests by Codex Cloud workflows and reviewed before merge.
- Class-level umbrella Skills are preferred over one-session-one-skill micro-fragmentation.

## Official skills are seed skills

Official Skills are the curated baseline. Runtime learning should first produce evidence and proposals, then repository updates are applied through reviewable PRs.

## Skill evolution lifecycle

1. Use existing Skills in tutoring.
2. Capture trace data.
3. Detect failures or gaps.
4. Write a structured proposal.
5. Apply patch through Codex-based PR changes.
6. Run validate checks.
7. Run eval checks and case updates.
8. Human reviewers approve or request revision.
9. Promote status (`draft` -> `experimental` -> `community` -> `official`).
10. Release through marketplace metadata.

## Additional CLI examples

```bash
python tools/cathygo.py eval
python tools/cathygo.py inspect-skill math-grade7b-cn-zj-s2-ch05-fractions
python tools/cathygo.py proposals list
python tools/cathygo.py proposals validate evolution/proposals/example.yaml
```
