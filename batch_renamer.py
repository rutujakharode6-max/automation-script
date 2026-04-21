import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("renamer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

HISTORY_FILE = "rename_history.json"

def get_files(directory):
    """Returns a list of files in the directory, excluding the scripts and history."""
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) 
            and f not in {HISTORY_FILE, "renamer.log", "batch_renamer.py"}]

def apply_patterns(files, directory, pattern_type, **kwargs):
    """Calculates new names based on patterns."""
    new_names = []
    for i, filename in enumerate(files):
        name, ext = os.path.splitext(filename)
        new_name = name
        
        if pattern_type == 'prefix':
            new_name = kwargs.get('prefix', '') + name
        elif pattern_type == 'suffix':
            new_name = name + kwargs.get('suffix', '')
        elif pattern_type == 'replace':
            old = kwargs.get('old', '')
            new = kwargs.get('new', '')
            if kwargs.get('use_regex', False):
                try:
                    new_name = re.sub(old, new, name)
                except Exception as e:
                    logger.error(f"Regex error: {e}")
            else:
                new_name = name.replace(old, new)
        elif pattern_type == 'numbering':
            start = kwargs.get('start', 1)
            padding = kwargs.get('padding', 3)
            new_name = f"{name}_{str(start + i).zfill(padding)}"
        elif pattern_type == 'date':
            date_str = datetime.now().strftime(kwargs.get('format', '%Y%m%d'))
            new_name = f"{name}_{date_str}"
            
        new_names.append(new_name + ext)
    return new_names

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return None

def undo_rename(directory):
    history = load_history()
    if not history:
        print("No history found to undo.")
        return

    print("\n--- Undo Preview ---")
    for current, original in history.items():
        print(f"{current} -> {original}")
    
    confirm = input("\nRestore these original names? (y/n): ").lower()
    if confirm == 'y':
        for current, original in history.items():
            try:
                os.rename(os.path.join(directory, current), os.path.join(directory, original))
                logger.info(f"Restored: {current} -> {original}")
            except Exception as e:
                logger.error(f"Failed to restore {current}: {e}")
        os.remove(HISTORY_FILE)
        print("Undo complete.")

def main():
    print("=== Batch File Renamer CLI ===")
    directory = input("Enter directory path: ").strip().strip('"')
    if not os.path.isdir(directory):
        print("Invalid directory.")
        return

    while True:
        files = get_files(directory)
        if not files:
            print("No files found in directory.")
            break

        print(f"\nTarget Directory: {directory}")
        print("1. Add Prefix")
        print("2. Add Suffix")
        print("3. Replace Text / Regex")
        print("4. Sequential Numbering")
        print("5. Add Date Stamp")
        print("6. Undo Last Rename")
        print("Q. Quit")
        
        choice = input("\nSelect an option: ").upper()
        if choice == 'Q': break
        if choice == '6':
            undo_rename(directory)
            continue

        kwargs = {}
        pattern_type = ''
        
        if choice == '1':
            pattern_type = 'prefix'
            kwargs['prefix'] = input("Enter prefix: ")
        elif choice == '2':
            pattern_type = 'suffix'
            kwargs['suffix'] = input("Enter suffix: ")
        elif choice == '3':
            pattern_type = 'replace'
            kwargs['old'] = input("Text/Pattern to find: ")
            kwargs['new'] = input("Replacement text: ")
            kwargs['use_regex'] = input("Use Regex? (y/n): ").lower() == 'y'
        elif choice == '4':
            pattern_type = 'numbering'
            kwargs['start'] = int(input("Start numbering from (default 1): ") or 1)
            kwargs['padding'] = int(input("Zero padding (default 3): ") or 3)
        elif choice == '5':
            pattern_type = 'date'
            kwargs['format'] = input("Date format (default %Y%m%d): ") or '%Y%m%d'
        else:
            print("Invalid choice.")
            continue

        new_names = apply_patterns(files, directory, pattern_type, **kwargs)
        
        # Preview
        print("\n--- Rename Preview ---")
        preview_map = {}
        for old, new in zip(files, new_names):
            if old != new:
                print(f"{old} -> {new}")
                preview_map[new] = old

        if not preview_map:
            print("No changes would be made.")
            continue

        confirm = input("\nApply these changes? (y/n): ").lower()
        if confirm == 'y':
            history = {}
            for old, new in zip(files, new_names):
                if old != new:
                    try:
                        os.rename(os.path.join(directory, old), os.path.join(directory, new))
                        history[new] = old
                        logger.info(f"Renamed: {old} -> {new}")
                    except Exception as e:
                        logger.error(f"Error renaming {old}: {e}")
            save_history(history)
            print("Rename complete.")

if __name__ == "__main__":
    main()
