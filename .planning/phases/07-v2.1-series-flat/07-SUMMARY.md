# Phase 7 Summary: v2.1 — Series Sin Subcarpetas de Temporada

**Phase:** 07-v2.1-series-flat
**Status:** complete
**Completed:** 2026-04-22

## What Was Changed

Modified `organize_videos_and_games()` to place all series episodes directly in `Series\<Show>\` without creating `Temporada X` subfolders.

**Before:**
```
Series\
  Breaking Bad\
    Temporada 1\
      Breaking Bad - Temporada 1 - Episodio 1.mp4
      ...
    Temporada 2\
      Breaking Bad - Temporada 2 - Episodio 1.mp4
```

**After:**
```
Series\
  Breaking Bad\
    Breaking Bad - Temporada 1 - Episodio 1.mp4
    Breaking Bad - Temporada 2 - Episodio 1.mp4
    ...
```

## What Stayed the Same

- Movies: `Peliculas\<Titulo (Ano)>\` (unchanged)
- All other organization features (games, docs, subtitles, empty cleanup)
- Undo log and dry-run behavior

## Files Modified

- `organizer.py` — Line 538: changed `dst_dir = drive_root / "Series" / show / f"Temporada {season}"` to `dst_dir = drive_root / "Series" / show`
- `.planning/REQUIREMENTS.md` — ORG-01 updated
- `.planning/ROADMAP.md` — Phase 7 marked complete
- `.planning/STATE.md` — milestone updated to v2.1

## Decision

All episodes of a series are now grouped in a single folder. This makes it easier to browse and play episodes without navigating season subfolders.