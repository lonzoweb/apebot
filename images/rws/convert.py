import os
import shutil
import re

# -------------------------
# CONFIG
# -------------------------
ROOT = "/Users/jessealonso/Repos/apebot/images/rws/rwss"  # folder containing "Major Arcana"
OUTPUT = "/Users/jessealonso/Repos/apebot/images/rws"  # folder to move renamed files

MAJOR_NAMES = [
    "the fool",
    "the magician",
    "the high priestess",
    "the empress",
    "the emperor",
    "the hierophant",
    "the lovers",
    "the chariot",
    "strength",
    "the hermit",
    "wheel of fortune",
    "justice",
    "the hanged man",
    "death",
    "temperance",
    "the devil",
    "the tower",
    "the star",
    "the moon",
    "the sun",
    "judgement",
    "the world",
]

os.makedirs(OUTPUT, exist_ok=True)


# -------------------------
# HELPER FUNCTION
# -------------------------
def normalize(s):
    """Remove all non-alphanumeric characters and lowercase"""
    return re.sub(r"[^a-z0-9]", "", s.lower())


# -------------------------
# PROCESS MAJOR ARCANA
# -------------------------
def process_major():
    major_path = os.path.join(ROOT, "Major Arcana")
    print("Processing Major Arcana in:", major_path)

    if not os.path.exists(major_path):
        print("ERROR: Major Arcana folder does not exist!")
        return

    files = os.listdir(major_path)
    print("Found Major Arcana files:", files)

    for filename in files:
        if not filename.lower().startswith("tarot"):
            print("Skipping (does not start with 'tarot'):", filename)
            continue

        try:
            # extract part after 'tarot-'
            name_part = filename.split("-", 1)[1].rsplit(".", 1)[0]
        except IndexError:
            print("Skipping (cannot split filename correctly):", filename)
            continue

        name_part_clean = normalize(name_part)
        matched = False

        for index, full_name in enumerate(MAJOR_NAMES):
            # normalize both ways: with or without 'the ' to match your filenames
            smashed = normalize(full_name)
            smashed_no_the = normalize(full_name.replace("the ", ""))
            if name_part_clean in (smashed, smashed_no_the):
                num = f"{index:02d}"
                # always format output as "XX-name.jpg"
                formatted = name_part.lower().replace(" ", "-")
                ext = os.path.splitext(filename)[1]  # keep original extension
                new_name = f"{num}-{formatted}{ext.lower()}"
                src = os.path.join(major_path, filename)
                dst = os.path.join(OUTPUT, new_name)

                shutil.copy(src, dst)
                print("Copied Major:", new_name)
                matched = True
                break

        if not matched:
            print("No match found for:", filename)


# -------------------------
# RUN SCRIPT
# -------------------------
process_major()
print("Major Arcana conversion complete. Check folder:", OUTPUT)
