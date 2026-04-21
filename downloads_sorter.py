import os
import shutil
import time
import logging
from pathlib import Path
from collections import Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("folder_sorter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Category Mapping
CATEGORIES = {
    'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.heic'],
    'Documents': ['.pdf', '.doc', '.docx', '.txt', '.xlsx', '.xls', '.pptx', '.csv', '.rtf'],
    'Videos': ['.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv'],
    'Music': ['.mp3', '.wav', '.flac', '.m4a', '.aac'],
    'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
    'Executables': ['.exe', '.msi', '.bat', '.sh'],
    'Code': ['.py', '.js', '.html', '.css', '.cpp', '.java', '.json']
}

def get_category(extension):
    for category, extensions in CATEGORIES.items():
        if extension.lower() in extensions:
            return category
    return 'Others'

def handle_naming_conflict(target_path):
    counter = 1
    path = Path(target_path)
    new_path = path
    while new_path.exists():
        new_path = path.parent / f"{path.stem}_{counter}{path.suffix}"
        counter += 1
    return str(new_path)

def sort_folder(target_dir):
    logger.info(f"Sorting files in: {target_dir}")
    stats = Counter()
    
    # Files directly in the target directory
    for item in os.listdir(target_dir):
        item_path = os.path.join(target_dir, item)
        
        # We only sort files, don't move the sorting folders themselves
        if os.path.isfile(item_path):
            if item in {"folder_sorter.log", "downloads_sorter.py"}:
                continue
                
            ext = os.path.splitext(item)[1]
            category = get_category(ext)
            
            dest_folder = os.path.join(target_dir, category)
            os.makedirs(dest_folder, exist_ok=True)
            
            target_file_path = handle_naming_conflict(os.path.join(dest_folder, item))
            
            try:
                shutil.move(item_path, target_file_path)
                logger.info(f"Moved: {item} -> {category}/")
                stats[category] += 1
            except Exception as e:
                logger.error(f"Error moving {item}: {e}")

    # Delete empty folders
    for root, dirs, files in os.walk(target_dir, topdown=False):
        for name in dirs:
            dir_path = os.path.join(root, name)
            if not os.listdir(dir_path):
                try:
                    os.rmdir(dir_path)
                    logger.info(f"Deleted empty folder: {dir_path}")
                except Exception as e:
                    logger.debug(f"Could not delete folder {dir_path}: {e}")

    return stats

def main():
    print("=== Automated Folder Sorter ===")
    target = input("Enter directory to sort (default: current directory): ").strip().strip('"') or "."
    
    if not os.path.isdir(target):
        print("Invalid directory.")
        return

    interval_input = input("Enter interval for periodic cleaning (in minutes, 0 for once): ")
    try:
        interval = float(interval_input) * 60
    except ValueError:
        interval = 0

    while True:
        results = sort_folder(target)
        
        print("\n--- Summary Report ---")
        if not results:
            print("No files moved.")
        for category, count in results.items():
            print(f"{category}: {count} files")
        print(f"Check 'folder_sorter.log' for details.")

        if interval <= 0:
            break
        
        print(f"\nSleeping for {interval/60} minutes... (Ctrl+C to stop)")
        time.sleep(interval)

if __name__ == "__main__":
    main()
