# Active Context

## Current Focus

Initialize and baseline the Memory Bank so future sessions can recover full project
context after memory resets.

## Recent Changes

- Established `projectbrief.md` with core product definition and scope.
- Added `productContext.md` describing product intent, users, and UX goals.
- Created remaining core Memory Bank files for architecture, technical context,
  active work tracking, and progress status.

## Immediate Next Steps

1. Implement the first runnable end-to-end pipeline skeleton (Style Bible -> Concept ->
   Prompt -> Image -> Evaluation -> Retry -> Manifest).
2. Define data contracts (JSON schemas) for style bible, card concept, evaluator output,
   and manifest records.
3. Stand up deterministic logging and artifact folder conventions for all 78 cards.

## Open Decisions / Uncertainties

- Exact runtime stack choice (Python-first orchestration vs Node-first orchestration).
- Strategy for model call abstraction, retries, and idempotency.
- Storage approach for generated artifacts and metadata (local FS vs object store).
