# Scripts Overview
1. **Photo Organizer**: Sorts images by date.
2. **Duplicate Finder**: Removes duplicates based on content hash.
3. **Batch Renamer**: Renames files using custom patterns and regex.

## Features - Duplicate Finder
- **Content Hashing**: SHA256 verification.
- **Keep Strategies**: Choose to keep Oldest or Newest.
- **Reporting**: Summary of space saved.

## Features - Batch Renamer
- **Multiple Patterns**: Prefix, suffix, replace, numbering, and date stamps.
- **Regex Support**: Advanced search and replace logic.
- **Undo System**: One-click restoration of original filenames.
- **Preview**: See exactly what changes will happen before applying.

## Prerequisite
Ensure you have the `exifread` library installed for the Photo Organizer:
```bash
pip install exifread
```

## Running the Script
1. Open your terminal.
2. Navigate to the folder containing `photo_organizer.py`.
3. Run the script:
   ```bash
   python photo_organizer.py
   ```
4. Follow the prompts:
   - **Source Directory**: The folder where your messy photos are currently located.
   - **Destination Directory**: Where you want the organized folders (`2024/January/...`) to be created.

## Running the Duplicate Finder
1. Open your terminal.
2. Navigate to the folder containing `cli_duplicate_finder.py`.
3. Run the script:
   ```bash
   python cli_duplicate_finder.py
   ```
4. Follow the interactive prompts to:
   - Provide the scan path.
   - Choose a keep strategy (Oldest vs Newest).
   - Select an action (Move to 'Duplicates_Found' folder or Delete).
   - Enable mandatory Dry-Run mode if you want to preview first.

## Running the Batch Renamer
1. Open your terminal.
2. Navigate to the folder containing `batch_renamer.py`.
3. Run the script:
   ```bash
   python batch_renamer.py
   ```
4. Choose from the interactive menu:
   - Apply prefix/suffix.
   - Use Regex for complex replacements.
   - Add sequential numbering or dates.
   - Use the **Undo** option if you make a mistake.

## Example File Structure After Running
```
Destination/
  ├── 2023/
  │   ├── December/
  │   │   └── christmas_party.jpg
  ├── 2024/
  │   ├── January/
  │   │   └── new_years_eve.png
  │   └── February/
  │       └── valentines_day.jpg
```
