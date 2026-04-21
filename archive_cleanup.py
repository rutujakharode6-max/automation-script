import os
import shutil
import logging
import zipfile
import time
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cleanup.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

WHITELIST = {'.py', '.exe', '.sh'} # Example: protect scripts and executables

def get_file_age_days(file_path):
    mtime = os.path.getmtime(file_path)
    dt = datetime.fromtimestamp(mtime)
    diff = datetime.now() - dt
    return diff.days

def human_readable_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

def archive_files(files_to_archive, archive_name):
    """Compresses files into a ZIP and deletes the originals."""
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_archive:
            zipf.write(file, os.path.basename(file))
            os.remove(file)
            logger.info(f"Archived and removed: {file}")

def cleanup_and_archive(target_dir, age_threshold, action='archive', protect_list=None):
    if protect_list is None: protect_list = set()
    
    logger.info(f"Starting cleanup in: {target_dir} (Threshold: {age_threshold} days)")
    
    files_to_process = []
    total_size = 0
    
    buckets = {
        '30-90 days': [],
        '90-365 days': [],
        'Over 1 year': []
    }

    for root, dirs, files in os.walk(target_dir):
        # Skip blacklisted directories if any (could add here)
        for name in files:
            file_path = os.path.join(root, name)
            ext = os.path.splitext(name)[1].lower()
            
            if ext in WHITELIST or name in protect_list:
                continue
            
            if name in {"cleanup.log", "archive_cleanup.py"}:
                continue

            age = get_file_age_days(file_path)
            if age >= age_threshold:
                size = os.path.getsize(file_path)
                files_to_process.append((file_path, age, size))
                total_size += size
                
                # Categorize
                if age < 90: buckets['30-90 days'].append(name)
                elif age < 365: buckets['90-365 days'].append(name)
                else: buckets['Over 1 year'].append(name)

    if not files_to_process:
        print("No files found matching the age criteria.")
        return 0

    print("\n--- Summary of Old Files Found ---")
    for bucket, names in buckets.items():
        if names:
            print(f"{bucket}: {len(names)} files")
    print(f"Total potential space to free: {human_readable_size(total_size)}")

    confirm = input(f"\nDo you want to {action} these {len(files_to_process)} files? (yes/no): ").lower()
    if confirm != 'yes':
        print("Operation cancelled.")
        return 0

    freed_space = 0
    if action == 'archive':
        archive_dir = os.path.join(target_dir, "Archive_Storage")
        os.makedirs(archive_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(archive_dir, f"cleanup_backup_{timestamp}.zip")
        
        archive_files([f[0] for f in files_to_process], zip_path)
        freed_space = total_size # Technically transferred to zip, but freed from original location
        print(f"Files archived to: {zip_path}")
    
    elif action == 'delete':
        second_confirm = input("FINAL WARNING: These files will be PERMANENTLY deleted. Type 'DELETE' to confirm: ")
        if second_confirm == 'DELETE':
            for f_path, age, size in files_to_process:
                try:
                    os.remove(f_path)
                    logger.info(f"Deleted: {f_path} ({age} days old)")
                    freed_space += size
                except Exception as e:
                    logger.error(f"Error deleting {f_path}: {e}")
        else:
            print("Operation cancelled.")

    return freed_space

def main():
    print("=== Old File Cleanup & Archive Utility ===")
    target = input("Enter directory to scan: ").strip().strip('"')
    if not os.path.isdir(target):
        print("Invalid directory.")
        return

    try:
        age_threshold = int(input("Enter age threshold in days (e.g., 30): "))
    except ValueError:
        print("Invalid number.")
        return

    print("\nSelect Action:")
    print("1. Archive (Compress into ZIP and move)")
    print("2. Delete Permanently")
    choice = input("Select (1/2): ")
    action = 'archive' if choice == '1' else 'delete'

    freed = cleanup_and_archive(target, age_threshold, action)
    
    print(f"\n=== Cleanup Report ===")
    print(f"Total Space Freed/Managed: {human_readable_size(freed)}")
    print(f"Log: cleanup.log")

if __name__ == "__main__":
    main()
