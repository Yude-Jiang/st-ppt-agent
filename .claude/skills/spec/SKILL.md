# Skill: spec

Generate or update a functional specification for a feature.

## Trigger

Use when the user says: "write a spec for X", "spec out X", or "draft a spec".

## Behavior

1. Read `DOMAIN.md` and `CLAUDE.md` to understand domain rules and constraints.
2. Ask clarifying questions if the feature scope is ambiguous (max 3 questions).
3. Write the spec to `docs/explorations/<feature-slug>.md` using the structure below.
4. Summarize what was written and what open questions remain.

## Output Structure

```markdown
# Spec: <Feature Name>

## Problem
<!-- One paragraph: what pain does this solve and for whom? -->

## Goals
- [ ] Goal 1
- [ ] Goal 2

## Non-Goals
- What this feature explicitly does NOT do.

## Proposed Solution
<!-- Narrative description + key design decisions. -->

## Data Model Changes
<!-- New or modified entities, fields, relations. -->

## API / Interface Changes
<!-- New endpoints, events, or UI surfaces. -->

## Open Questions
- [ ] Question 1
```

## Notes

- Keep specs in `docs/explorations/` until the feature is shipped.
- Reference the spec from the relevant GitHub issue if one exists.
