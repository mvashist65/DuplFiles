#!/usr/bin/env python3
"""
Find duplicate files in a directory recursively.
Uses file size for initial filtering, then MD5 hash for comparison.
Outputs results to a file for later action.
"""

import os
import hashlib
import argparse
from collections import defaultdict
from pathlib import Path
from datetime import datetime


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


def main():
    parser = argparse.ArgumentParser(
        description='Find duplicate files in a directory recursively.'
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
    
    return 0


if __name__ == '__main__':
    exit(main())
