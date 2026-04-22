# Domain Pitfalls - v1.1 Research

**Domain:** Advanced media organizer with external APIs, file monitoring, and progress tracking
**Researched:** 2026-04-22
**Focus:** Integration pitfalls for SxxExx patterns, TMDB/TVDB, progress bars, and watch mode

---

## Critical Pitfalls

### Pitfall 1: Optional Dependencies Breaking Core Functionality

**What goes wrong:**
Import-time failures when optional dependencies are installed but broken, or when import statements are at module level instead of function level.

**Why it happens:**
`python
# BAD: Module-level import
import requests  # Crashes entire script if missing

# BAD: Import in try block but used globally
try:
    import tqdm
except ImportError:
    tqdm = None

def scan_files():
    with tqdm(total=100):  # AttributeError if tqdm is None
        pass
`

**Consequences:**
- Script fails to start when optional dependencies are missing
- Users can't use core features because of optional dependency issues
- Poor user experience with cryptic import errors

**Prevention:**
`python
# GOOD: Function-level detection
def scan_with_progress(total):
    try:
        from tqdm import tqdm
        with tqdm(total=total) as pbar:
            # ... use pbar
    except ImportError:
        # Fallback to simple progress
        print(f'Processing {total} files...')
        # ... simple implementation
`

**Warning signs:**
- import requests at module level
- Global variables set from optional imports
- No try/except around optional dependency usage

---

### Pitfall 2: Watch Mode Resource Leaks

**What goes wrong:**
File monitoring threads or observers not properly cleaned up, leading to hanging processes or resource exhaustion.

**Why it happens:**
`python
# BAD: No cleanup
observer = Observer()
observer.start()
# Script exits without observer.stop()
`

**Consequences:**
- Python process doesn't terminate properly
- Multiple watch processes accumulate on system
- High CPU usage from orphaned monitoring threads

**Prevention:**
`python
class WatchManager:
    def __init__(self):
        self.observer = None
        
    def start(self):
        self.observer = Observer()
        # ... setup handlers
        self.observer.start()
        
    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
`

**Warning signs:**
- observer.start() without corresponding stop()
- No timeout on join()
- Watch mode without proper signal handling

---

### Pitfall 3: API Rate Limiting and Blocking UI

**What goes wrong:**
TMDB/TVDB API calls block the UI thread, or exceed rate limits causing temporary bans.

**Why it happens:**
`python
# BAD: Synchronous API calls in UI thread
for movie in movies:
    metadata = tmdb_api.lookup(movie.name)  # Blocks UI
    # Process result
`

**Consequences:**
- Unresponsive UI during metadata validation
- API rate limit exceeded, service temporarily unavailable
- Poor user experience with long waits

**Prevention:**
`python
# GOOD: Batch processing with progress
def validate_metadata_batch(names, api_client):
    results = {}
    with tqdm(total=len(names), desc='Validating') as pbar:
        for name in names:
            try:
                result = api_client.lookup(name, timeout=5)
                results[name] = result
            except (requests.Timeout, requests.ConnectionError):
                results[name] = None  # Graceful failure
            pbar.update(1)
    return results
`

**Warning signs:**
- API calls in the main thread
- No timeout on HTTP requests
- No error handling for network failures

---

### Pitfall 4: Progress Bar Performance Issues

**What goes wrong:**
Progress bars add significant overhead for fast operations, or cause memory issues with large file counts.

**Why it happens:**
`python
# BAD: Progress bar for every file
for file_path in all_files:
    pbar.update(1)  # Too frequent updates
    process_file(file_path)
`

**Consequences:**
- Operations take longer due to progress bar overhead
- Memory usage spikes with very large file sets
- UI becomes unresponsive during updates

