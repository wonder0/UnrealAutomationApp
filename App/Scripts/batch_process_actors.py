import unreal
import math
from collections import defaultdict
from AutomationUtils.automation_helper import AutomationHelper

# -------------------------------------------------------------------------
# USER CONFIGURATION
# -------------------------------------------------------------------------

BATCH_SIZE = 1000                               # Number of actors to process at a time
GRID_SIZE_METERS = unreal.Vector(50, 50, 20)    # Grid size in meters
TAG_PREFIX = "Grid"                             # Prefix for the grid tag (e.g., "Grid_X.._Y.._Z..")

helper = AutomationHelper()
log = helper.log

# -------------------------------------------------------------------------
# GRID LOGIC
# -------------------------------------------------------------------------

def get_grid_coordinates_3d(location: unreal.Vector, grid_size_uu: unreal.Vector):
    grid_x = math.floor(location.x / grid_size_uu.x)
    grid_y = math.floor(location.y / grid_size_uu.y)
    grid_z = math.floor(location.z / grid_size_uu.z)
    return (grid_x, grid_y, grid_z)

def get_grid_tag(grid_coords, prefix: str) -> str:
    """Return a single tag string encoding the grid coordinate."""
    return f"{prefix}_X{grid_coords[0]}_Y{grid_coords[1]}_Z{grid_coords[2]}"

def assign_grid_tag_to_loaded_static_meshes(grid_size_uu: unreal.Vector):
    """
    Applies a grid tag ONLY to currently loaded StaticMeshActors.
    This is called PER BATCH.
    """
    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    static_mesh_actors = [a for a in all_actors if isinstance(a, unreal.StaticMeshActor)]

    if not static_mesh_actors:
        log("No loaded StaticMeshActors found for this batch.")
        return

    # Compute tag target for each actor
    with unreal.ScopedEditorTransaction("Batch Grid Tagging"):
        for actor in static_mesh_actors:
            loc = actor.get_actor_location()
            coords = get_grid_coordinates_3d(loc, grid_size_uu)
            new_tag_str = get_grid_tag(coords, TAG_PREFIX)

            # Get current tags (Actor.Tags is an array of Name)
            try:
                tags = list(actor.get_editor_property("tags"))
            except Exception:
                # Fallback if needed
                tags = list(getattr(actor, "tags", []))

            # Remove any previous grid tags that match our prefix
            cleaned_tags = [t for t in tags if not str(t).startswith(f"{TAG_PREFIX}_")]

            # Add the new tag (ensure Name type)
            new_tag = unreal.Name(new_tag_str)
            if new_tag not in cleaned_tags:
                cleaned_tags.append(new_tag)

            # Write back
            actor.set_editor_property("tags", cleaned_tags)

# -------------------------------------------------------------------------
# WORLD PARTITION BATCH PROCESSING LOGIC
# -------------------------------------------------------------------------

def get_all_static_mesh_actor_descs():
    """Gather ALL StaticMeshActor descriptors from World Partition."""
    descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
    static_descs = []
    for d in descs:
        class_name = d.native_class.get_name() if d.native_class else ""
        if "StaticMeshActor" in class_name:
            static_descs.append(d)
    return static_descs

def chunk_list(lst, size):
    """Yield successive size-sized chunks from list."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

def unload_all_static_mesh_actors():
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()

    actor_descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
    if actor_descs is None:
        log("No actor descriptors found. Are you in a World Partition level?")
        return

    static_mesh_guids = []
    for desc in actor_descs:
        class_name = desc.native_class.get_name() if desc.native_class else ""
        if desc.is_spatially_loaded and "StaticMeshActor" in class_name:
            static_mesh_guids.append(desc.guid)

    if static_mesh_guids:
        log(f"Unloading {len(static_mesh_guids)} StaticMeshActors...")
        unreal.WorldPartitionBlueprintLibrary.unload_actors(static_mesh_guids)
        log("Done!")
    else:
        log("No loaded StaticMeshActors found.")

def process_batches():
    log("===== World Partition StaticMeshActor Grid Tagging =====")

    # Convert meters to Unreal Units (cm)
    grid_size_uu = GRID_SIZE_METERS * 100.0
    all_descs = get_all_static_mesh_actor_descs()
    total = len(all_descs)

    log(f"Found {total} StaticMeshActor descriptors.")

    batches = list(chunk_list(all_descs, BATCH_SIZE))
    batch_count = len(batches)

    for i, batch in enumerate(batches, 1):
        log(f"\n--- Processing batch {i}/{batch_count} ({len(batch)} actors) ---")

        # Load
        guids = [d.guid for d in batch]
        unreal.WorldPartitionBlueprintLibrary.load_actors(guids)
        log(f"Loaded {len(guids)} actors.")

        # Apply tagging logic
        assign_grid_tag_to_loaded_static_meshes(grid_size_uu)

        # Save level to persist tag changes
        unreal.EditorLevelLibrary.save_current_level()
        log("Batch saved.")

        import time
        time.sleep(3)

        # Unload to free memory
        unload_all_static_mesh_actors()
        log("Unloaded batch.")

    log("\n===== All batches processed successfully! =====")

# -------------------------------------------------------------------------
# EXECUTION
# -------------------------------------------------------------------------
if __name__ == "__main__":
    process_batches()