# Architecture Patterns - v1.1 Research

**Domain:** Advanced media organizer with optional external dependencies and new monitoring capabilities
**Researched:** 2026-04-22
**Focus:** Integration patterns for SxxExx, TMDB/TVDB, progress bars, and watch mode

---

## Recommended Architecture

### Core Design Principles

1. **Progressive Enhancement**: All new features are optional and gracefully degrade
2. **Clean Separation**: New capabilities in dedicated modules with clear interfaces
3. **Backward Compatibility**: No breaking changes to existing v1.0 functionality
4. **Dependency Isolation**: External libraries only imported when features are used

### Extended Architecture Layers

`
┌─────────────────────────────────────────────────────────┐
│                      ENTRY POINT                        │
│  main() → detect drives → select drive → main_menu()   │
└──────────────────────┬──────────────────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────────────────┐
│                    MENU / UI LAYER                      │
│  main_menu()   show_menu()   ask_yes_no()               │
│  prompt_choice()   print_table()   confirm_action()     │
│  + progress_display()   watch_mode_controls()           │
└──────────────────────┬──────────────────────────────────┘
                       │ calls
┌──────────────────────▼──────────────────────────────────┐
│                  OPERATIONS LAYER                       │
│  op_rename_from_tsv()   op_organize_series()            │
│  op_organize_movies()   op_organize_games()             │
│  op_generate_tsv()      op_cleanup_empty_dirs()         │
│  op_coherence_check()   op_undo()                       │
│  + op_sxxexx_support()  + op_metadata_validate()        │
│  + op_watch_mode()      + op_progress_scan()            │
└───────────┬───────────────────────┬─────────────────────┘
            │                       │
┌───────────▼───────┐   ┌───────────▼─────────────────────┐
│   SCANNER / RULES │   │         EXECUTOR                │
│                   │   │                                  │
│  scan_drive()     │   │  class Executor:                 │
│  is_no_touch()    │   │    dry_run: bool                 │
│  is_protected()   │   │    undo_log: UndoLog             │
│  parse_series()   │   │    def move(src, dst)            │
│  parse_movie()    │   │    def rename(src, new_name)     │
│  parse_game_dir() │   │    def mkdir(path)               │
│  free_path()      │   │    def rmdir(path)               │
│  + parse_sxxexx() │   │    + progress_callback           │
│  + metadata_client│   │                                  │
└───────────────────┴─────────────────────┬───────────────┘
                                          │
                    ┌─────────────────────▼───────────────┐
                    │         NEW MODULES                 │
                    │                                     │
                    │  metadata.py — TMDB/TVDB client     │
                    │  watcher.py — File monitoring       │
                    │  progress.py — Progress display     │
                    │                                     │
                    └─────────────────────────────────────┘
`

### New Module Responsibilities

#### metadata.py
- **Purpose**: Optional metadata validation against TMDB/TVDB APIs
- **Interface**: alidate_series(name, year=None), alidate_movie(name, year)
- **Dependencies**: equests (optional), python-dotenv (optional)
- **Fallback**: Returns None when dependencies unavailable

#### watcher.py
- **Purpose**: File system monitoring for automatic organization
- **Interface**: WatchManager(drive_path, callback), start(), stop()
- **Dependencies**: watchdog (optional)
- **Fallback**: Polling-based implementation using os.scandir

#### progress.py
- **Purpose**: Visual progress indication for long operations
- **Interface**: ProgressBar(total, desc), update(n), close()
- **Dependencies**: 	qdm (preferred) or ich (alternative)
- **Fallback**: Simple text-based progress using print statements

### Integration Patterns

#### Optional Feature Detection
`python
# At module level - detect capabilities
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# In operations - graceful degradation
def op_metadata_validate(name, year=None):
    if not HAS_REQUESTS:
        print('Metadata validation requires: pip install requests')
        return None
    # ... validation logic
`

#### Progress Integration
`python
def scan_with_progress(drive_path):
    if HAS_TQDM and file_count > 1000:
        with tqdm(total=file_count, desc='Scanning') as pbar:
            for item in scan_drive(drive_path):
                # ... processing
                pbar.update(1)
    else:
        # Standard scanning without progress
        for item in scan_drive(drive_path):
            # ... processing
`

#### Watch Mode Architecture
`python
class WatchManager:
    def __init__(self, drive_path, organizer_callback):
        self.drive_path = drive_path
        self.callback = organizer_callback
        self.watcher = None
        
    def start(self):
        try:
            from watchdog.observers import Observer
            # Event-driven watching
            self.watcher = Observer()
            # ... setup event handlers
        except ImportError:
            # Fallback to polling
            self._start_polling()
    
    def _start_polling(self):
        # Polling implementation using threading.Timer
        # Check for new files every 30 seconds
        pass
`

### Data Flow for New Features

#### SxxExx Pattern Support
1. Extend existing RE_SERIES_VARIANT regex patterns
2. Add parse_sxxexx() function alongside parse_series()
3. Update organization logic to handle both patterns
4. Maintain backward compatibility with existing files

#### TMDB/TVDB Integration
1. User provides API keys via environment or config
2. During rename plan generation, optionally validate names
3. Add suggestion column to TSV with corrected names
4. Allow user to accept/reject suggestions

#### Progress Bars
1. Detect operation size during initial scan
2. Activate progress bars for operations > threshold
3. Update progress during file processing
4. Show completion statistics

#### Watch Mode
1. User selects 'Start Watch Mode' from menu
2. Monitor specified drive for new media files
3. When detected, run organization automatically
4. Provide controls to pause/resume/stop watching

### Error Handling & Resilience

#### Network Dependencies
- TMDB/TVDB calls should timeout and fail gracefully
- Cache successful validations to reduce API calls
- Clear error messages when APIs unavailable

#### File System Monitoring
- Handle drive disconnections during watch mode
- Robust file filtering to avoid processing temp files
- Configurable polling intervals for performance tuning

#### Optional Dependencies
- Import-time detection prevents crashes
- Clear user messaging about missing dependencies
- Feature flags in menu to hide unavailable options

### Performance Considerations

#### Progress Reporting
- Minimal overhead for small operations (< 1000 files)
- Efficient progress updates (batch updates, not per-file)
- Memory-efficient for large file sets

#### Watch Mode
- Event-driven preferred over polling when available
- File type filtering reduces unnecessary processing
- Batch processing of multiple new files

#### Metadata Validation
- Lazy loading of API clients
- Request caching to avoid duplicate calls
- Timeout handling to prevent UI blocking
