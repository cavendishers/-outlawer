# Documentation Workflow

## Goal

Keep implementation progress and documentation aligned by requiring manual status updates after each completed phase.

## Core Rule

When a phase is completed, verified, or materially changed, manually update the related documentation in the same branch before considering the phase closed.

## Required Manual Update Points

Always review and update these files when relevant:

- `README.md`
- `AGENTS.md`
- `docs/development-phases.md`
- the domain document that changed, such as:
  - `docs/api-contract.md`
  - `docs/database-design.md`
  - `docs/ai-extraction-format.md`
  - `docs/deployment.md`
  - `docs/migration-guide.md`

## Phase Status Workflow

For each phase in `docs/development-phases.md`:

1. change `Status` from `TODO` to `IN_PROGRESS` when work starts
2. change `Status` to `BLOCKED` if delivery is paused by a blocker
3. change `Status` to `DONE` only after implementation and verification are complete
4. update the listed related documents for that phase

## Verification Before Marking DONE

Before marking a phase `DONE`, confirm:

- required code is merged or ready
- migrations exist for schema changes
- tests or verification steps were run
- relevant docs reflect current reality

## Documentation Discipline

- do not mark a phase complete if the docs still describe the old design
- do not skip migration documentation when schema changed
- do not skip API contract updates when endpoint behavior changed
- do not overwrite architecture docs with guesses; reflect implemented behavior

## Recommended Commit Hygiene

When a phase is finished, include both:

- implementation changes
- documentation status updates

This keeps the repository history aligned with real delivery progress.
