import unreal
from AutomationUtils.automation_helper import AutomationHelper
import AutomationUtils.datasmith_logic as datasmith_logic

helper = AutomationHelper()
# -------------------------------------------------------
# Helper: Compute scale/rotation/mirror-invariant fingerprint
# -------------------------------------------------------
def compute_edge_fingerprint(mesh):
    try:
        mesh_desc = mesh.get_static_mesh_description(0)
    except Exception:
        return None

    edge_count = mesh_desc.get_edge_count()
    lengths = []

    for i in range(edge_count):
        edge_id = unreal.EdgeID(i)
        if not mesh_desc.is_edge_valid(edge_id):
            continue

        verts = mesh_desc.get_edge_vertices(edge_id)
        if len(verts) != 2:
            continue
        
        v0 = mesh_desc.get_vertex_position(verts[0])
        v1 = mesh_desc.get_vertex_position(verts[1])
        length = (v1 - v0).length()

        if length > 0:
            lengths.append(length)

    if not lengths:
        return None

    max_len = max(lengths)

    normalized = [round(l / max_len, 4) for l in lengths]
    normalized.sort()

    return tuple(normalized)


# -------------------------------------------------------
# Main Duplicate Finder
# -------------------------------------------------------
def find_duplicate_meshes_with_logs(folder_path):
    log = helper.log

    log(f"Scanning folder: {folder_path}")

    asset_paths = unreal.EditorAssetLibrary.list_assets(folder_path, recursive=True, include_folder=False)

    mesh_assets = []
    for path in asset_paths:
        try:
            asset = unreal.EditorAssetLibrary.load_asset(path)
            if isinstance(asset, unreal.StaticMesh):
                mesh_assets.append(asset)
        except Exception as e:
            log(f"[ERROR] Could not load asset at path {path}: {e}")

    if not mesh_assets:
        log("[INFO] No static meshes found.")
        return {}

    log(f"[INFO] Found {len(mesh_assets)} static meshes. Processing...")

    unique_fingerprints = {}
    duplicates_map = {}

    for mesh in mesh_assets:
        try:
            fingerprint = compute_edge_fingerprint(mesh)
            if fingerprint is None:
                log(f"[WARNING] Mesh {mesh.get_name()} has no valid fingerprint. Skipping.")
                continue

            if fingerprint not in unique_fingerprints:
                unique_fingerprints[fingerprint] = mesh  # first (master)
                duplicates_map[mesh] = []
            else:
                master = unique_fingerprints[fingerprint]
                duplicates_map[master].append(mesh)

        except Exception as e:
            log(f"[ERROR] Failed analyzing mesh {mesh.get_name()}: {e}")

    # -------------------------------------------------------
    # Logging results
    # -------------------------------------------------------

    total_groups = len(duplicates_map)
    total_duplicates = sum(len(v) for v in duplicates_map.values())

    log("----------------------------------------------------")
    log(f"[RESULT] Unique Master Meshes: {total_groups}")
    log(f"[RESULT] Total Duplicate Meshes: {total_duplicates}")
    log("----------------------------------------------------")

    for master, dups in duplicates_map.items():
        log(f"[MASTER] {master.get_name()}  --> {len(dups)} duplicates")
        for d in dups:
            log(f"          - {d.get_name()}")

    log("----------------------------------------------------")
    log("[DONE] Duplicate mesh analysis complete.")
    log("----------------------------------------------------")

    return duplicates_map


# -------------------------------------------------------
# RUN SCRIPT (modify folder path here)
# -------------------------------------------------------
folder_to_scan = "/Game/Datasmith/M1-102-PAR-DC1-XX-BM036-BNM-ZZ-902140_nwc/Geometries"
find_duplicate_meshes_with_logs(folder_to_scan)