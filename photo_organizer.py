import os
import shutil
import logging
import exifread
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("organizer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}

def get_creation_date(file_path):
    """
    Extracts the creation date from image metadata (EXIF) or file status.
    Returns a datetime object.
    """
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f, stop_tag='DateTimeOriginal', details=False)
            
            # Try to get the original date the photo was taken
            date_str = tags.get('EXIF DateTimeOriginal') or tags.get('Image DateTime')
            
            if date_str:
                # Format is usually YYYY:MM:DD HH:MM:SS
                return datetime.strptime(str(date_str), '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        logger.debug(f"Could not extract EXIF data from {file_path}: {e}")

    # Fallback to filesystem creation time (Windows) or modification time
    # On Windows, getctime is typically the creation time.
    timestamp = os.path.getctime(file_path)
    return datetime.fromtimestamp(timestamp)

def get_unique_path(target_dir, filename):
    """
    If a file exists at the target path, appends a suffix to make it unique.
    """
    base_name = os.path.splitext(filename)[0]
    extension = os.path.splitext(filename)[1]
    counter = 1
    
    unique_name = filename
    while os.path.exists(os.path.join(target_dir, unique_name)):
        unique_name = f"{base_name}_{counter}{extension}"
        counter += 1
        
    return os.path.join(target_dir, unique_name)

def organize_photos(source_dir, dest_dir):
    """
    Scans source_dir for images and moves them to dest_dir organized by YYYY/Month.
    """
    source_path = Path(source_dir)
    dest_path = Path(dest_dir)

    if not source_path.exists():
        logger.error(f"Source directory '{source_dir}' does not exist.")
        return

    if not dest_path.exists():
        dest_path.mkdir(parents=True)
        logger.info(f"Created destination directory: {dest_dir}")

    files_moved = 0
    files_skipped = 0
    errors = 0

    logger.info(f"Starting organization from '{source_dir}' to '{dest_dir}'...")

    for file in source_path.rglob('*'):
        if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS:
            try:
                # Get the creation date
                created_at = get_creation_date(file)
                
                year = created_at.strftime('%Y')
                month = created_at.strftime('%B') # Full month name

                # Define target directory: dest/YYYY/Month
                target_folder = dest_path / year / month
                target_folder.mkdir(parents=True, exist_ok=True)

                # Get unique path in case of filename conflict
                target_file_path = get_unique_path(target_folder, file.name)

                # Move the file
                shutil.move(str(file), target_file_path)
                logger.info(f"Moved: {file.name} -> {year}/{month}/")
                files_moved += 1

            except Exception as e:
                logger.error(f"Error processing {file}: {e}")
                errors += 1
        else:
            if file.is_file():
                logger.debug(f"Skipping non-image file: {file.name}")
                files_skipped += 1

    logger.info("Organization complete!")
    logger.info(f"Summary: Moved: {files_moved}, Skipped: {files_skipped}, Errors: {errors}")

def main():
    print("=== Photo Organizer Utility ===")
    source = input("Enter the source directory path: ").strip().strip('"')
    destination = input("Enter the destination directory path: ").strip().strip('"')

    if not source or not destination:
        print("Error: Both source and destination paths are required.")
        return

    organize_photos(source, destination)

if __name__ == "__main__":
    main()
