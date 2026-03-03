# System Patterns

## Intended Architecture

The system is designed as a sequential autonomous pipeline with explicit handoffs between
stages. Each stage reads structured input, produces structured output, and writes
artifacts for traceability.

1. **Style Bible Stage**: Generate global style and guardrail rules once per deck.
2. **Concept Stage**: Generate per-card concept JSON from tarot semantics + style rules.
3. **Prompt Stage**: Compile concept JSON into production image prompts.
4. **Image Stage**: Generate image output for each attempt.
5. **Evaluation Stage**: Score quality/compliance and return pass/fail + patch guidance.
6. **Repair Stage**: Apply bounded retry strategy until pass or max attempts.
7. **Manifest Stage**: Persist best attempt and metadata for every card.

## Core Design Principles

- **Structured contracts first**: JSON outputs between all stages.
- **Deterministic orchestration**: predictable execution order and retry policy.
- **Artifact completeness**: persist prompts, evaluations, and final outputs.
- **Guardrail enforcement**: ban text/logos/watermarks/anatomy errors.
- **Best-attempt preservation**: never lose highest-scoring result.

## Retry Pattern

- Attempt 1: Normal generation from baseline prompt.
- Attempt 2: Surgical prompt patch from evaluator feedback.
- Attempt 3+: Safe-mode simplification to reduce failure modes.
- Max retries enforced; best score retained if no full pass.
