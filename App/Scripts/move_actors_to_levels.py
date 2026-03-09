import unreal
import json
import sys
from AutomationUtils.automation_helper import AutomationHelper

# --------------------------------------------------------------------------------------
# USER CONFIGURATION
# --------------------------------------------------------------------------------------
TAG_PREFIX = "Grid_"               # Tag prefix to categorize actors
TARGET_FOLDER = "/Game/Levels"     # Folder where new levels will be created
BATCH_SIZE = 1000                  # Process actors in batches
# --------------------------------------------------------------------------------------

helper = AutomationHelper()
log = helper.log


# ======================================================================================
# UTILITY FUNCTIONS
# ======================================================================================

def get_params():
    """UAT parameter parser."""
    if len(sys.argv) >= 3 and sys.argv[1] == "--params":
        try:
            return json.loads(sys.argv[2])
        except:
            pass
    return {}


def ensure_folder(path):
    """Ensure target folder exists."""
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        asset_tools.create_directory(path)
        log(f"Created folder: {path}")
    else:
        log(f"Folder exists: {path}")


def extract_tag_from_actor(actor, prefix):
    """Extract the first tag matching prefix from an actor."""
    try:
        for t in actor.tags:
            t = str(t)
            if t.startswith(prefix):
                return t
    except:
        pass
    return None


def load_actors_from_guids(guids):
    """Load actors via World Partition from a list of GUIDs."""
    unreal.WorldPartitionBlueprintLibrary.load_actors(guids)
    loaded = unreal.EditorLevelLibrary.get_all_level_actors()
    return loaded


def find_actors_by_guid(requested_guids):
    """Find currently loaded actors by GUID matching."""
    world_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    guid_map = {}

    for actor in world_actors:
        try:
            actor_guid = actor.actor_guid
            if actor_guid in requested_guids:
                guid_map.setdefault(actor_guid, actor)
        except:
            pass

    return guid_map


def cut_actors(actors):
    """Cut actors using EDIT COPY then destroy originals."""
    if not actors:
        return False

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    try:
        unreal.SystemLibrary.execute_console_command(world, "EDIT COPY")

        actor_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        arr = unreal.Array(unreal.Actor)
        for a in actors:
            arr.append(a)

        actor_ss.destroy_actors(arr)
        log(f"Cut {len(arr)} actors.")
        return True
    except Exception as e:
        log(f"Failed to cut actors: {e}")
        return False


def paste_actors():
    """Paste actors using clipboard."""
    editor_ss = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_ss.get_editor_world()

    try:
        unreal.SystemLibrary.execute_console_command(world, "EDIT PASTE")
        actor_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        pasted = actor_ss.get_selected_level_actors()
        log(f"Pasted {len(pasted)} actors.")
        return pasted
    except Exception as e:
        log(f"Failed to paste actors: {e}")
        return []


def move_guids_to_level(guids, persistent_level_path, target_level_path):
    """Move all actors for given GUIDs into a target level."""
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    # 1. Load actors from GUIDs
    unreal.WorldPartitionBlueprintLibrary.load_actors(guids)
    actor_map = find_actors_by_guid(guids)
    actors = list(actor_map.values())

    if not actors:
        log("No actors to move.")
        return

    # 2. Select actors
    actor_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    arr = unreal.Array(unreal.Actor)
    for a in actors:
        arr.append(a)
    actor_ss.set_selected_level_actors(arr)

    # 3. Cut actors from persistent level
    if not cut_actors(arr):
        return

    level_editor.save_current_level()

    # 4. Switch to target level
    level_editor.load_level(target_level_path)

    # 5. Paste actors there
    paste_actors()
    level_editor.save_current_level()

    # 6. Return to persistent level
    level_editor.load_level(persistent_level_path)


# ======================================================================================
# MAIN LOGIC — GRID TAG BATCH PROCESSING
# ======================================================================================

