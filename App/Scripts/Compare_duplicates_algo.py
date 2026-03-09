import unreal
from AutomationUtils.automation_helper import AutomationHelper
import os
import time

# ===============================================================================
# HELPER & UTILITY FUNCTIONS
# ===============================================================================

def get_sorted_vertices(mesh, log_function):
    """
    Extracts and returns a sorted list of vertex positions for a given mesh.
    Sorting ensures a consistent order for comparison. Returns None if invalid.
    """
    try:
        smd = mesh.get_static_mesh_description(0)
        if not smd: return None
        
        positions = [(round(p.x, 3), round(p.y, 3), round(p.z, 3)) for i in range(smd.get_vertex_count()) if (p := smd.get_vertex_position(unreal.VertexID(i)))]
        positions.sort()
        return positions
    except Exception as e:
        log_function(f"[WARNING] Could not get vertices for {mesh.get_name()}: {e}")
        return None

# ===============================================================================
# TWO-PASS DUPLICATE DETECTION ANALYSIS
# ===============================================================================

def analyze_duplicates_in_passes(folder_path):
    """
    Executes a two-pass analysis to find duplicate meshes without moving any files.
    
    Pass 1: Uses a fast method to identify potential duplicate clusters in memory.
    Pass 2: Runs a precise analysis on those clusters to confirm true duplicates.
    """
    helper = AutomationHelper()
    log = helper.log
    start_time = time.time()

    log("====================================================")
    log("        Two-Pass Duplicate Analysis (No Move)       ")
    log("====================================================")
    log(f"Scanning Root Folder: {folder_path}\n")

    # --- Data Preparation ---
    asset_paths = unreal.EditorAssetLibrary.list_assets(folder_path, recursive=True, include_folder=False)
    mesh_assets = [asset for path in asset_paths if (asset := unreal.EditorAssetLibrary.load_asset(path)) and isinstance(asset, unreal.StaticMesh)]
    
    if not mesh_assets:
        log("[INFO] No static meshes found to analyze.")
        return

    # --- Pass 1: Coarse Clustering ---
    log("--- PASS 1: Finding potential duplicate clusters in memory... ---")
    coarse_clusters_map = {}
    for mesh in mesh_assets:
        try:
            if mesh.get_num_lods() == 0: continue
            num_triangles = mesh.get_static_mesh_description(0).get_triangle_count()
            bounds_str = f"({mesh.get_bounding_box().min.x:.4f})-({mesh.get_bounding_box().max.x:.4f})"
            fingerprint = (num_triangles, bounds_str)
            coarse_clusters_map.setdefault(fingerprint, []).append(mesh)
        except Exception as e:
            log(f"[ERROR] Pass 1 Analysis: Could not analyze {mesh.get_name()}: {e}")

    potential_groups = [group for group in coarse_clusters_map.values() if len(group) > 1]
    
    if not potential_groups:
        log("[INFO] Pass 1 did not find any potential duplicate clusters. Analysis complete.")
        return
        
    log(f"[INFO] Pass 1 identified {len(potential_groups)} potential duplicate clusters for further analysis.")

    # --- Pass 2: Precise Analysis on In-Memory Clusters ---
    log("\n--- PASS 2: Running precise analysis on potential clusters... ---")
    total_confirmed_duplicates = 0
    
    for group in potential_groups:
        log(f"  -> Analyzing a potential group of {len(group)} meshes...")
        
        vertex_data_map = {mesh: get_sorted_vertices(mesh, log) for mesh in group}
        vertex_data_map = {m: v for m, v in vertex_data_map.items() if v}
            
        processed_meshes = set()
            
        for i in range(len(group)):
            mesh_a = group[i]
            if mesh_a in processed_meshes or mesh_a not in vertex_data_map:
                continue

            current_group_duplicates = 0
            verts_a = vertex_data_map[mesh_a]
            processed_meshes.add(mesh_a)

            for j in range(i + 1, len(group)):
                mesh_b = group[j]
                if mesh_b in processed_meshes or mesh_b not in vertex_data_map:
                    continue
                    
                verts_b = vertex_data_map[mesh_b]
                if len(verts_a) != len(verts_b):
                    continue

                # Check for identical or mirrored match
                is_match = (verts_a == verts_b) or any(verts_a == sorted([(*v[:ax], -v[ax], *v[ax+1:]) for v in verts_b]) for ax in range(3))
                    
                if is_match:
                    current_group_duplicates += 1
                    processed_meshes.add(mesh_b)
            
            if current_group_duplicates > 0:
                log(f"    - Confirmed {current_group_duplicates} true duplicates for master: {mesh_a.get_name()}")
                total_confirmed_duplicates += current_group_duplicates

    # --- Final Summary ---
    log("\n====================================================")
    log("                       RESULTS                      ")
    log("====================================================")
    execution_time = time.time() - start_time
    log(f"Total Meshes Scanned: {len(mesh_assets)}")
    log(f"Potential Duplicate Groups Found in Pass 1: {len(potential_groups)}")
    log(f"Total Confirmed Duplicates (Identical or Mirrored): {total_confirmed_duplicates}")
    log(f"Total Execution Time: {execution_time:.2f} seconds.")
    log("====================================================")


if __name__ == "__main__":
    folder_to_scan = "/Game/Datasmith/M1-102-PAR-DC1-XX-BM036-BNM-ZZ-902140_4/Geometries/_Potential_Duplicates/Object_1250_Cluster_26/1"
    analyze_duplicates_in_passes(folder_to_scan)