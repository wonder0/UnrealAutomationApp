import unreal
import json
import sys
from AutomationUtils.automation_helper import AutomationHelper
import AutomationUtils.datasmith_logic as datasmith_logic


# 1. Script Manifest
SCRIPT_MANIFEST = {
    "display_name": "Simple Datasmith Import",
    "inputs": [
        {
            "name": "layer",
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


log(params.get("layer") + " is the layer")

# --------------------------------------------------------------------------------------
# USER CONFIGURATION
# --------------------------------------------------------------------------------------
# TAG_PREFIX = "Grid_" + params.get("layer")
TAG_PREFIX = "Grid_"
TARGET_FOLDER = "/Game/Levels/"+ params.get("layer")
BATCH_SIZE = 3000
DEBUG_SAMPLE = 5
# -----------------------------------------------------------------------------------------


# ======================================================================================
# UTILITY FUNCTIONS
# ======================================================================================


def ensure_folder(path):
    """Ensure a content folder exists."""
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.AssetToolsHelpers.get_asset_tools().create_directory(path)
        log(f"Created folder: {path}")
    else:
        log(f"Folder exists: {path}")


def extract_grid_tag(actor):
    """Return the grid tag from the actor."""
    try:
        for t in actor.tags:
            s = str(t)
            if s.startswith(TAG_PREFIX):
                return s
    except:
        pass
    return None


def load_actors_from_descriptors(descs):
    """Load actors from descriptors and return actual actor instances."""
    guids = [d.guid for d in descs]
    unreal.WorldPartitionBlueprintLibrary.load_actors(guids)
    return unreal.EditorLevelLibrary.get_all_level_actors()


def cut_actors(actor_list):
    """Clipboard-cut the actors and destroy originals."""
    if not actor_list:
        return False

    editor_actor_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

    try:
        unreal.SystemLibrary.execute_console_command(world, "EDIT COPY")

        arr = unreal.Array(unreal.Actor)
        for a in actor_list:
            arr.append(a)

        editor_actor_ss.destroy_actors(arr)
        log(f"Cut {len(arr)} actors.")
        return True

    except Exception as e:
        log(f"Failed cut: {e}")
        return False


def paste_actors():
    """Paste from clipboard and return pasted actors."""
    try:
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = editor.get_editor_world()

        unreal.SystemLibrary.execute_console_command(world, "EDIT PASTE")

        actor_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        pasted = actor_ss.get_selected_level_actors()
        log(f"Pasted {len(pasted)} actors.")
        return pasted

    except Exception as e:
        log(f"Paste error: {e}")
        return []


def get_desc_class_name(desc):
    try:
        return desc.native_class.get_name() if desc.native_class else ""
    except:
        return ""


def is_static_mesh_desc(desc):
    return "StaticMeshActor" in get_desc_class_name(desc)


def get_desc_label(desc):
    """
    Robustly fetch the descriptor label across engine variations.
    """
    # Common property name
    try:
        return str(desc.label)
    except Exception:
        pass

    # Some builds expose as actor_label
    try:
        return str(desc.actor_label)
    except Exception:
        pass

    # Generic editor property access
    try:
        return str(desc.get_editor_property("label"))
    except Exception:
        pass

    # Ultimate fallback: string of desc (rarely useful, but avoids exceptions)
    return ""


def find_descriptors_by_labels(label_set, all_descs):
    """
    Return descriptors whose label matches any string in label_set.
    Ensures we only match StaticMeshActor descriptors.
    """
    matched = []
    for d in all_descs:
        if not is_static_mesh_desc(d):
            continue
        lbl = get_desc_label(d)
        if lbl in label_set:
            matched.append(d)
    return matched


def find_loaded_actors_by_label(label_set):
    """Return loaded actors where actor_label is in a set of labels."""
    results = []
    for actor in unreal.EditorLevelLibrary.get_all_level_actors():
        try:
            if actor.get_actor_label() in label_set:
                results.append(actor)
        except:
            pass
    return results


# ======================================================================================
# MAIN PROCESSING LOGIC
# ======================================================================================

def process_by_grid_tags():

    # ensure_folder(TARGET_FOLDER)

    # Editor subsystems
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    persistent_level = level_editor.get_current_level()
    persistent_path = persistent_level.get_path_name()
    log(f"Persistent Level: {persistent_path}")

    # Collect ALL actor descriptors
    all_descs_initial = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
    if not all_descs_initial:
        log("No actor descriptors found!")
        return

    # Restrict to StaticMeshActor descriptors which are spatially loaded
    sm_descs = []
    for d in all_descs_initial:
        try:
            if d.is_spatially_loaded and is_static_mesh_desc(d):
                sm_descs.append(d)
        except:
            pass

    total = len(sm_descs)
    log(f"Found {total} spatially-loaded StaticMeshActor descriptors.")

    # --------------------------------------------------------------------------------------
    # Batch processing across all static mesh actors
    # --------------------------------------------------------------------------------------
    batch_count = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for bi in range(0, total, BATCH_SIZE):

        batch_descs = sm_descs[bi:bi + BATCH_SIZE]
        batch_index = bi // BATCH_SIZE + 1
        log(f"\n=== Batch {batch_index}/{batch_count} | {len(batch_descs)} actors ===")

        # 1) Load this batch (so we can modify tags/labels)
        loaded_actors = load_actors_from_descriptors(batch_descs)

        # 2) For each actor in the batch:
        #    - capture original label (as tag)
        #    - rename label to internal name (stable identity)
        #    - build mappings and group by grid
        batch_internal_names = []                      # Identity list for this batch
        internal_to_original_label = {}                # internal_name -> original_label
        grid_to_internal_names = {}                    # grid_tag -> [internal_name]

        for actor in loaded_actors:
            # Extract original label and add as tag
            orig_label = actor.get_actor_label()
            tags = list(actor.tags)
            tags.append(orig_label)  # EXACT label stored as tag per your choice (A)
            actor.tags = tags

            # Internal (stable) name
            internal_name = actor.get_name()

            # Rename label to internal name (persistence target)
            actor.set_actor_label(internal_name)

            # Track
            batch_internal_names.append(internal_name)
            internal_to_original_label[internal_name] = orig_label

            # Categorize by grid
            grid_tag = extract_grid_tag(actor)
            if grid_tag:
                grid_to_internal_names.setdefault(grid_tag, []).append(internal_name)

        # DEBUG: log first 5 internal names for this batch
        sample = batch_internal_names[:DEBUG_SAMPLE]
        # log(f"[DEBUG] Batch internal-name sample ({len(sample)}): {sample}")

        # Save persistent level to lock in name and tag changes
        level_editor.save_current_level()

        # 3) Create all required levels for this batch
        for grid_tag in grid_to_internal_names.keys():
            lvlname =  params.get("layer") + f"_{grid_tag}_"
            lvlasset = f"{TARGET_FOLDER}/{lvlname}.{lvlname}"
            if not unreal.EditorAssetLibrary.does_asset_exist(lvlasset):
                log(f"Creating new level: {lvlasset}")
                unreal.EditorLevelLibrary.new_level(f"{TARGET_FOLDER}/{lvlname}")
            else:
                log(f"Level exists: {lvlasset}")

        # Reload persistent level to regenerate descriptors and internal state
        level_editor.load_level(persistent_path)

        # 4) Reconstruct the same 1000 actors via descriptor.label == internal_name
        all_descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()

        # Precompute descriptor label universe for diagnostics
        # (first N labels just for debugging visibility)
        desc_label_universe = []
        for d in all_descs:
            if is_static_mesh_desc(d):
                lbl = get_desc_label(d)
                if lbl:
                    desc_label_universe.append(lbl)
        # log(f"[DEBUG] Descriptor label sample ({min(DEBUG_SAMPLE, len(desc_label_universe))}): "
        #     f"{desc_label_universe[:DEBUG_SAMPLE]}")

        # --------------------------------------------------------------------------------------
        # Sort grid categories by size descending
        # --------------------------------------------------------------------------------------
        sorted_grid_groups = sorted(grid_to_internal_names.items(), key=lambda x: len(x[1]), reverse=True)
        log("We have the sorted groups now")
        # --------------------------------------------------------------------------------------
        # Process grid categories
        # --------------------------------------------------------------------------------------
        for grid_tag, internal_name_list in sorted_grid_groups:
            log("Its entering here")
            expected_count = len(internal_name_list)
            log(f"\n-- Processing Grid {grid_tag} | Expecting {expected_count} actors --")

            # Always match by *internal names* first (the labels we set), but also
            # add a fallback of original labels in case label persistence failed for some.
            fallback_original_labels = [internal_to_original_label.get(n, "") for n in internal_name_list]
            name_match_set = set(internal_name_list) | set([l for l in fallback_original_labels if l])

            # Match descriptors against our expected label set
            grid_descs = find_descriptors_by_labels(name_match_set, all_descs)
            matched_count = len(grid_descs)

            if matched_count == 0:
                log("[WARN] No matching descriptors found for this grid.")
                log(f"[DEBUG] First expected labels: {list(name_match_set)[:DEBUG_SAMPLE]}")
                log(f"[DEBUG] First available desc labels: {desc_label_universe[:DEBUG_SAMPLE]}")
                continue

            if matched_count != expected_count:
                log(f"[WARN] Descriptor match count mismatch. Matched {matched_count} / Expected {expected_count}")
                # Log a small diff sample
                matched_labels = set(get_desc_label(d) for d in grid_descs)
                missing = list(name_match_set - matched_labels)[:DEBUG_SAMPLE]
                extra = list(matched_labels - name_match_set)[:DEBUG_SAMPLE]
                if missing:
                    log(f"[DEBUG] Example missing: {missing}")
                if extra:
                    log(f"[DEBUG] Example unexpected matches: {extra}")

            # Load these actors for this grid
            unreal.WorldPartitionBlueprintLibrary.load_actors([d.guid for d in grid_descs])

            # Find actual loaded actors by their *current* label
            loaded_for_grid = find_loaded_actors_by_label(name_match_set)
            if not loaded_for_grid:
                log("[WARN] No loaded actors matched the desired labels in this grid after load.")
                continue

            # Select and cut them
            actor_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            arr = unreal.Array(unreal.Actor)
            for a in loaded_for_grid:
                arr.append(a)
            actor_ss.set_selected_level_actors(arr)

            if not cut_actors(arr):
                continue

            level_editor.save_current_level()

            # Load target grid level
            lvlname =  params.get("layer") + f"_{grid_tag}_"
            target_path = f"{TARGET_FOLDER}/{lvlname}"
            level_editor.load_level(target_path)

            # Paste them
            pasted = paste_actors()

            # Restore original labels from the *in-memory map* (most reliable)
            restored = 0
            for a in pasted:
                try:
                    current_internal_or_label = a.get_actor_label()  # after paste this is still the label used for match
                    # We want to restore the original label for this *internal identity*.
                    # Try both exact match and a slower scan if needed.
                    if current_internal_or_label in internal_to_original_label:
                        a.set_actor_label(internal_to_original_label[current_internal_or_label])
                        restored += 1
                    else:
                        # Slow path: find internal name via object name if needed
                        internal_name = a.get_name()
                        if internal_name in internal_to_original_label:
                            a.set_actor_label(internal_to_original_label[internal_name])
                            restored += 1
                except Exception:
                    pass

            log(f"Restored {restored}/{len(pasted)} labels for grid {grid_tag}.")

            level_editor.save_current_level()

            # Return to persistent
            level_editor.load_level(persistent_path)

            # Remove processed internal names from the batch list
            for nm in internal_name_list:
                if nm in batch_internal_names:
                    batch_internal_names.remove(nm)

        # --------------------------------------------------------------------------------------
        # End of batch
        # --------------------------------------------------------------------------------------
        log(f"Batch {batch_index} complete. Remaining (unmoved) in batch: {len(batch_internal_names)}")

    # --------------------------------------------------------------------------------------
    # ALL BATCHES DONE
    # --------------------------------------------------------------------------------------
    log("\n=== ALL STATIC MESH ACTORS PROCESSED SUCCESSFULLY ===")


# ======================================================================================
# ENTRY POINT
# ======================================================================================

if __name__ == "__main__":
    try:
        # params = get_params()
        process_by_grid_tags()
        log("hi")
        log(params.get("layer"))
    finally:
        helper.close()