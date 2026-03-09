import unreal
from AutomationUtils.automation_helper import AutomationHelper
import AutomationUtils.datasmith_logic as datasmith_logic

# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------
TARGET_FOLDER = "/Game/Levels/Imported"
TARGET_NAME = "Chunk_01"
TARGET_LEVEL = f"{TARGET_FOLDER}/{TARGET_NAME}"

DATASMITH_FILE = r"D:\Sphere\ADS-ATR-MOD-ISD-ARL-ZZZ-000020_0.udatasmith"

helper = AutomationHelper()


# ------------------------------------------------------------
# 1. CREATE NEW STREAMING LEVEL (CHUNK_01)
# ------------------------------------------------------------
persistent_world = unreal.EditorLevelLibrary.get_editor_world()
helper.log("Checking persistent world...")

if not persistent_world:
    helper.log("Error: Persistent level does not exist.")
    raise RuntimeError("Persistent world not found")

helper.log("Persistent world found.")

# Check if the level already exists
existing_levels = unreal.EditorLevelUtils.get_levels(persistent_world)
existing_paths = [
    lvl.get_world_asset().get_path_name() 
    for lvl in existing_levels
    if hasattr(lvl, "get_world_asset") and lvl.get_world_asset()
]

helper.log("Existing sub-levels:")
for p in existing_paths:
    helper.log(f"  - {p}")

streaming_level = None

if TARGET_LEVEL in existing_paths:
    helper.log(f"{TARGET_NAME} already exists as a sub-level.")
    # Find the existing streaming level object
    for lvl in existing_levels:
        if hasattr(lvl, "get_world_asset") and lvl.get_world_asset():
            if lvl.get_world_asset().get_path_name() == TARGET_LEVEL:
                # Get the streaming level from the level object
                streaming_levels = persistent_world.get_streaming_levels()
                for sl in streaming_levels:
                    if sl.get_world_asset() and sl.get_world_asset().get_path_name() == TARGET_LEVEL:
                        streaming_level = sl
                        helper.log(f"Found existing streaming level: {TARGET_NAME}")
                        break
                break
else:
    helper.log(f"{TARGET_NAME} not found — creating new streaming level...")
    
    # Create a new streaming level
    streaming_level = unreal.EditorLevelUtils.create_new_streaming_level(
        level_streaming_class=unreal.LevelStreamingDynamic,
        new_level_path=TARGET_LEVEL,
        move_selected_actors_into_new_level=False
    )
    
    if streaming_level:
        helper.log(f"Successfully created streaming level: {TARGET_NAME}")
        
        # Set transform if needed (optional)
        streaming_level.set_editor_property("level_transform", unreal.Transform(
            location=unreal.Vector(0, 0, 0),
            rotation=unreal.Rotator(0, 0, 0),
            scale=unreal.Vector(1, 1, 1)
        ))
    else:
        helper.log("ERROR: Failed to create streaming level!")
        raise RuntimeError("Streaming level creation failed")

# Save the persistent world
unreal.EditorLevelLibrary.save_all_dirty_levels()
helper.log("Persistent world saved.")


# ------------------------------------------------------------
# 2. MAKE CHUNK_01 THE CURRENT LEVEL FOR EDITING
# ------------------------------------------------------------
if streaming_level:
    # Make this streaming level the current level
    unreal.EditorLevelUtils.make_level_current(streaming_level)
    helper.log(f"{TARGET_NAME} is now the active editing level. Ready for Datasmith import.")
else:
    helper.log("ERROR: No streaming level available for editing!")
    raise RuntimeError("Streaming level not available")


# ------------------------------------------------------------
# 3. IMPORT DATASMITH → CHUNK_01
# ------------------------------------------------------------
task = unreal.AssetImportTask()
task.filename = DATASMITH_FILE
task.destination_path = "/Game/Datasmith"
task.factory = unreal.DatasmithImportFactory()
task.automated = True
task.replace_existing = True

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
helper.log("Datasmith import completed.")


# ------------------------------------------------------------
# 4. SAVE CHUNK_01
# ------------------------------------------------------------
unreal.EditorLevelLibrary.save_current_level()
helper.log(f"Saved {TARGET_NAME} level.")


# ------------------------------------------------------------
# 5. CREATE PACKED LEVEL ACTOR (OPTIONAL - for optimization)
# ------------------------------------------------------------
# Get all actors in the current level
current_level = unreal.EditorLevelLibrary.get_editor_world().get_current_level()
all_actors = unreal.EditorLevelLibrary.get_all_level_actors()

# Filter actors that belong to the current streaming level
actors_in_level = [
    actor for actor in all_actors 
    if actor.get_outer() == current_level
]

helper.log(f"Found {len(actors_in_level)} actors in {TARGET_NAME}")

# You can create a Packed Level Actor here if needed
# This will be useful for your future workflow
# Uncomment when you're ready to pack:
"""
if len(actors_in_level) > 0:
    # Select the actors you want to pack
    unreal.EditorLevelLibrary.set_selected_level_actors(actors_in_level)
    
    # Create Packed Level Actor
    # Note: This typically requires using the editor's menu commands
    # or a custom blueprint/C++ implementation
    helper.log("Ready to create Packed Level Actor from selected actors")
"""

helper.log("COMPLETED: Streaming level created → made current → Datasmith imported → saved.")
helper.log(f"You can now find and reopen '{TARGET_LEVEL}' anytime to add more content.")