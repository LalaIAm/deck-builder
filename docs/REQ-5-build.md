# 📝 Multimodal evaluation agent (REQ-5) — Build

**Short ID:** REQ-5  
**Status:** PLANNED  
**URL:** https://app.braingrid.ai/requirements/overview?id=ad24ec1c-1cd8-49d3-be22-8debd4c2f7d8

---

## Tasks (implementation order)

| #   | Task                                                                                                                                   | Status  | Blocked by |
| --- | -------------------------------------------------------------------------------------------------------------------------------------- | ------- | ---------- |
| 1   | **YAML agent & task config** — `config/agents.yaml` + `config/tasks.yaml` (evaluator_agent, evaluate_image_task)                       | PLANNED | —          |
| 2   | **evaluator_agent** — `@agent` in `crew.py`, llm=gpt-4o, output_json=EvaluationVerdict                                                 | PLANNED | 1          |
| 3   | **evaluate_image_task** — `@task` in `crew.py`: vision call via `openai.OpenAI()`, prompt construction, pass/fail override             | PLANNED | 2          |
| 4   | **Error handling, context wiring** — context=[generate_image_task], RuntimeError with card_id/attempt_number, full acceptance criteria | PLANNED | 3          |

---

## Summary

- **Goal:** Implement evaluator agent + `evaluate_image_task` that score a tarot
  card PNG with gpt-4o vision and return a validated `EvaluationVerdict` JSON
  (pass/fail, subscores, prompt_patch) for REQ-6/REQ-7.
- **Config:** Add `evaluator_agent` and `evaluate_image_task` in YAML;
  agent/task in `crew.py` use `EvaluationVerdict`, gpt-4o.
- **Vision:** Load PNG as base64, call
  `openai.OpenAI().chat.completions.create(model="gpt-4o", messages=[image_url + text])`
  directly (same pattern as REQ-4); parse JSON → Pydantic; apply Python
  pass/fail override.
- **Pass/fail:** `overall_score = mean(subscores)`; artifact = LLM said
  `passed=False` but `overall_score >= 7`; final
  `passed = (overall_score >= 7) and (not artifact)`.

Full requirement content and acceptance criteria are in BrainGrid; run
`braingrid requirement show REQ-5` for the full spec.
