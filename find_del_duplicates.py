#!/usr/bin/env python3
"""
Find duplicate files in a directory recursively.
Uses file size for initial filtering, then MD5 hash for comparison.
Outputs results to a file for later action.
Supports interactive and automated deletion of duplicate files.
"""

import os
import hashlib
import argparse
import shutil
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from typing import List, Tuple


def get_file_hash(filepath: str, block_size: int = 65536) -> str:
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                hasher.update(block)
        return hasher.hexdigest()
    except (IOError, OSError) as e:
        print(f"Error reading {filepath}: {e}")
        return None


def find_duplicates(directory: str, min_size: int = 0) -> dict:
    """
    Find duplicate files in directory recursively.
    
    Args:
        directory: Root directory to search
        min_size: Minimum file size in bytes to consider (default: 0)
    
    Returns:
        Dictionary mapping hash -> list of file paths
    """
    # First pass: group files by size (quick filter)
    size_map = defaultdict(list)
    
    print(f"Scanning directory: {directory}")
    file_count = 0
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            try:
                size = os.path.getsize(filepath)
                if size >= min_size:
                    size_map[size].append(filepath)
                    file_count += 1
            except (OSError, IOError) as e:
                print(f"Error accessing {filepath}: {e}")
    
    print(f"Found {file_count} files")
    
    # Second pass: hash files that share the same size
    hash_map = defaultdict(list)
    potential_duplicates = {size: paths for size, paths in size_map.items() if len(paths) > 1}
    
    files_to_hash = sum(len(paths) for paths in potential_duplicates.values())
    print(f"Hashing {files_to_hash} potential duplicates...")
    
    hashed = 0
    for size, paths in potential_duplicates.items():
        for filepath in paths:
            file_hash = get_file_hash(filepath)
            if file_hash:
                hash_map[file_hash].append(filepath)
            hashed += 1
            if hashed % 100 == 0:
                print(f"  Hashed {hashed}/{files_to_hash} files...")
    
    # Filter to only include actual duplicates
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    
    return duplicates


def write_results(duplicates: dict, output_file: str, directory: str):
    """Write duplicate findings to output file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Duplicate File Report\n")
        f.write(f"{'=' * 60}\n")
        f.write(f"Scanned directory: {directory}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'=' * 60}\n\n")
        
        if not duplicates:
            f.write("No duplicate files found.\n")
            return 0, 0
        
        total_groups = len(duplicates)
        total_duplicates = sum(len(paths) - 1 for paths in duplicates.values())
        total_wasted = 0
        
        f.write(f"Found {total_groups} groups of duplicates ({total_duplicates} duplicate files)\n\n")
        
        group_num = 1
        for file_hash, paths in sorted(duplicates.items(), key=lambda x: -len(x[1])):
            # Sort by modification time - oldest first (considered "original")
            paths_with_mtime = []
            for p in paths:
                try:
                    mtime = os.path.getmtime(p)
                    size = os.path.getsize(p)
                    paths_with_mtime.append((p, mtime, size))
                except OSError:
                    paths_with_mtime.append((p, 0, 0))
            
            paths_with_mtime.sort(key=lambda x: x[1])  # Sort by mtime
            
            file_size = paths_with_mtime[0][2]
            wasted_space = file_size * (len(paths) - 1)
            total_wasted += wasted_space
            
            f.write(f"Group {group_num} (Hash: {file_hash[:12]}..., Size: {format_size(file_size)})\n")
            f.write(f"{'-' * 50}\n")
            
            # First file is considered the original
            f.write(f"  [ORIGINAL] {paths_with_mtime[0][0]}\n")
            f.write(f"             Modified: {datetime.fromtimestamp(paths_with_mtime[0][1]).strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Rest are duplicates
            for path, mtime, _ in paths_with_mtime[1:]:
                f.write(f"  [DUPLICATE] {path}\n")
                f.write(f"              Modified: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            f.write(f"\n")
            group_num += 1
        
        f.write(f"{'=' * 60}\n")
        f.write(f"Summary:\n")
        f.write(f"  Total duplicate groups: {total_groups}\n")
        f.write(f"  Total duplicate files: {total_duplicates}\n")
        f.write(f"  Potential space savings: {format_size(total_wasted)}\n")
        
        return total_groups, total_wasted


def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def delete_file(filepath: str, use_trash: bool = True) -> Tuple[bool, str]:
    """
    Delete a file safely.
    
    Args:
        filepath: Path to file to delete
        use_trash: If True, move to trash; if False, permanently delete
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if use_trash:
            # Move to trash directory
            trash_dir = os.path.join(os.path.expanduser('~'), '.duplicate_trash')
            os.makedirs(trash_dir, exist_ok=True)
            
            # Create unique filename in trash
            filename = os.path.basename(filepath)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            trash_path = os.path.join(trash_dir, f"{timestamp}_{filename}")
            
            # Handle duplicate names in trash
            counter = 1
            while os.path.exists(trash_path):
                trash_path = os.path.join(trash_dir, f"{timestamp}_{counter}_{filename}")
                counter += 1
            
            shutil.move(filepath, trash_path)
            return True, f"Moved to trash: {trash_path}"
        else:
            # Permanently delete
            os.remove(filepath)
            return True, "Permanently deleted"
    except Exception as e:
        return False, f"Error: {str(e)}"


