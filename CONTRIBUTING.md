# Contributing

## Workflow

1. Create a focused branch for one change set.
2. Keep commits atomic and descriptive using Conventional Commits.
3. Run the relevant validation for the area you touched before opening a pull request.
4. Update documentation when behavior, setup, or operational expectations change.

## Pull Request Checklist

- Explain the user-facing or operator-facing impact.
- Link related planning notes, issues, or roadmap steps when available.
- Avoid bundling refactors with functional fixes.
- Confirm no secrets, certificates, or local environment files were introduced.

## Local Expectations

- Use `dicom_guardian/Makefile` targets for Python setup and checks.
- Use `dicom_ui/Makefile` or workspace `npm` commands for UI setup and checks.
- Prefer small reversible changes over broad repository rewrites.
