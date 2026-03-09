import unreal

def batch_pack_levels():
    # 1. Setup paths
    output_folder = "/Game/Packed"
    
    # Ensure the directory exists in the asset registry
    if not unreal.EditorAssetLibrary.does_directory_exist(output_folder):
        unreal.EditorAssetLibrary.make_directory(output_folder)
    
    # 2. Get selected levels
    selected_assets = unreal.EditorUtilityLibrary.get_selected_asset_data()
    world_assets = [a for a in selected_assets if a.asset_class_path.asset_name == "World"]
    
    if not world_assets:
        unreal.log_warning("Please select one or more Levels (Worlds) in the Content Browser.")
        return

    lib = unreal.PackedLevelToolsFunctionLibrary

    for asset_data in world_assets:
        world_path = str(asset_data.package_name)
        asset_name = str(asset_data.asset_name)
        
        # Construct the target path (C++ will append the .AssetName suffix)
        target_path = f"{output_folder}/BP_{asset_name}_Packed"
        
        unreal.log(f"--- Processing: {world_path} ---")
        
        # Call our C++ Plugin
        result = lib.create_packed_level_actor_from_world_asset(world_path, target_path)
        
        if result:
            unreal.log(f"SUCCESS: Created {target_path}")
        else:
            unreal.log_error(f"FAILED: Could not pack {world_path}")

# Run the tool
batch_pack_levels()