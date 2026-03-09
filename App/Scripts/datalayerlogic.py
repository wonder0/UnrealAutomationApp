import unreal
from AutomationUtils.automation_helper import AutomationHelper

helper = AutomationHelper()
log = helper.log
dles = unreal.get_editor_subsystem(unreal.DataLayerEditorSubsystem)

label = "Sample"
package_folder = "/Game/DataLayers"
# Corrected path construction
asset_path = f"{package_folder}/{label}.{label}"

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

# 1. Try to find the existing instance in the world
dl_instance = dles.get_data_layer_from_label(label)

# 2. If it doesn't exist, create the asset and then the world instance
if not dl_instance:
    # Check if asset exists in Content Browser, create if missing
    if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        create_data_layer_asset(label, package_folder)
    
    # Add the asset to the World Editor (Outliner)
    dl_instance = add_asset_to_world_data_layers(asset_path)

# 3. Add selected actors to the instance
if dl_instance:
    ok = dles.add_selected_actors_to_data_layer(dl_instance)
    log(f"Added selected actors to Data Layer '{label}': {ok}")
else:
    log(f"Error: Could not find or create Data Layer instance for '{label}'")
