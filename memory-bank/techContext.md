# Tech Context

## Repository & Environment

- Repository: `LalaIAm/deck-builder`
- Local path: `c:/Users/lthor/OneDrive/amor-fati-img/deck-builder`
- OS: Windows 11
- Editor: VS Code

## Planned Technology Direction

- **Primary capability**: Autonomous generation pipeline for 78 tarot cards
- **Model interactions**: Text and image model API calls, with structured JSON outputs
- **Execution style**: Sequential orchestration with bounded retries
- **Artifacts**: Per-card image outputs + metadata/evaluation manifests

## Tooling Available in Environment

- Git/GitHub CLI (`git`, `gh`)
- JavaScript ecosystem (`node`, `npm`)
- Python ecosystem (`python`, `pip`)
- Common CLI utilities (`curl`, `sqlite3`)

## Technical Constraints (Current)

- Runtime stack not finalized (Node-first vs Python-first orchestration)
- API and schema contracts still to be defined in code
- No production storage/deployment architecture finalized yet

## Early Conventions

- Prefer explicit JSON contracts between pipeline stages
- Track every attempt with reproducible metadata
- Keep retry behavior deterministic and observable
