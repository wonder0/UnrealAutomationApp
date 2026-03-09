import os
import shutil

SCRIPT_MANIFEST = {
    "display_name": "Simple Datasmith Import",
    "inputs": [
        {
            "name": "source_folder",
            "type": "folder_path",
            "label": "Source Folder",
            "default": ""
        }
    ]
}

# 2. Standard Parameter Parsing
def get_params():
    if len(sys.argv) >= 3 and sys.argv[1] == '--params':
        try:
            return json.loads(sys.argv[2])
        except:
            return {}
    return {}

params = get_params()

def sort_items_by_suffix(directory_path="."):
    """
    Sorts files and folders in a directory based on the last part of their
    name, which is delimited by a '-'.

    For example, an item named '5223348-ATR-ZZZ-ZZZ-M3-WF' will be moved
    to a folder named 'WF' inside the specified directory.
    """
    if not os.path.isdir(directory_path):
        print(f"Error: The directory '{directory_path}' was not found.")
        return

    print(f"Starting to sort items in: '{os.path.abspath(directory_path)}'")

    # Get a list of all items in the directory to avoid issues with moving
    # items during iteration.
    all_items = os.listdir(directory_path)

    for item_name in all_items:
        # Construct the full path of the item
        item_path = os.path.join(directory_path, item_name)

        # Extract the base name to split
        base_name = os.path.basename(item_name)
        
        # Split the name by the hyphen to find the sorting key
        name_parts = base_name.split('-')

        # We only process items that contain a hyphen in their name
        if len(name_parts) > 1:
            # The folder key is the last part of the name
            folder_key = name_parts[5]

            # In case the last part has a file extension, we remove it.
            # This handles both 'file-WF.txt' and 'folder-WF' correctly.
            folder_name = os.path.splitext(folder_key)[0]
            
            # Define the destination folder path
            dest_folder_path = os.path.join(directory_path, folder_name)

            # If the item is a directory and its name matches the destination
            # folder, we should not try to move it into itself.
            if os.path.isdir(item_path) and item_name == folder_name:
                print(f"Skipping '{item_name}' as it's a destination directory.")
                continue

            # Create the destination folder if it doesn't already exist
            try:
                os.makedirs(dest_folder_path, exist_ok=True)
            except OSError as e:
                print(f"Error creating directory '{dest_folder_path}': {e}")
                continue

            # Construct the final destination path for the item
            destination_path = os.path.join(dest_folder_path, item_name)

            # Move the item to the new folder
            try:
                shutil.move(item_path, destination_path)
                print(f"Moved '{item_name}' to '{folder_name}/'")
            except shutil.Error as e:
                # This can happen if an item with the same name already exists
                # in the destination.
                print(f"Could not move '{item_name}': {e}")
            except OSError as e:
                print(f"An OS error occurred while moving '{item_name}': {e}")

if __name__ == "__main__":
    # Specify the directory you want to sort.
    # To use the current directory where the script is located, use "."
    # To use a different directory, provide the path, e.g., "C:/Users/YourUser/Desktop/MyFolder"
    
    sort_items_by_suffix(params.get("source_folder", ""))
    print("\nSorting process completed.")