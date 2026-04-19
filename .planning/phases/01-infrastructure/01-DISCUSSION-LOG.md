# Phase 1: Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 01-infrastructure
**Areas discussed:** Drive selection UX

---

## Drive Selection UX

### Single drive found

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-select silently | Print "Usando F:\ (NOMBRE)" and go to menu — no prompt | ✓ |
| Auto-select with confirmation | Show drive and wait for Enter | |
| Always prompt | Show selection list even with one option | |

**User's choice:** Auto-select silently
**Notes:** Fastest path for the common case.

---

### No drives found

| Option | Description | Selected |
|--------|-------------|----------|
| Show error and exit | Print clear message and close | ✓ |
| Ask for manual path | Prompt user to type a drive letter manually | |
| Retry loop | Wait and retry, print waiting message | |

**User's choice:** Show error and exit
**Notes:** Simple and safe.

---

### Multiple drives found — display format

| Option | Description | Selected |
|--------|-------------|----------|
| Letter + label + size | "1) F:\ MEDIOS (931 GB)" | ✓ |
| Letter + label only | "1) F:\ MEDIOS" | |
| Letter only | "1) F:\" | |

**User's choice:** Letter + label + size
**Notes:** Enough info to pick confidently without clutter.

---

## Areas Not Discussed (user skipped)

- **Menu shell completeness** — left to Claude's discretion
- **Safety block verbosity** — left to Claude's discretion

## Claude's Discretion

- Menu placeholder entries for Phase 2-4 features
- ROM/ISO skip verbosity (silent count vs. per-item warning)
- Internal code structure within single .py file
- Logging configuration details

## Deferred Ideas

None.