def process_by_grid_tags():

    ensure_folder(TARGET_FOLDER)

    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    persistent_level = level_editor.get_current_level()
    persistent_level_path = persistent_level.get_path_name()

    log(f"Persistent Level: {persistent_level_path}")

    # ----------------------------------------------------------------------
    # Gather all WP actor descriptors
    # ----------------------------------------------------------------------
    actor_descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
    if not actor_descs:
        log("No actor descriptors found. Are you in a World Partition level?")
        return

    static_mesh_descs = [
        d for d in actor_descs
        if d.is_spatially_loaded and d.native_class and "StaticMeshActor" in d.native_class.get_name()
    ]

    log(f"Found {len(static_mesh_descs)} StaticMeshActor descriptors.")

    # ----------------------------------------------------------------------
    # Batch processing loop
    # ----------------------------------------------------------------------
    batch_count = (len(static_mesh_descs) + BATCH_SIZE - 1) // BATCH_SIZE

    for bi in range(0, len(static_mesh_descs), BATCH_SIZE):

        batch_descs = static_mesh_descs[bi:bi + BATCH_SIZE]
        batch_guids = [d.guid for d in batch_descs]
        batch_num = bi // BATCH_SIZE + 1

        log(f"\n=== Batch {batch_num}/{batch_count} | {len(batch_guids)} actors ===")

        # ---------------------------------------------
        # Load batch to inspect tags
        # ---------------------------------------------
        unreal.WorldPartitionBlueprintLibrary.load_actors(batch_guids)
        loaded_actors = unreal.EditorLevelLibrary.get_all_level_actors()

        # Build tag groups: {tag_value: [GUIDs]}
        tag_groups = {}

        for actor in loaded_actors:
            guid = actor.actor_guid
            tag = extract_tag_from_actor(actor, TAG_PREFIX)
            if tag:
                tag_groups.setdefault(tag, []).append(guid)

        if not tag_groups:
            log("No tagged actors in this batch.")
            unreal.WorldPartitionBlueprintLibrary.unload_actors(batch_guids)
            continue

        # ---------------------------------------------
        # Create all required levels for this batch
        # ---------------------------------------------
        for tag_value in tag_groups.keys():
            level_name = f"{tag_value}_"
            asset_path = f"{TARGET_FOLDER}/{level_name}.{level_name}"

            if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                log(f"Creating level: {asset_path}")
                unreal.EditorLevelLibrary.new_level(f"{TARGET_FOLDER}/{level_name}")
            else:
                log(f"Level exists: {asset_path}")

        # ---------------------------------------------
        # Sort tag groups: largest first
        # ---------------------------------------------
        sorted_tags = sorted(tag_groups.items(), key=lambda x: len(x[1]), reverse=True)

        # ---------------------------------------------
        # Now process each grid group
        # ---------------------------------------------
        for tag_value, guids_for_tag in sorted_tags:

            level_name = f"{tag_value}_"
            target_level_path = f"{TARGET_FOLDER}/{level_name}"

            log(f"\n-- Processing Tag {tag_value} ({len(guids_for_tag)} GUIDs) --")

            # Load persistent level
            unreal.EditorLevelLibrary.load_level(persistent_level_path)    

            log(guids_for_tag)        
            # Move actors for this tag
            move_guids_to_level(
                guids_for_tag,
                persistent_level_path=persistent_level_path,
                target_level_path=target_level_path
            )

            # After move, restore original batch in persistent
            unreal.WorldPartitionBlueprintLibrary.load_actors(batch_guids)

        # ---------------------------------------------
        # After all tag groups, unload batch
        # ---------------------------------------------
        unreal.WorldPartitionBlueprintLibrary.unload_actors(batch_guids)
        log(f"Unloaded {len(batch_guids)} actors in batch.")

    log("\n=== ALL GRID PROCESSING COMPLETE ===")


# ======================================================================================
# ENTRY POINT
# ======================================================================================

if __name__ == '__main__':
    params = get_params()
    process_by_grid_tags()