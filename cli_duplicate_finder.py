import os
import hashlib
import shutil
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("duplicate_finder_cli.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def compute_hash(file_path, algorithm='sha256'):
    """Computes the hash of a file."""
    hash_func = hashlib.new(algorithm)
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing {file_path}: {e}")
        return None

def find_duplicates(directory):
    """Finds duplicate files based on content."""
    size_map = defaultdict(list)
    logger.info(f"Scanning directory: {directory}")
    
    # First pass: Group by size (much faster than hashing everything)
    for root, _, files in os.walk(directory):
        for name in files:
            file_path = os.path.join(root, name)
            try:
                size = os.path.getsize(file_path)
                size_map[size].append(file_path)
            except Exception as e:
                logger.error(f"Error accessing {file_path}: {e}")

    # Second pass: Hash files with same size
    hash_map = defaultdict(list)
    for size, paths in size_map.items():
        if len(paths) > 1:
            for path in paths:
                file_hash = compute_hash(path)
                if file_hash:
                    hash_map[file_hash].append(path)

    # Filter out non-duplicates
    return {h: paths for h, paths in hash_map.items() if len(paths) > 1}

def human_readable_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

def process_duplicates(duplicates, action='move', keep_strategy='oldest', dry_run=False):
    """Handles the duplicate files based on strategy."""
    total_freed = 0
    managed_files = 0
    
    duplicates_folder = Path("Duplicates_Found")
    if action == 'move' and not dry_run:
        duplicates_folder.mkdir(exist_ok=True)

    for file_hash, paths in duplicates.items():
        # Sort based on strategy
        # oldest: sort by mtime ascending (oldest first)
        # newest: sort by mtime descending (newest first)
        paths_with_time = []
        for p in paths:
            try:
                paths_with_time.append((p, os.path.getmtime(p), os.path.getsize(p)))
            except:
                continue
        
        if not paths_with_time:
            continue

        if keep_strategy == 'oldest':
            paths_with_time.sort(key=lambda x: x[1])
        elif keep_strategy == 'newest':
            paths_with_time.sort(key=lambda x: x[1], reverse=True)
        # For manual, we'd need an interactive loop, but let's implement the logic for CLI

        # The first file is kept, others are "duplicates"
        to_keep = paths_with_time[0][0]
        to_remove = paths_with_time[1:]

        logger.info(f"Group {file_hash[:8]}... Keeping: {to_keep}")
        
        for file_path, mtime, size in to_remove:
            if dry_run:
                logger.info(f"[DRY-RUN] Would {action}: {file_path} ({human_readable_size(size)})")
            else:
                try:
                    if action == 'delete':
                        os.remove(file_path)
                        logger.info(f"Deleted: {file_path}")
                    elif action == 'move':
                        dest = duplicates_folder / os.path.basename(file_path)
                        # Handle collision in duplicates folder
                        counter = 1
                        while dest.exists():
                            dest = duplicates_folder / f"{Path(file_path).stem}_{counter}{Path(file_path).suffix}"
                            counter += 1
                        shutil.move(file_path, str(dest))
                        logger.info(f"Moved to '{duplicates_folder}': {file_path}")
                    
                    total_freed += size
                    managed_files += 1
                except Exception as e:
                    logger.error(f"Failed to {action} {file_path}: {e}")

    return managed_files, total_freed

def main():
    print("=== Content-Based Duplicate Finder CLI ===")
    source = input("Enter directory to scan: ").strip().strip('"')
    if not os.path.isdir(source):
        print("Invalid directory.")
        return

    duplicates = find_duplicates(source)
    if not duplicates:
        print("No duplicate files found.")
        return

    total_groups = len(duplicates)
    total_dupes = sum(len(p) - 1 for p in duplicates.values())
    potential_space = sum(os.path.getsize(p[0]) * (len(p) - 1) for p in duplicates.values())

    print(f"\nFound {total_groups} groups of duplicates ({total_dupes} extra files).")
    print(f"Potential space savings: {human_readable_size(potential_space)}")

    dry_run_input = input("\nRun in Dry-Run mode? (y/n): ").lower() == 'y'
    
    print("\nKeep Strategy:")
    print("1. Keep Oldest (Keep the file created/modified first)")
    print("2. Keep Newest (Keep the file modified last)")
    strategy_choice = input("Select strategy (1/2): ")
    keep_strategy = 'oldest' if strategy_choice == '1' else 'newest'

    print("\nAction:")
    print("1. Move duplicates to 'Duplicates_Found' folder")
    print("2. Delete duplicates permanently")
    action_choice = input("Select action (1/2): ")
    action = 'move' if action_choice == '1' else 'delete'

    if not dry_run_input:
        confirm = input(f"WARNING: This will {action} {total_dupes} files. Proceed? (yes/no): ").lower()
        if confirm != 'yes':
            print("Aborted.")
            return

    count, space = process_duplicates(duplicates, action, keep_strategy, dry_run_input)

    print("\n=== Scan Report ===")
    if dry_run_input:
        print(f"Dry-run complete. No files were actually changed.")
    else:
        print(f"Total files {action}d: {count}")
        print(f"Total space saved: {human_readable_size(space)}")
    print(f"Check 'duplicate_finder_cli.log' for details.")

if __name__ == "__main__":
    main()
