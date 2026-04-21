# Automation Script Toolkit

A collection of powerful Python utilities for organizing files, finding duplicates, and managing disk space effectively.

## 🚀 Included Tools

### 1. Photo Organizer (`photo_organizer.py`)
Automatically sorts images into a structured `Year/Month` folder hierarchy.
- **Precision**: Uses EXIF metadata ("Date Taken") for accurate sorting.
- **Safety**: Intelligent name conflict resolution (adds numeric suffixes).
- **Format Support**: JPG, PNG, GIF, BMP, TIFF, WebP, HEIC.

### 2. Duplicate Finder (`cli_duplicate_finder.py`)
Identifies and removes duplicate files based on content hash (SHA256).
- **Fast**: Efficiently groups files by size before hashing.
- **Flexible**: Choose to keep the oldest or newest version of a file.
- **Safe**: Includes a mandatory dry-run mode to preview changes.
- **Cleanup**: Option to move duplicates to a specific folder or delete them.

### 3. Batch File Renamer (`batch_renamer.py`)
A comprehensive renaming utility with an interactive menu.
- **Patterns**: Add prefixes/suffixes, replace text, add sequential numbers, or date stamps.
- **Advanced**: Full support for Regular Expressions (Regex).
- **Safety**: Real-time preview of changes and a one-click Undo system to restore original names.

### 4. Downloads Folder Sorter (`downloads_sorter.py`)
Keeps your workspace tidy by categorizing files into logical folders (Documents, Images, etc.).
- **Automatic**: Scans extensions and moves files to appropriate categories.
- **Periodic**: Support for automated cleaning intervals.
- **Cleanup**: Deletes empty subdirectories after sorting.

### 5. Old File Cleanup & Archive (`archive_cleanup.py`)
Manages disk space by targeting unused files based on age.
- **Categorization**: Groups files by age (30-90 days, 90-365 days, 1+ year).
- **Archiving**: Option to compress old files into ZIP archives before moving.
- **Safety**: Multi-step confirmation for deletions and whitelist support for critical files.

---

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rutujakharode6-max/automation-script.git
   ```
2. Navigate to the directory:
   ```bash
   cd automation-script
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 📖 Usage

Run any script using Python and follow the interactive prompts:
```bash
python photo_organizer.py
python cli_duplicate_finder.py
python batch_renamer.py
python downloads_sorter.py
python archive_cleanup.py
```

## 📝 Logging
All scripts generate detailed logs (`organizer.log`, `renamer.log`, etc.) so you can track precisely which files were moved, renamed, or deleted.

## 📜 License
MIT License
