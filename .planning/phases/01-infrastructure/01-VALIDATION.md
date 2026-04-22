---
phase: 1
slug: infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-19
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — Phase 1 is a single Python file; all verification is via CLI invocation and grep |
| **Config file** | none |
| **Quick run command** | `python -c "import organizer; print('OK')"` |
| **Full suite command** | `python organizer.py --help 2>&1; python -c "import organizer; print('OK')"` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -c "import organizer; print('OK')"`
- **After every plan wave:** Run full import + grep checks below
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01 | 1 | INFRA-01, INFRA-03, INFRA-04, INFRA-05, INFRA-06, INFRA-07 | — | Executor.move blocks ROM/ISO and system paths; never calls shutil.move on blocked files | import-check + grep | `python -c "import organizer; e=organizer.Executor(dry_run=False); print(organizer.is_no_touch('a.iso'))"` | ❌ W0 | ⬜ pending |
| 01-01-T2 | 01 | 1 | INFRA-02, INFRA-08, MENU-01 | — | select_drive exits cleanly when no drives found; show_menu input loop rejects invalid selections | import-check + grep | `python -c "import organizer; print(organizer.setup_console_logging())"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `organizer.py` must be importable after Task 1 completes (syntactically valid, no NameErrors at import time)
- [ ] All grep acceptance criteria from plan Task 1 must pass before Task 2 begins

*Wave 0 is lightweight — no test framework install needed. All verification is via `python -c "import organizer"` and grep.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Removable drive listing on live Windows machine | INFRA-01 | Requires a physical USB/SD card inserted | Insert removable drive, run `py organizer.py`, verify drive appears in numbered list |
| Auto-select single drive (D-01) | INFRA-02 | Requires exactly one removable drive attached | Insert one drive only, run `py organizer.py`, verify it auto-selects without prompting |
| Exit on no drives (D-02) | INFRA-02 | Requires no removable drives attached | Remove all drives, run `py organizer.py`, verify Spanish error message and clean exit |
| Log file created at `<drive>\_organizer_logs\` | INFRA-08 | Requires drive selection at runtime | Select a drive, verify `_organizer_logs\organizer.log` is created on the selected drive |

---

## must_haves Truth Verification Map

Maps each `must_haves.truths` entry from 01-01-PLAN.md to the command that confirms it post-execution:

| Truth | Verification Command |
|-------|---------------------|
| Script lists all removable drives and asks user to pick | Manual — see table above |
| Non-existent option rejected with re-prompt | Manual — run script, enter invalid number |
| No drives → Spanish error + clean exit | Manual — see table above |
| File with NO_TOUCH_EXTS extension blocked at Executor.move() | `python -c "import organizer; e=organizer.Executor(dry_run=False); r=e.move(organizer.Path('x.iso'), organizer.Path('y')); assert r is None, r"` |
| Path with SKIP_PATH_PARTS substring blocked at Executor.move() | `python -c "import organizer; e=organizer.Executor(dry_run=False); r=e.move(organizer.Path('System Volume Information\\\\x'), organizer.Path('y')); assert r is None"` |
| dry_run=True logs intent and returns path without touching filesystem | `python -c "import organizer; e=organizer.Executor(dry_run=True); p=organizer.Path('organizer.py'); r=e.move(p, organizer.Path('nowhere\\\\organizer.py')); assert r is not None"` |
| Colliding destination gets (2), (3)... suffix not overwrite | `grep -n "_free_path" organizer.py` and `grep -n "stem" organizer.py` |
| Numbered menu with 4 stubs + exit (0) after drive selection | Manual — run script, verify menu |
| Log file created at `<drive>\_organizer_logs\` after drive selection | Manual — see table above |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
