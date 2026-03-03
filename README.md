# Tarot Deck Generator

An autonomous, AI-driven system that generates a complete, stylistically cohesive 78-card tarot deck using a CrewAI multi-agent pipeline.

## Setup

### 1. Install dependencies

Requires Python 3.11+. Uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and populate the required keys:

| Key                 | Description                           |
| ------------------- | ------------------------------------- |
| `OPENAI_API_KEY`    | Your OpenAI API key                   |
| `OPENAI_MODEL_NAME` | Model for text agents (e.g. `gpt-4o`) |

### 3. Run the pipeline

```bash
crewai run
```

---

## Configuration

Edit `config/settings.yaml` to control pipeline behavior:

| Key              | Default           | Description                                                                        |
| ---------------- | ----------------- | ---------------------------------------------------------------------------------- |
| `model`          | `gpt-4o`          | LLM used by text-based agents (concept, prompt, evaluator, repair, orchestrator) |
| `image_model`    | `gpt-image-1`     | Model used by the image generation agent                                           |
| `max_retries`    | `3`               | Maximum generation + evaluation attempts per card before accepting the best result |
| `output_path`    | `output/`         | Directory where generated PNGs and the results manifest are written                |
| `card_spec_path` | `data/cards.json` | Path to the bundled 78-card JSON spec (do not modify unless using a custom deck) |

Environment overrides for path resolution:
- `TAROT_CONFIG_PATH`: absolute/relative path to `settings.yaml`
- `TAROT_CARDS_PATH`: absolute/relative path to `cards.json`

---

## Output

After a successful run, the `output/` directory will contain:

```text
output/
|-- images/
|   |-- major_00_the_fool.png
|   |-- major_01_the_magician.png
|   `-- ... (78 PNGs total)
`-- manifest.json
```

`manifest.json` maps each `card_id` to its generation result:

```json
{
  "major_00": {
    "concept": { "...": "..." },
    "initial_prompt": "...",
    "best_attempt_path": "output/images/major_00_the_fool.png",
    "total_attempts": 2,
    "final_verdict": {
      "pass": true,
      "subscores": { "...": 0.0 },
      "rule_checks": { "no_text_artifacts": true },
      "reasons": [],
      "prompt_patch": "",
      "failure_mode": "none"
    }
  }
}
```

---

## Project Structure

```text
tarot_deck_generator/
|-- pyproject.toml          # uv project config + crewai run entry point
|-- .env.example            # Required environment variable template
|-- config/
|   `-- settings.yaml       # Pipeline configuration knobs
|-- data/
|   `-- cards.json          # Bundled 78-card tarot spec
|-- output/                 # Generated images + manifest (gitignored)
`-- src/
    `-- tarot_deck_generator/
        |-- crew.py         # CrewAI crew class + run() entry point
        |-- models.py       # Pydantic data contracts for inter-agent communication
        `-- config/
            |-- agents.yaml # Agent role/goal/backstory definitions
            `-- tasks.yaml  # Task descriptions + agent assignments
```

---

## Agents

| Agent                | Role                                                             |
| -------------------- | ---------------------------------------------------------------- |
| `style_bible_agent`  | Generates the Deck Style Bible JSON (once per run)              |
| `concept_agent`      | Generates per-card visual concept JSON                           |
| `prompt_agent`       | Converts concept JSON to image generation prompt string          |
| `image_agent`        | Calls OpenAI image API, returns PNG reference                    |
| `evaluator_agent`    | Scores image against concept + style bible, returns verdict JSON |
| `repair_agent`       | Revises failing prompts with escalating simplification           |
| `orchestrator_agent` | Coordinates the full 78-card pipeline                            |