def interactive_delete(duplicates: dict) -> Tuple[int, int]:
    """
    Interactively delete duplicate files.
    
    Args:
        duplicates: Dictionary mapping hash -> list of file paths
    
    Returns:
        Tuple of (files_deleted, space_freed)
    """
    files_deleted = 0
    space_freed = 0
    
    print(f"\n{'=' * 60}")
    print("INTERACTIVE DELETION MODE")
    print(f"{'=' * 60}")
    print("\nCommands:")
    print("  d [num] - Delete specific duplicate by number")
    print("  da      - Delete all duplicates in this group (keep oldest)")
    print("  s       - Skip this group")
    print("  q       - Quit deletion process")
    print(f"{'=' * 60}\n")
    
    use_trash = True
    response = input("Use trash (safe, recoverable) or permanent deletion? [trash/permanent]: ").strip().lower()
    if response in ['permanent', 'perm', 'p']:
        confirm = input("WARNING: Permanent deletion cannot be undone! Continue? [yes/no]: ").strip().lower()
        if confirm == 'yes':
            use_trash = False
        else:
            print("Using trash mode for safety.")
    
    group_num = 1
    for file_hash, paths in sorted(duplicates.items(), key=lambda x: -len(x[1])):
        # Sort by modification time - oldest first
        paths_with_mtime = []
        for p in paths:
            try:
                mtime = os.path.getmtime(p)
                size = os.path.getsize(p)
                paths_with_mtime.append((p, mtime, size))
            except OSError:
                paths_with_mtime.append((p, 0, 0))
        
        paths_with_mtime.sort(key=lambda x: x[1])
        
        file_size = paths_with_mtime[0][2]
        
        print(f"\nGroup {group_num}/{len(duplicates)} - Size: {format_size(file_size)}, {len(paths)} copies")
        print(f"{'-' * 60}")
        print(f"  0. [ORIGINAL - KEEP] {paths_with_mtime[0][0]}")
        print(f"     Modified: {datetime.fromtimestamp(paths_with_mtime[0][1]).strftime('%Y-%m-%d %H:%M:%S')}")
        
        for idx, (path, mtime, _) in enumerate(paths_with_mtime[1:], 1):
            print(f"  {idx}. [DUPLICATE] {path}")
            print(f"     Modified: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        while True:
            choice = input(f"\nAction [d <num>/da/s/q]: ").strip().lower()
            
            if choice == 'q':
                print("\nExiting deletion process...")
                return files_deleted, space_freed
            
            elif choice == 's':
                break
            
            elif choice == 'da':
                # Delete all duplicates, keep original
                confirm = input(f"Delete {len(paths_with_mtime) - 1} duplicates? [y/n]: ").strip().lower()
                if confirm == 'y':
                    for path, _, _ in paths_with_mtime[1:]:
                        success, msg = delete_file(path, use_trash)
                        if success:
                            files_deleted += 1
                            space_freed += file_size
                            print(f"  ✓ Deleted: {path}")
                        else:
                            print(f"  ✗ Failed: {path} - {msg}")
                break
            
            elif choice.startswith('d '):
                try:
                    num = int(choice.split()[1])
                    if num == 0:
                        print("  ✗ Cannot delete the original (index 0)")
                    elif 1 <= num < len(paths_with_mtime):
                        path = paths_with_mtime[num][0]
                        success, msg = delete_file(path, use_trash)
                        if success:
                            files_deleted += 1
                            space_freed += file_size
                            print(f"  ✓ Deleted: {path}")
                        else:
                            print(f"  ✗ Failed: {path} - {msg}")
                    else:
                        print(f"  ✗ Invalid index: {num}")
                except (ValueError, IndexError):
                    print("  ✗ Invalid command format. Use: d <number>")
            else:
                print("  ✗ Invalid command. Use: d <num>, da, s, or q")
        
        group_num += 1
    
    return files_deleted, space_freed


def auto_delete(duplicates: dict, keep_strategy: str = 'oldest', use_trash: bool = True) -> Tuple[int, int]:
    """
    Automatically delete duplicates based on strategy.
    
    Args:
        duplicates: Dictionary mapping hash -> list of file paths
        keep_strategy: 'oldest', 'newest', or 'shortest_path'
        use_trash: If True, move to trash; if False, permanently delete
    
    Returns:
        Tuple of (files_deleted, space_freed)
    """
    files_deleted = 0
    space_freed = 0
    
    print(f"\n{'=' * 60}")
    print(f"AUTO-DELETE MODE (Keep: {keep_strategy})")
    print(f"{'=' * 60}\n")
    
    for file_hash, paths in duplicates.items():
        paths_with_info = []
        for p in paths:
            try:
                mtime = os.path.getmtime(p)
                size = os.path.getsize(p)
                paths_with_info.append((p, mtime, size, len(p)))
            except OSError:
                continue
        
        if not paths_with_info:
            continue
        
        # Determine which file to keep based on strategy
        if keep_strategy == 'oldest':
            paths_with_info.sort(key=lambda x: x[1])  # Sort by mtime
        elif keep_strategy == 'newest':
            paths_with_info.sort(key=lambda x: -x[1])  # Sort by -mtime
        elif keep_strategy == 'shortest_path':
            paths_with_info.sort(key=lambda x: x[3])  # Sort by path length
        
        keep_file = paths_with_info[0][0]
        file_size = paths_with_info[0][2]
        
        print(f"Keeping: {keep_file}")
        
        # Delete all others
        for path, _, _, _ in paths_with_info[1:]:
            success, msg = delete_file(path, use_trash)
            if success:
                files_deleted += 1
                space_freed += file_size
                print(f"  ✓ Deleted: {path}")
            else:
                print(f"  ✗ Failed: {path} - {msg}")
    
    return files_deleted, space_freed


def main():
    parser = argparse.ArgumentParser(
        description='Find duplicate files in a directory recursively.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Deletion Modes:
  --delete interactive    : Manually choose which files to delete
  --delete auto-oldest    : Auto-delete, keeping oldest file
  --delete auto-newest    : Auto-delete, keeping newest file
  --delete auto-shortest  : Auto-delete, keeping file with shortest path

Examples:
  # Find duplicates only
  %(prog)s /path/to/directory
  
  # Interactive deletion
  %(prog)s /path/to/directory --delete interactive
  
  # Auto-delete keeping oldest files
  %(prog)s /path/to/directory --delete auto-oldest --permanent
        """
    )
    parser.add_argument(
        'directory',
        help='Directory to scan for duplicates'
    )
    parser.add_argument(
        '-o', '--output',
        default='duplicates_report.txt',
        help='Output file path (default: duplicates_report.txt)'
    )
    parser.add_argument(
        '-m', '--min-size',
        type=int,
        default=0,
        help='Minimum file size in bytes to consider (default: 0)'
    )
    parser.add_argument(
        '--delete',
        choices=['interactive', 'auto-oldest', 'auto-newest', 'auto-shortest'],
        help='Enable deletion mode'
    )
    parser.add_argument(
        '--permanent',
        action='store_true',
        help='Permanently delete files (default: move to trash)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    directory = os.path.abspath(args.directory)
    
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory")
        return 1
    
    print(f"\nDuplicate File Finder")
    print(f"{'=' * 40}")
    
    duplicates = find_duplicates(directory, args.min_size)
    
    total_groups, total_wasted = write_results(duplicates, args.output, directory)
    
    print(f"\nResults written to: {args.output}")
    print(f"Found {total_groups} groups of duplicates")
    print(f"Potential space savings: {format_size(total_wasted)}")
    
    # Deletion mode
    if args.delete and duplicates:
        if args.dry_run:
            print("\n*** DRY RUN MODE - No files will be deleted ***")
            return 0
        
        print(f"\n{'=' * 60}")
        print("WARNING: You are about to delete files!")
        print(f"{'=' * 60}")
        
        if args.permanent:
            print("⚠️  PERMANENT DELETION MODE - Files cannot be recovered!")
            confirm = input("Type 'DELETE' to confirm permanent deletion: ").strip()
            if confirm != 'DELETE':
                print("Deletion cancelled.")
                return 0
        else:
            print("Files will be moved to ~/.duplicate_trash (recoverable)")
            confirm = input("Continue with deletion? [y/n]: ").strip().lower()
            if confirm != 'y':
                print("Deletion cancelled.")
                return 0
        
        files_deleted = 0
        space_freed = 0
        
        if args.delete == 'interactive':
            files_deleted, space_freed = interactive_delete(duplicates)
        elif args.delete.startswith('auto-'):
            strategy = args.delete.replace('auto-', '')
            files_deleted, space_freed = auto_delete(
                duplicates, 
                keep_strategy=strategy,
                use_trash=not args.permanent
            )
        
        print(f"\n{'=' * 60}")
        print("DELETION SUMMARY")
        print(f"{'=' * 60}")
        print(f"Files deleted: {files_deleted}")
        print(f"Space freed: {format_size(space_freed)}")
        
        if not args.permanent:
            trash_dir = os.path.join(os.path.expanduser('~'), '.duplicate_trash')
            print(f"\nDeleted files moved to: {trash_dir}")
            print("To permanently delete, remove this directory manually.")
    
    return 0


if __name__ == '__main__':
    exit(main())
