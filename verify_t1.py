import sys
sys.path.insert(0, '.')
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('organizer', 'organizer.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

assert mod.is_no_touch('movie.iso')
assert mod.is_no_touch('GAME.GBA')
assert mod.is_no_touch('archive.cso')
assert mod.is_no_touch('archive.pbp')
assert mod.is_no_touch('archive.v64')
assert not mod.is_no_touch('movie.mkv')
assert not mod.is_no_touch('nodot')
assert mod.should_skip_path('F:\\System Volume Information\\foo')
assert mod.should_skip_path('F:\\$RECYCLE.BIN\\foo')
assert not mod.should_skip_path('F:\\MEDIOS\\ok.mkv')
ex = mod.Executor(dry_run=True)
assert ex.dry_run
ex.dry_run = False
assert not ex.dry_run
print('T1 PASS')
