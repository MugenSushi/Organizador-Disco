import sys
sys.path.insert(0, '.')
import importlib.util
import unittest.mock as mock
import subprocess
from pathlib import Path

spec = importlib.util.spec_from_file_location('organizer', 'organizer.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

for name in ['setup_console_logging', 'add_file_logging', 'select_drive', 'show_menu',
             'main', 'get_removable_drives', 'Executor', 'is_no_touch', 'should_skip_path',
             '_free_path', 'NO_TOUCH_EXTS', 'SKIP_PATH_PARTS', 'LOG_DIR_NAME']:
    assert hasattr(mod, name), f'Missing symbol: {name}'

# D-02: select_drive exits with code 1 on empty list
r = subprocess.run(
    [sys.executable, '-c',
     'import sys; sys.path.insert(0, "."); import importlib.util; '
     'spec=importlib.util.spec_from_file_location("o","organizer.py"); '
     'm=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); '
     'm.select_drive([])'],
    capture_output=True, text=True
)
assert r.returncode == 1, f'D-02 exit code wrong: {r.returncode}'
assert 'extraibles' in r.stdout, f'D-02 message missing: {r.stdout!r}'

# D-01: auto-select single drive
single = [{'root': 'F:\\', 'label': 'MEDIOS', 'size_gb': 931.0, 'serial': 12345}]
with mock.patch('builtins.print') as mp:
    result = mod.select_drive(single)
assert result == single[0], 'D-01 returned wrong drive'
printed = ' '.join(str(c) for call in mp.call_args_list for c in call.args)
assert 'Usando' in printed, f'D-01 message missing: {printed!r}'

print('T2 PASS')
