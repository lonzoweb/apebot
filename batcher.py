import os
import logging

# =========================================================
# CONFIGURATION
# =========================================================

# ⚠️ IMPORTANT: Replace this placeholder with the actual
# path to your image directory (e.g., "images/tarot/")
TARGET_DIR = "/Users/jessealonso/Repos/apebot/images/tarot"

# =========================================================

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ExtensionRenamer")


def rename_extensions_to_jpg(directory: str):
    """Changes the extension of all .png files in the directory to .jpg."""
    count = 0

    if not os.path.isdir(directory):
        logger.error(f"FATAL: Target directory not found: '{directory}'")
        return

    logger.info(f"Starting extension change in directory: '{directory}'")

    # Iterate over all files in the target directory
    for filename in os.listdir(directory):

        # Split the file name and extension
        name, ext = os.path.splitext(filename)

        # Check if the file has the .png extension
        if ext.lower() == ".png":

            old_path = os.path.join(directory, filename)
            # Create the new filename with the .jpg extension
            new_filename = name + ".jpg"
            new_path = os.path.join(directory, new_filename)

            try:
                os.rename(old_path, new_path)
                logger.info(f"Renamed: '{filename}' -> '{new_filename}'")
                count += 1
            except Exception as e:
                logger.error(f"Failed to rename '{filename}': {e}")

    logger.info("--- Process Complete ---")
    logger.info(f"✅ Successfully changed {count} files from .png to .jpg.")


if __name__ == "__main__":
    rename_extensions_to_jpg(TARGET_DIR)
