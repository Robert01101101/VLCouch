---
name: generate-commit-message
description: >-
  Draft human-readable, well-structured git commit messages from staged or
  unstaged changes. Use when the user asks for a commit message, wants help
  summarizing changes before committing, or before running git commit.
---

# Generate commit messages

Produce commit messages that are easy to scan in `git log`, understandable without opening the diff, and friendly to screen readers and non-native English readers.

## When to use

- User asks to write, draft, suggest, or improve a commit message
- User is about to commit and has not provided a message
- User asks to summarize changes for a commit or PR

When the user only wants a message (not an actual commit), output the message in a fenced code block they can copy.

When committing, follow the user's git safety rules separately; this skill covers **message content and structure only**.

## Workflow

1. **Gather context** (run in parallel when possible):
   ```powershell
   git status
   git diff
   git diff --staged
   git log --oneline -10
   ```
2. **Identify intent**: bug fix, new feature, refactor, test, docs, chore, or mixed
3. **Group changes** by user-visible or developer-visible outcome — not by file list
4. **Draft** using the template below
5. **Validate** with the checklist before presenting or committing

## Message structure

Use this layout every time. Blank line between sections is required.

```
<subject line>

<summary paragraph>

Changes:
- <outcome-focused bullet>
- <outcome-focused bullet>

<optional footer>
```

### Subject line

| Rule | Detail |
|------|--------|
| Length | Aim for 50–72 characters; hard max 72 |
| Voice | Imperative mood: "Add", "Fix", "Remove", "Update" — not "Added" or "Adds" |
| Content | State **what** changed at a high level; save **why** for the body |
| Scope | Optional `type(scope):` prefix when it aids scanning (see types below) |
| Avoid | File names, ticket noise, trailing period, vague words ("misc", "stuff", "WIP") |

**Types** (use when helpful, not mandatory): `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `build`, `ci`

### Summary paragraph

One or two short sentences in plain language:

- **Why** the change was made (problem, goal, or user impact)
- Readable on its own if someone only sees the subject + this paragraph

### Changes bullets

- One bullet per **logical change**, not per file touched
- Describe **outcome**, not implementation detail ("Watch API returns resume position" not "edited watch_service.py")
- Max 5 bullets; merge minor edits into one bullet
- Parallel grammar (all start with verbs or all noun phrases)

### Optional footer

Use only when relevant:

- `Breaking change:` — what broke and migration path
- `Refs #123` — issue link when user provides a ticket
- Test note: `Verified with .\scripts\test.ps1 -Layer api` when tests were run

## Accessibility and readability

- **Plain language** — avoid jargon unless the audience is clearly expert-only
- **No emoji** — meaning must not depend on symbols
- **No ALL CAPS** for emphasis
- **Expand acronyms** on first use in the body (e.g., "end-to-end (E2E)")
- **One idea per sentence**; keep paragraphs to 1–3 sentences
- **Subject stands alone** — many tools show only the first line
- **Consistent terms** — pick one word (endpoint vs route, component vs widget) and stick to it

## Quality checklist

Before finalizing:

- [ ] Subject is imperative, under 72 chars, and describes the main outcome
- [ ] Body explains *why*, not just *what*
- [ ] Bullets are grouped by outcome, not file path
- [ ] No secrets, credentials, or `.env` values in the message
- [ ] Message matches actual diff (re-read `git diff` if unsure)
- [ ] Tone matches recent `git log` style when the repo has established patterns

## Anti-patterns

| Avoid | Prefer |
|-------|--------|
| `fix stuff` | `fix(watch): resume playback from saved position` |
| `update files` | `feat(ui): show continue-watching row on home` |
| Long subject with commas | Short subject; detail in body |
| `WIP` / `checkpoint` | Wait until changes are coherent, or split commits |
| Listing every filename | Group by feature or fix |

## Examples

See [examples.md](examples.md) for full before/after samples.

**Minimal fix:**

```
fix(watch): restore saved playback position on resume

Episodes were always starting from the beginning because the watch
API ignored the stored position.

Changes:
- Return resume offset from GET /api/watch/status
- Pass start time to VLC when launching playback
```

**Feature with tests:**

```
feat(shows): add continue-watching section on show detail

Users can pick up the last unwatched episode without hunting the list.

Changes:
- Add continue-watching API helper and ShowDetail section
- Cover empty and in-progress states in component tests
```

## Mixed or large diffs

If changes span unrelated concerns:

1. Tell the user the diff should be **split into separate commits**
2. Propose one message per logical commit
3. Do not force a single message over unrelated work
