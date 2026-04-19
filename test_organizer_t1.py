"""
TDD RED — Task 1: Core engine tests.
These tests MUST fail before organizer.py Sections 1-7 are written.
"""
import sys
import tempfile
import os
from pathlib import Path
import importlib.util


def load_organizer():
    spec = importlib.util.spec_from_file_location(
        "organizer",
        Path(__file__).parent / "organizer.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- is_no_touch ----

def test_is_no_touch_iso():
    mod = load_organizer()
    assert mod.is_no_touch("movie.iso"), "iso must be blocked"


def test_is_no_touch_gba_uppercase():
    mod = load_organizer()
    assert mod.is_no_touch("GAME.GBA"), "GBA uppercase must be blocked"


def test_is_no_touch_cso():
    mod = load_organizer()
    assert mod.is_no_touch("archive.cso"), "cso (Ordenar.ps1 superset) must be blocked"


def test_is_no_touch_pbp():
    mod = load_organizer()
    assert mod.is_no_touch("archive.pbp"), "pbp must be blocked"


def test_is_no_touch_v64():
    mod = load_organizer()
    assert mod.is_no_touch("archive.v64"), "v64 must be blocked"


def test_is_no_touch_mkv_not_blocked():
    mod = load_organizer()
    assert not mod.is_no_touch("movie.mkv"), "mkv must NOT be blocked"


def test_is_no_touch_no_extension():
    mod = load_organizer()
    assert not mod.is_no_touch("nodot"), "no-extension file must NOT be blocked"


# ---- should_skip_path ----

def test_should_skip_system_volume_information():
    mod = load_organizer()
    assert mod.should_skip_path("F:\\System Volume Information\\foo"), \
        "System Volume Information must be skipped"


def test_should_skip_recycle_bin():
    mod = load_organizer()
    assert mod.should_skip_path("F:\\$RECYCLE.BIN\\foo.mkv"), \
        "$RECYCLE.BIN must be skipped"


def test_should_skip_normal_path_not_skipped():
    mod = load_organizer()
    assert not mod.should_skip_path("F:\\MEDIOS\\movie.mkv"), \
        "Normal media path must NOT be skipped"


# ---- _free_path ----

def test_free_path_non_existing_unchanged():
    mod = load_organizer()
    p = Path(tempfile.gettempdir()) / "does_not_exist_xyz123.mkv"
    result = mod._free_path(p)
    assert result == p, "_free_path must return path unchanged when it doesn't exist"


def test_free_path_collision_appends_2():
    mod = load_organizer()
    with tempfile.TemporaryDirectory() as tmpdir:
        existing = Path(tmpdir) / "movie.mkv"
        existing.touch()
        result = mod._free_path(existing)
        assert result.name == "movie (2).mkv", \
            f"Expected 'movie (2).mkv', got '{result.name}'"


def test_free_path_collision_appends_3():
    mod = load_organizer()
    with tempfile.TemporaryDirectory() as tmpdir:
        existing = Path(tmpdir) / "movie.mkv"
        existing.touch()
        existing2 = Path(tmpdir) / "movie (2).mkv"
        existing2.touch()
        result = mod._free_path(existing)
        assert result.name == "movie (3).mkv", \
            f"Expected 'movie (3).mkv', got '{result.name}'"


# ---- Executor ----

def test_executor_dry_run_returns_path_without_moving():
    mod = load_organizer()
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "safe.mkv"
        src.touch()
        dst = Path(tmpdir) / "subdir" / "safe.mkv"
        ex = mod.Executor(dry_run=True)
        result = ex.move(src, dst)
        assert result is not None, "dry_run move must return a Path"
        assert isinstance(result, Path), "returned value must be Path"
        assert not dst.exists(), "dry_run must NOT create the destination"


def test_executor_blocks_rom_extension():
    mod = load_organizer()
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "game.iso"
        src.touch()
        dst = Path(tmpdir) / "dest" / "game.iso"
        ex = mod.Executor(dry_run=False)
        result = ex.move(src, dst)
        assert result is None, "move of ROM/ISO must return None"


def test_executor_blocks_system_path():
    mod = load_organizer()
    with tempfile.TemporaryDirectory() as tmpdir:
        system_src = Path(tmpdir) / "System Volume Information" / "file.mkv"
        system_src.parent.mkdir(parents=True, exist_ok=True)
        system_src.touch()
        dst = Path(tmpdir) / "dest" / "file.mkv"
        ex = mod.Executor(dry_run=False)
        result = ex.move(system_src, dst)
        assert result is None, "move from system path must return None"


def test_executor_dry_run_attribute_mutable():
    mod = load_organizer()
    ex = mod.Executor(dry_run=True)
    assert ex.dry_run is True
    ex.dry_run = False
    assert ex.dry_run is False, "dry_run must be a mutable attribute"


if __name__ == "__main__":
    tests = [
        test_is_no_touch_iso,
        test_is_no_touch_gba_uppercase,
        test_is_no_touch_cso,
        test_is_no_touch_pbp,
        test_is_no_touch_v64,
        test_is_no_touch_mkv_not_blocked,
        test_is_no_touch_no_extension,
        test_should_skip_system_volume_information,
        test_should_skip_recycle_bin,
        test_should_skip_normal_path_not_skipped,
        test_free_path_non_existing_unchanged,
        test_free_path_collision_appends_2,
        test_free_path_collision_appends_3,
        test_executor_dry_run_returns_path_without_moving,
        test_executor_blocks_rom_extension,
        test_executor_blocks_system_path,
        test_executor_dry_run_attribute_mutable,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS: {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
