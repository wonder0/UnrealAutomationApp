import time
import sys
import json
from AutomationUtils.automation_helper import AutomationHelper

SCRIPT_MANIFEST = {
    "display_name": "Test Script with Parameters",
    "inputs": [
        {
            "name": "source_folder",
            "label": "Source Directory",
            "type": "folder_path",
            "default": "D:/Assets"
        },
        {
            "name": "force_import",
            "label": "Force Re-import",
            "type": "bool",
            "default": False
        },
        {
            "name": "texture_scale",
            "label": "Texture Scale",
            "type": "float",
            "default": 1.0
        },
        {
            "name": "item_count",
            "label": "Number of Items",
            "type": "int",
            "default": 20
        }
    ]
}

def get_params():
    if len(sys.argv) >= 3 and sys.argv[1] == '--params':
        try:
            return json.loads(sys.argv[2])
        except:
            return {}
    return {}

helper = AutomationHelper()
helper.log("Starting Script 1 with Parameters")

params = get_params()
helper.log(f"Received parameters: {params}")

source_folder = params.get('source_folder', 'N/A')
force_import = params.get('force_import', False)
texture_scale = params.get('texture_scale', 1.0)
item_count = params.get('item_count', 20)

helper.log(f"Source Folder: {source_folder}")
helper.log(f"Force Import: {force_import}")
helper.log(f"Texture Scale: {texture_scale}")
helper.log(f"Item Count: {item_count}")

for i in range(item_count):
    helper.check_signals()
    helper.log(f"Processing item {i+1} of {item_count}...")
    time.sleep(0.5)

helper.log("Script Finished!")
helper.close()