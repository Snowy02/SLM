You've spotted a crucial detail. Thank you for providing that example. The .. in the path indicates a relative path, and how it's interpreted depends entirely on where you run the script from. This can lead to confusing "File not found" errors.

The most robust and professional way to handle this is to work with absolute paths. An absolute path is the full path from the root of your file system (e.g., C:\Users\YourUser\Fourth_task\... or /home/youruser/Fourth_task/...), and it is unambiguous.

Let's fix this by updating both of our scripts to use absolute paths. This will make your pipeline much more reliable.

Action Plan: A 2-Step Fix

We will make a small but vital change to both discover_files.py and process_documents.py.

Step 1: Update discover_files.py to Save Absolute Paths

First, we need to ensure the file_paths.txt file is populated with full, absolute paths. This removes all ambiguity.

Open scripts/discover_files.py.

Replace its content with the following updated code. The key change is using .resolve() to get the absolute path.

Generated python
# In scripts/discover_files.py (REVISED AND ROBUST VERSION)

from pathlib import Path

# --- Configuration ---
# Define the root path of your project
# This assumes your script is in a 'scripts' subfolder
PROJECT_ROOT = Path(__file__).parent.parent

# Define the source directory and the output file using the project root
# Note: I corrected 'knowledge_spurce' to 'knowledge_source' to match our plan
# If your folder is truly named 'knowledge_spurce', change it here.
SOURCE_DIRECTORY = PROJECT_ROOT / "knowledge_source"
OUTPUT_FILE = PROJECT_ROOT / "scripts" / "file_paths.txt"


def discover_and_save_paths():
    """Finds all files in the source directory and saves their
    ABSOLUTE paths to a text file."""
    
    print("--- Starting Phase 2: File Discovery ---")
    
    if not SOURCE_DIRECTORY.exists():
        print(f"[ERROR] Source directory not found at: {SOURCE_DIRECTORY}")
        return

    # Using rglob('*') to find all files recursively
    # The .resolve() method converts each path to its absolute form
    all_files = [str(file.resolve()) for file in SOURCE_DIRECTORY.rglob('*') if file.is_file()]

    if not all_files:
        print(f"[WARNING] No files found in {SOURCE_DIRECTORY}")
        return

    print(f"Found {len(all_files)} files. Saving their absolute paths to {OUTPUT_FILE.name}...")

    # Write the absolute paths to the output file
    with open(OUTPUT_FILE, "w") as f:
        for path in all_files:
            f.write(path + "\n")

    print("--- File Discovery Complete ---")


if __name__ == "__main__":
    discover_and_save_paths()


Delete the old file_paths.txt. This is important to ensure you don't have a mix of old relative paths and new absolute paths.

Re-run the discovery script from your project root (Fourth_task):

Generated bash
python scripts/discover_files.py
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Now, if you open scripts/file_paths.txt, you will see full, unambiguous paths like C:\path\to\your\project\Fourth_task\knowledge_source\Azure\document.pdf.

Step 2: Proceed to Phase 3 with the Updated process_documents.py

The process_documents.py script I provided earlier is already quite robust because it uses pathlib. It should handle the new absolute paths correctly. However, I will re-post it here with a few minor tweaks and clearer comments to ensure it aligns perfectly with this new robust approach.

Why this works: The pathlib library is excellent at handling OS-specific path formats. It doesn't matter if the path in the text file uses forward slashes / or backslashes \; Path(path_string) will correctly interpret it. The relative_to() method also works perfectly with absolute paths, which is what we need to create a clean output filename.

Here is the finalized code for process_documents.py.

Open scripts/process_documents.py.

Use the following code. It's nearly identical to before, but it's guaranteed to work with the absolute paths you just generated.

Generated python
# In scripts/process_documents.py (Final Version)

import json
from pathlib import Path
from unstructured.partition.auto import partition
from tqdm import tqdm

# --- Configuration ---
# Define the root path of your project
PROJECT_ROOT = Path(__file__).parent.parent.resolve() # Use .resolve() for robustness

# Define the input file containing the list of document paths
INPUT_FILE_LIST = PROJECT_ROOT / "scripts" / "file_paths.txt"

# Define the directory where structured JSON outputs will be saved
OUTPUT_DIR = PROJECT_ROOT / "data_processed"

def process_all_documents():
    """
    Reads a list of ABSOLUTE file paths, processes each file using unstructured,
    and saves the structured output as a JSON file.
    """
    print("--- Starting Phase 3: Document Processing ---")

    # 1. Create the output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory created at: {OUTPUT_DIR}")

    # 2. Read the list of file paths to process
    if not INPUT_FILE_LIST.exists():
        print(f"[ERROR] The file list '{INPUT_FILE_LIST.name}' was not found.")
        print("Please run 'discover_files.py' first.")
        return
        
    with open(INPUT_FILE_LIST, "r") as f:
        # We read absolute paths, so no further resolution is needed
        file_paths = [line.strip() for line in f.readlines()]
    
    print(f"Found {len(file_paths)} files to process from {INPUT_FILE_LIST.name}")

    # 3. Process each file one by one
    success_count = 0
    error_count = 0
    
    for file_path_str in tqdm(file_paths, desc="Processing files"):
        # The string from the file is already an absolute path.
        # Path() handles both Windows and Unix style paths automatically.
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            print(f" [WARNING] File not found, skipping: {file_path_str}")
            error_count += 1
            continue

        # Create a clean, unique name for the output JSON file
        # based on its path relative to the PROJECT_ROOT.
        # This works perfectly even if file_path is absolute.
        try:
            relative_path = file_path.relative_to(PROJECT_ROOT)
            output_filename = str(relative_path).replace("\\", "_").replace("/", "_") + ".json"
            output_path = OUTPUT_DIR / output_filename
        except ValueError:
            # Fallback if the file is outside the project for some reason
            output_filename = file_path.name + ".json"
            output_path = OUTPUT_DIR / output_filename

        try:
            # Use unstructured's 'partition' to automatically handle any file type
            elements = partition(filename=str(file_path))

            dict_elements = [el.to_dict() for el in elements]

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(dict_elements, f, indent=4)
            
            success_count += 1

        except Exception as e:
            print(f" [ERROR] Failed to process {file_path_str}: {e}")
            error_count += 1

    print("\n--- Processing Complete ---")
    print(f"Successfully processed: {success_count} files")
    print(f"Failed to process: {error_count} files")
    print(f"Structured JSON output saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    process_all_documents()
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END
Your Next Steps

Make sure you have followed Step 1 above (updated discover_files.py, deleted the old file_paths.txt, and re-ran the script).

Make sure you have installed all the necessary libraries from the previous response (unstructured[all-docs], tqdm, and the Tesseract OCR engine).

Now, run the process_documents.py script from your project root:

Generated bash
python scripts/process_documents.py
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

This pipeline is now much more robust and should work flawlessly regardless of your operating system or where you run the scripts from. You are ready to move on to Phase 4 after this completes successfully.
