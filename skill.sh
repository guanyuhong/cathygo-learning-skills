#!/usr/bin/env bash

declare -A SKILLS=(
  [cathygo-knowledge-map]="skills/cathygo-knowledge-map/SKILL.md"
  [cathygo-learning-pack]="skills/cathygo-learning-pack/SKILL.md"
  [cathygo-qij-question]="skills/cathygo-qij-question/SKILL.md"
)

if [[ $# -eq 0 ]]; then
  echo "Usage: source ./skill.sh <skill-name>"
  echo "Available skills: ${!SKILLS[@]}"
  return 0 2>/dev/null || exit 0
fi

if [[ -z "${SKILLS[$1]}" ]]; then
  echo "Unknown skill: $1" >&2
  echo "Available skills: ${!SKILLS[@]}" >&2
  return 1 2>/dev/null || exit 1
fi

echo "${SKILLS[$1]}"
