# Skill: status-report

Generate a concise status report of the current session's progress.

## Trigger

Use when the user says: "status", "what's done", "give me a status report",
"what have we done so far", or "/status-report".

## Behavior

1. Read `PROGRESS.md` for recorded task history.
2. Run `git log --oneline -20` to see recent commits.
3. Run `git status` to see uncommitted changes.
4. Synthesize a report using the structure below.
5. Offer to update `PROGRESS.md` with the current state.

## Output Structure

```
## Status Report — <date>

### Completed this session
- [ item 1 ]
- [ item 2 ]

### In progress
- [ item ] — <what's left>

### Blocked / needs decision
- [ item ] — <what's needed>

### Next steps
1. ...
2. ...
```

## Notes

- Keep the report under 30 lines.
- Use bullet points, not paragraphs.
- If `PROGRESS.md` is empty, note that and offer to initialize it.
