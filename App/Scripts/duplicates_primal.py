import unreal
from AutomationUtils.automation_helper import AutomationHelper
import os

def find_and_consolidate_duplicates(folder_path, helper, tolerance=0.01):
    """
    Finds duplicate static meshes using a scale-invariant method and then
    consolidates each group (master and duplicates) into a new folder.

    Args:
        folder_path (str): The folder path to scan for assets.
        helper (AutomationHelper): An instance of the AutomationHelper for logging.
        tolerance (float): The tolerance for comparing normalized bounding box dimensions.
    """
    log = helper.log
    asset_paths = unreal.EditorAssetLibrary.list_assets(folder_path, recursive=True, include_folder=False)
    
    mesh_assets = []
    for path in asset_paths:
        try:
            asset = unreal.EditorAssetLibrary.load_asset(path)
            if isinstance(asset, unreal.StaticMesh):
                mesh_assets.append(asset)
        except Exception as e:
            log(f"Could not load asset at path {path}: {e}")

    if not mesh_assets:
        log(f"No Static Mesh assets found to analyze in: {folder_path}")
        return {}

    log(f"Analyzing {len(mesh_assets)} static meshes using a scale-invariant method...")
    unique_meshes_map = {}
    
    # --- Pass 1: Find Duplicates with Scale-Invariant Fingerprint ---
    for mesh in mesh_assets:
        try:
            if mesh.get_num_lods() == 0 or not (smd := mesh.get_static_mesh_description(0)):
                continue

            num_triangles = smd.get_triangle_count()
            bounds = mesh.get_bounding_box()
            size = bounds.max - bounds.min
            dims = sorted([size.x, size.y, size.z])
            shortest_side = dims[0]
            
            if shortest_side < 0.0001:
                normalized_dims_tuple = tuple(f"{d:.2f}" for d in dims)
            else:
                normalized_dims = [dim / shortest_side for dim in dims]
                rounded_dims = [round(d / tolerance) * tolerance for d in normalized_dims]
                normalized_dims_tuple = tuple(f"{d:.2f}" for d in rounded_dims)

            fingerprint = (num_triangles, normalized_dims_tuple)
            unique_meshes_map.setdefault(fingerprint, []).append(mesh)

        except Exception as e:
            log(f"Error analyzing {mesh.get_name()}: {e}")

    # --- Prepare the Consolidation Map ---
    consolidation_map = {}
    for fingerprint, mesh_group in unique_meshes_map.items():
        if len(mesh_group) > 1:
            mesh_group.sort(key=lambda m: m.get_path_name())
            master_mesh = mesh_group[0]
            duplicates = mesh_group[1:]
            consolidation_map[master_mesh] = duplicates

    total_duplicates = sum(len(v) for v in consolidation_map.values())
    log(f"Analysis complete. Found {len(consolidation_map)} unique meshes with a total of {total_duplicates} duplicates.")
    
    # --- Pass 2: Consolidate Files into New Folders ---
    if consolidation_map:
        consolidate_into_folders(consolidation_map, folder_path, helper)
    else:
        log("\n[INFO] No duplicates found, so no file organization is necessary.")

    log("\n[DONE] Duplicate analysis and consolidation process is complete.")
    return consolidation_map

def consolidate_into_folders(consolidation_map, base_scan_path, helper):
    """
    For each master mesh, creates a new folder and moves the master and its duplicates into it.

    Args:
        consolidation_map (dict): Dict of master assets to their duplicate assets.
        base_scan_path (str): The root path where the scan was performed.
        helper (AutomationHelper): The logger instance.
    """
    log = helper.log
    log("\n--- Starting Duplicate Consolidation into New Folders ---")
    moved_count = 0
    # Define a root folder for all consolidated assets to keep things tidy
    consolidation_root = os.path.join(base_scan_path, "_Consolidated_Duplicates")

    for master_mesh, duplicates in consolidation_map.items():
        # Create a unique folder name for the group
        new_folder_path = os.path.join(consolidation_root, f"{master_mesh.get_name()}_Group")
        log(f"\nProcessing group for master: {master_mesh.get_name()}")
        log(f" -> Target consolidation folder: {new_folder_path}")

        # Create a list of all assets that need to be moved for this group
        assets_to_move = [master_mesh] + duplicates

        for asset in assets_to_move:
            old_path = asset.get_path_name()
            new_path = os.path.join(new_folder_path, asset.get_name())

            if old_path == new_path:
                log(f"  - [SKIPPED] {asset.get_name()} is already in the target folder.")
                continue

            # Check if an asset with the same name already exists at the destination
            if unreal.EditorAssetLibrary.does_asset_exist(new_path):
                log(f"  - [ERROR] Cannot move {asset.get_name()}. An asset with this name already exists at {new_path}.")
                continue
            
            try:
                # rename_asset creates the directory structure if it doesn't exist and moves the asset
                unreal.EditorAssetLibrary.rename_asset(old_path, new_path)
                log(f"  -> [MOVED] {asset.get_name()} to {new_folder_path}")
                moved_count += 1
            except Exception as e:
                log(f"  - [ERROR] Failed to move {asset.get_name()}: {e}")

    log(f"\n--- Consolidation Complete: {moved_count} assets were moved into new folders. ---")


if __name__ == "__main__":
    automation_helper = AutomationHelper()
    
    # Define the root folder to scan for duplicates
    folder_to_scan = "/Game/Datasmith/M1-102-PAR-DC1-XX-BM036-BNM-ZZ-902140_4/Geometries"
    
    # Run the entire find-and-consolidate process
    find_and_consolidate_duplicates(folder_to_scan, automation_helper, tolerance=0.01)