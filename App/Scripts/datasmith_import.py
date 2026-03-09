import sys
import json
import unreal
import os
import time
import re
import traceback
from AutomationUtils.automation_helper import AutomationHelper
import AutomationUtils.datasmith_logic as datasmith_logic

# 1. Script Manifest
SCRIPT_MANIFEST = {
    "display_name": "Simple Datasmith Import",
    "inputs": [
        {
            "name": "source_folder",
            "type": "folder_path",
            "label": "Source Folder",
            "default": ""
        },
        {
            "name": "destination_folder",
            "type": "string",
            "label": "Destination Folder",
            "default": "Datasmith"
        },
        {
            "name": "data_layer",
            "type": "string",
            "label": "Data Layer",
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

helper = AutomationHelper()
params = get_params()
log = helper.log

# 3. Configuration
SOURCE_FOLDER = params.get("source_folder", "")
DESTINATION_PATH = "/Game/" + params.get("destination_folder")
DATA_LAYER = params.get("data_layer")

dles = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)

def create_data_layer_asset(asset_name, package_path):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    new_asset = asset_tools.create_asset(asset_name, package_path, unreal.DataLayerAsset, unreal.DataAssetFactory())
    if new_asset:
        unreal.EditorAssetLibrary.save_asset(new_asset.get_path_name())
        log(f"Successfully created DataLayerAsset: {asset_name}")
    return new_asset

def add_asset_to_world_data_layers(layer_asset_path):
    layer_asset = unreal.load_asset(layer_asset_path)
    if not isinstance(layer_asset, unreal.DataLayerAsset):
        return None
    
    params = unreal.DataLayerCreationParameters()
    params.set_editor_property('data_layer_asset', layer_asset)
    return dles.create_data_layer_instance(params)

def handle_data_layer(data_layer_label, actors):
    if not data_layer_label:
        return

    label = data_layer_label
    package_folder = "/Game/DataLayers"
    asset_path = f"{package_folder}/{label}.{label}"

    dl_instance = dles.get_data_layer_from_label(label)

    if not dl_instance:
        if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            create_data_layer_asset(label, package_folder)
        dl_instance = add_asset_to_world_data_layers(asset_path)

    if dl_instance:
        unreal.EditorLevelLibrary.set_selected_level_actors(actors)
        ok = dles.add_selected_actors_to_data_layer(dl_instance)
        log(f"Added {len(actors)} actors to Data Layer '{label}': {ok}")
    else:
        log(f"Error: Could not find or create Data Layer instance for '{label}'")

def unparent_actors(actors):
    log(f"Unparenting {len(actors)} actors...")
    for actor in actors:
        if actor and actor.get_attach_parent_actor():
            actor.detach_from_actor(
                location_rule=unreal.DetachmentRule.KEEP_WORLD,
                rotation_rule=unreal.DetachmentRule.KEEP_WORLD,
                scale_rule=unreal.DetachmentRule.KEEP_WORLD
            )
    log("Unparenting complete.")

def main_process():
    if not SOURCE_FOLDER:
        log("Source folder is not defined. Please select a source folder.")
        return

    log(f"Scanning for Datasmith files in: {SOURCE_FOLDER}")
    datasmith_files = datasmith_logic.get_udatasmith_files(SOURCE_FOLDER)
    
    if not datasmith_files:
        log("No .udatasmith files found.")
        return

    log(f"Found {len(datasmith_files)} files to import.")

    for file_path in datasmith_files:
        file_name_with_ext = os.path.basename(file_path)
        root_actor_label = re.sub(r'\.udatasmith$', '', file_name_with_ext).replace('.', '_')
        
        log(f"--- Processing: {file_name_with_ext} ---")
        
        try:
            datasmith_logic.import_datasmith(file_path, DESTINATION_PATH, helper)
            
            root_actor, imported_actors = datasmith_logic.get_imported_actors(root_actor_label, helper)

            if imported_actors:
                unparent_actors(imported_actors)
                handle_data_layer(DATA_LAYER, imported_actors)
            
            datasmith_logic.remove_cameras_from_scene(helper)
            time.sleep(2)
            
            if root_actor:
                geometry_folder = f"{DESTINATION_PATH}/{root_actor_label}/Geometries"
                duplicate_map = datasmith_logic.find_in_memory_duplicate_meshes(geometry_folder, helper)

                if duplicate_map:
                    datasmith_logic.change_actor_meshes_to_master(duplicate_map, imported_actors, root_actor_label, DESTINATION_PATH, helper)
                    datasmith_logic.save_non_duplicate_geometries(duplicate_map, root_actor_label, DESTINATION_PATH, helper)

                    scene_asset_path = f"{DESTINATION_PATH}/{root_actor_label}"
                    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
                    assets = asset_registry.get_assets_by_path(scene_asset_path, recursive=False)
                    log(f"Processing scene asset at: {scene_asset_path}")

                    scene_asset = None
                    for asset_data in assets:
                        asset = asset_data.get_asset()
                        if isinstance(asset, unreal.DatasmithScene):
                            scene_asset = asset
                            break

                    if scene_asset:
                        log(f"Updating Datasmith Scene Asset: {scene_asset.get_path_name()}")
                        unreal.EditorAssetLibrary.save_asset(scene_asset.get_path_name())
                        log("Scene asset updated and saved successfully.")
                    else:
                        log(f"Could not find Datasmith Scene Asset to update at {scene_asset_path}")

            log(f"--- Successfully finished processing {file_name_with_ext} ---")

        except Exception as e:
            log(f"--- FAILED to process {file_name_with_ext}: {e} ---")
            log(f"Traceback: {traceback.format_exc()}")

    level_editor_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    level_editor_subsystem.save_current_level()
    log("Import process complete.")

# 4. Execution
if __name__ == "__main__":
    try:
        main_process()
    finally:
        helper.close()