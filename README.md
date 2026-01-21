# Enhanced Duplicate File Finder

A powerful Python tool to find and delete duplicate files with multiple safety features and deletion strategies.

## Features

- **Fast duplicate detection** using file size pre-filtering and MD5 hashing
- **Multiple deletion modes**: Interactive, Auto-oldest, Auto-newest, Auto-shortest-path
- **Safety features**: Trash mode (recoverable) vs permanent deletion
- **Dry-run mode** to preview what would be deleted
- **Detailed reporting** with timestamps and file information
- **Progress tracking** for large file sets

## Installation

No additional dependencies required - uses only Python standard library.

```bash
chmod +x find_duplicates_enhanced.py
```

## Usage Examples

### 1. Find Duplicates Only (No Deletion)

```bash
# Basic scan
python find_duplicates_enhanced.py /path/to/directory

# Ignore small files (< 1MB)
python find_duplicates_enhanced.py /path/to/directory -m 1048576

# Custom output file
python find_duplicates_enhanced.py /path/to/directory -o my_report.txt
```

### 2. Interactive Deletion

```bash
python find_duplicates_enhanced.py /path/to/directory --delete interactive
```

**Interactive commands:**
- `d 1` - Delete duplicate #1
- `d 2` - Delete duplicate #2
- `da` - Delete all duplicates in group (keep oldest)
- `s` - Skip this group
- `q` - Quit deletion process

### 3. Automatic Deletion Strategies

**Keep oldest file** (default strategy):
```bash
python find_duplicates_enhanced.py /path/to/directory --delete auto-oldest
```

**Keep newest file**:
```bash
python find_duplicates_enhanced.py /path/to/directory --delete auto-newest
```

**Keep file with shortest path** (useful for organized directories):
```bash
python find_duplicates_enhanced.py /path/to/directory --delete auto-shortest
```

### 4. Permanent Deletion (⚠️ Use with caution!)

```bash
# Interactive with permanent deletion
python find_duplicates_enhanced.py /path/to/directory --delete interactive --permanent

# Auto-delete with permanent deletion (requires typing 'DELETE' to confirm)
python find_duplicates_enhanced.py /path/to/directory --delete auto-oldest --permanent
```

### 5. Dry Run (Preview Only)

```bash
# See what would be deleted without actually deleting
python find_duplicates_enhanced.py /path/to/directory --delete auto-oldest --dry-run
```

## Deletion Modes Explained

### Trash Mode (Default - Safe)
- Files are moved to `~/.duplicate_trash/`
- Files can be recovered manually
- Timestamp is added to filename to prevent conflicts
- Safe for experimenting

### Permanent Mode (Requires --permanent flag)
- Files are permanently deleted
- Requires confirmation by typing 'DELETE'
- Cannot be recovered
- Use only when certain

## Keep Strategies

| Strategy | Keeps | Deletes | Best For |
|----------|-------|---------|----------|
| `auto-oldest` | Oldest file (earliest mtime) | Newer copies | Original files from backups |
| `auto-newest` | Newest file (latest mtime) | Older copies | Keeping most recent versions |
| `auto-shortest` | File with shortest path | Files in deeper directories | Well-organized folder structures |

## Output Report

The tool generates a detailed report (`duplicates_report.txt` by default) containing:

- Scan timestamp and directory
- Duplicate groups with file hashes
- File paths and modification times
- Original vs duplicate designation
- Summary with total space savings

Example report section:
```
Group 1 (Hash: 5d41402abc4b..., Size: 2.45 MB)
--------------------------------------------------
  [ORIGINAL] /home/user/docs/photo.jpg
             Modified: 2024-01-15 10:30:45
  [DUPLICATE] /home/user/backup/photo.jpg
              Modified: 2024-01-16 14:22:10
```

## Safety Features

1. **Confirmation prompts** for permanent deletion
2. **Protected originals** - Oldest file marked as [ORIGINAL] and protected in interactive mode
3. **Trash directory** - Recoverable deletion by default
4. **Dry-run mode** - Preview before deletion
5. **Error handling** - Continues on file access errors with warnings
6. **Clear reporting** - Always shows what was deleted

## Recovery from Trash

If you deleted files using trash mode (default):

```bash
# View deleted files
ls -lh ~/.duplicate_trash/

# Recover a specific file
mv ~/.duplicate_trash/20250114_143022_myfile.txt /path/to/restore/location/

# Permanently delete trash (free up space)
rm -rf ~/.duplicate_trash/
```

## Common Workflows

### Workflow 1: Conservative Cleanup
```bash
# Step 1: Find duplicates
python find_duplicates_enhanced.py ~/Documents

# Step 2: Review the report
cat duplicates_report.txt

# Step 3: Interactive deletion with trash
python find_duplicates_enhanced.py ~/Documents --delete interactive

# Step 4: Review trash before permanent deletion
ls ~/.duplicate_trash/
```

### Workflow 2: Aggressive Cleanup (Use Carefully!)
```bash
# Step 1: Dry run to preview
python find_duplicates_enhanced.py ~/Downloads --delete auto-oldest --dry-run

# Step 2: Review report
cat duplicates_report.txt

# Step 3: Execute with trash (recoverable)
python find_duplicates_enhanced.py ~/Downloads --delete auto-oldest

# Step 4: Verify results, then empty trash
rm -rf ~/.duplicate_trash/
```

### Workflow 3: Backup Directory Cleanup
```bash
# Find large duplicates only (>10MB)
python find_duplicates_enhanced.py ~/Backups -m 10485760 --delete auto-oldest
```

## Performance Tips

- Use `-m` to skip small files if you're only interested in large duplicates
- The tool is fastest on SSDs
- First scan (size grouping) is very fast
- Hash calculation is the slower step but only hashes potential duplicates

## Warning Signs & Best Practices

⚠️ **DO NOT** use on system directories (/usr, /bin, /etc, /System)
⚠️ **DO** scan your target directory first without deletion
⚠️ **DO** review the report before deleting
⚠️ **DO** use trash mode first, then verify before permanent deletion
⚠️ **DO** backup important data before running deletion

## Command Line Options

```
positional arguments:
  directory             Directory to scan for duplicates

options:
  -h, --help            Show help message
  -o, --output FILE     Output report file (default: duplicates_report.txt)
  -m, --min-size BYTES  Minimum file size in bytes (default: 0)
  --delete MODE         Enable deletion mode:
                        - interactive: Manual selection
                        - auto-oldest: Keep oldest files
                        - auto-newest: Keep newest files
                        - auto-shortest: Keep shortest paths
  --permanent           Permanently delete (default: trash)
  --dry-run             Preview deletion without executing
```

## Troubleshooting

**Problem**: Permission denied errors
- **Solution**: Run with appropriate permissions or skip system directories

**Problem**: Files deleted but space not freed
- **Solution**: Check if files are in trash (`~/.duplicate_trash/`), empty trash to free space

**Problem**: Wrong files being kept as "original"
- **Solution**: Use `--delete interactive` for manual control, or choose different auto strategy

**Problem**: Process takes too long
- **Solution**: Use `-m` flag to skip small files, or scan smaller directory trees

## License

Free to use and modify for personal and commercial use.