**Prevention:**
`python
# GOOD: Threshold-based activation and batch updates
def process_files_with_progress(file_list):
    total = len(file_list)
    if total < 100:  # Skip progress for small operations
        return process_files_simple(file_list)
    
    try:
        from tqdm import tqdm
        with tqdm(total=total, desc='Processing') as pbar:
            batch_size = max(1, total // 100)  # Update ~100 times
            for i, file_path in enumerate(file_list):
                process_file(file_path)
                if (i + 1) % batch_size == 0:
                    pbar.update(batch_size)
            pbar.update(total % batch_size)  # Final update
    except ImportError:
        return process_files_simple(file_list)
`

**Warning signs:**
- Progress bars for operations < 10 seconds
- Per-file progress updates
- No fallback when tqdm unavailable

---

### Pitfall 5: SxxExx Pattern Conflicts

**What goes wrong:**
SxxExx patterns conflict with existing parsing logic, or create ambiguous matches.

**Why it happens:**
`python
# BAD: Overlapping patterns
RE_SERIES = re.compile(r'(.*?) - Temporada (\d+) - Episodio (\d+)')
RE_SXXEXX = re.compile(r'(.*?)S(\d+)E(\d+)')  # Conflicts with movie titles
`

**Consequences:**
- Movie titles like 'Movie S2023.mkv' incorrectly parsed as series
- Existing files re-organized unexpectedly
- Inconsistent behavior between old and new files

**Prevention:**
`python
# GOOD: Context-aware parsing
def parse_filename(filename):
    # First try existing patterns
    series_match = RE_SERIES.search(filename)
    if series_match:
        return parse_series_match(series_match)
    
    # Then try SxxExx in series context only
    sxxexx_match = RE_SXXEXX.search(filename)
    if sxxexx_match and is_series_context(filename):
        return parse_sxxexx_match(sxxexx_match)
    
    # Finally try movie patterns
    movie_match = RE_MOVIE.search(filename)
    if movie_match:
        return parse_movie_match(movie_match)
    
    return None
`

**Warning signs:**
- Regex patterns that match across different media types
- No prioritization of existing patterns
- Changing behavior for existing files

---

### Pitfall 6: Watch Mode File Processing Race Conditions

**What goes wrong:**
Files being written when watch mode detects them, causing partial reads or conflicts.

**Why it happens:**
`python
# BAD: Process immediately on detection
def on_file_created(event):
    organize_file(event.src_path)  # File might still be writing
`

**Consequences:**
- Incomplete file processing
- Corruption of partially written files
- Failed organization attempts

**Prevention:**
`python
# GOOD: Wait for file stability
def on_file_created(event):
    path = Path(event.src_path)
    
    # Wait for file to be stable (size unchanged)
    initial_size = -1
    stable_count = 0
    
    while stable_count < 3:  # Wait for 3 stable checks
        time.sleep(1)
        if not path.exists():
            return  # File was deleted
        
        current_size = path.stat().st_size
        if current_size == initial_size:
            stable_count += 1
        else:
            initial_size = current_size
            stable_count = 0
    
    # Now safe to process
    organize_file(path)
`

**Warning signs:**
- Immediate processing of newly created files
- No stability checks for file size
- Ignoring file modification events during writing

---

## Integration Pitfalls

### API Key Management
- Store keys securely (environment variables, not hardcoded)
- Validate keys on startup, not during first API call
- Clear error messages for invalid/missing keys

### Dependency Version Conflicts
- Specify version ranges in optional dependencies
- Test with multiple versions of external libraries
- Document known compatibility issues

### Cross-Platform Watch Mode
- Windows-specific path handling in watch events
- Different filesystem behaviors between drives
- Proper encoding handling for international filenames

---

## Testing Considerations

### Mock External Dependencies
`python
# Use monkey patching for testing
import organizer
original_import = __builtins__.__import__

def mock_import(name, *args, **kwargs):
    if name == 'requests':
        raise ImportError('Mocked missing dependency')
    return original_import(name, *args, **kwargs)

__builtins__.__import__ = mock_import
`

### Simulate Network Conditions
- Use esponses library to mock API responses
- Test timeout and connection error scenarios
- Verify graceful degradation

### Watch Mode Testing
- Create temporary directories for watch testing
- Simulate file creation events
- Test cleanup on interruption
