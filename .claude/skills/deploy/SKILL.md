# Skill: deploy

Build, deploy, and smoke-test the application.

## Trigger

Use when the user says: "deploy", "ship it", "push to <env>", or "deploy to <env>".

## Behavior

1. Confirm the target environment if not specified (`staging` | `production`).
2. Run pre-deploy checks (lint, type-check, tests).
3. Execute `deploy.sh <environment>`.
4. Run `smoke-test.sh <environment>` to verify the deployment.
5. Report success or failure with a summary.

## Usage

```
/deploy [staging|production]
```

## Notes

- Never deploy to `production` without running smoke tests against `staging` first.
- If any pre-deploy check fails, abort and report the failure — do not skip checks.
- Deployment logs are written to `.claude/deploy.log` (gitignored).
