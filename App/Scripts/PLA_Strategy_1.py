import unreal
import math
import os
from AutomationUtils.automation_helper import AutomationHelper

# ------------------------------------------------------------
# CONFIGURATION FOR GRID-BASED LEVEL INSTANCES (AEC PROJECT)
# ------------------------------------------------------------
GRID_SIZE_X = 10000.0  # 100m horizontal
GRID_SIZE_Y = 10000.0  # 100m horizontal
GRID_SIZE_Z = 5000.0   # 50m vertical (adjust for floor heights)

DATASMITH_FILES = [
    r"D:\SixFlagsAssets\ARC\QC02001-ATK-MOD-BIM-ARC-09-SR2-00001.nwc.udatasmith",
    # r"D:\SixFlagsAssets\ARC\QC02001-ATK-MOD-BIM-ARC-10-TL1-00001.nwc.udatasmith",
    # r"D:\SixFlagsAssets\ARC\QC02001-ATK-MOD-BIM-ARC-06-FE2-00001.nwc.udatasmith"
]

TARGET_FOLDER = "/Game/Levels/Chunks"
DATASMITH_IMPORT_PATH = "/Game/Datasmith"

helper = AutomationHelper()


# ------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------
def get_actor_bounding_box_center(actor):
    """
    Get the center of the actor's bounding box in world space
    """
    try:
        origin, box_extent = actor.get_actor_bounds(only_colliding_components=False)
        return origin
    except:
        return actor.get_actor_location()


def calculate_grid_cell(position, grid_size_x, grid_size_y, grid_size_z):
    """
    Calculate which grid cell a position belongs to
    Returns: (cell_x, cell_y, cell_z)
    """
    cell_x = math.floor(position.x / grid_size_x)
    cell_y = math.floor(position.y / grid_size_y)
    cell_z = math.floor(position.z / grid_size_z)
    
    return (cell_x, cell_y, cell_z)


def get_chunk_name(cell_x, cell_y, cell_z):
    """
    Generate chunk name from grid coordinates
    """
    return f"Chunk_X{cell_x}_Y{cell_y}_Z{cell_z}"


def get_chunk_center_position(cell_x, cell_y, cell_z, grid_size_x, grid_size_y, grid_size_z):
    """
    Calculate the world-space center position of a chunk
    """
    center_x = (cell_x * grid_size_x) + (grid_size_x / 2)
    center_y = (cell_y * grid_size_y) + (grid_size_y / 2)
    center_z = (cell_z * grid_size_z) + (grid_size_z / 2)
    
    return unreal.Vector(center_x, center_y, center_z)


def get_datasmith_actors(persistent_level):
    """
    Get all StaticMeshActors from the most recent Datasmith import
    We'll identify them by checking if they're in the persistent level
    """
    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    
    # Filter for StaticMeshActors that are in the persistent level
    datasmith_actors = []
    for actor in all_actors:
        if isinstance(actor, unreal.StaticMeshActor):
            # Check if actor is in persistent level (not in a sublevel)
            actor_level = actor.get_level()
            if actor_level == persistent_level:
                datasmith_actors.append(actor)
    
    return datasmith_actors


def ensure_chunk_level_exists(chunk_path):
    """
    Ensure chunk level exists, create if it doesn't
    Returns True if successful
    """
    chunk_exists = unreal.EditorAssetLibrary.does_asset_exist(chunk_path)
    
    if not chunk_exists:
        helper.log(f"    Creating new chunk level: {chunk_path}")
        
        # Create new level
        new_level = unreal.EditorLevelLibrary.new_level(chunk_path)
        
        if not new_level:
            helper.log(f"    ERROR: Failed to create chunk level!")
            return False
        
        # Save the new level
        unreal.EditorLevelLibrary.save_current_level()
        helper.log(f"    ✓ Chunk level created and saved")
    else:
        helper.log(f"    ✓ Chunk level already exists: {chunk_path}")
    
    return True


def move_actors_to_chunk_level(actors, chunk_path, persistent_level_path):
    """
    Move actors from persistent level to chunk level using streaming level approach
    """
    if not actors:
        return 0
    
    helper.log(f"    Moving {len(actors)} actors to {chunk_path}")
    
    # Ensure we're in persistent level
    unreal.EditorLevelLibrary.load_level(persistent_level_path)
    
    # Get the persistent world
    world = unreal.EditorLevelLibrary.get_editor_world()
    
    # Add chunk as streaming level
    helper.log(f"    Adding chunk as streaming level...")
    streaming_level = unreal.EditorLevelUtils.add_level_to_world(
        world,
        chunk_path,
        unreal.LevelStreamingDynamic
    )
    
    if not streaming_level:
        helper.log(f"    ERROR: Failed to add streaming level!")
        return 0
    
    helper.log(f"    ✓ Streaming level added")
    
    # Get the actual level from streaming level
    chunk_level = streaming_level.get_loaded_level()
    
    if not chunk_level:
        helper.log(f"    ERROR: Could not get loaded level!")
        return 0
    
    # Move actors to the chunk level
    helper.log(f"    Moving actors...")
    moved_count = 0
    
    for actor in actors:
        try:
            success = unreal.EditorLevelUtils.move_actor_to_level(actor, chunk_level)
            if success:
                moved_count += 1
        except Exception as e:
            helper.log(f"    Warning: Could not move actor {actor.get_name()}: {e}")
    
    helper.log(f"    ✓ Moved {moved_count} actors")
    
    # Make chunk level current to save it
    unreal.EditorLevelUtils.make_level_current(streaming_level)
    
    # Save the chunk level
    helper.log(f"    Saving chunk level...")
    unreal.EditorLevelLibrary.save_current_level()
    helper.log(f"    ✓ Chunk level saved")
    
    # Return to persistent level
    unreal.EditorLevelLibrary.load_level(persistent_level_path)
    
    # Remove the streaming level reference (unload it)
    helper.log(f"    Unloading streaming level...")
    unreal.EditorLevelUtils.remove_level_from_world(streaming_level)
    helper.log(f"    ✓ Streaming level unloaded")
    
    return moved_count


def create_level_instance(level_path, spawn_location, instance_name):
    """
    Create a Level Instance actor in the current level
    """
    try:
        level_instance_class = unreal.load_class(None, '/Script/Engine.LevelInstance')
    except:
        try:
            level_instance_class = unreal.EditorAssetLibrary.load_blueprint_class(
                '/Engine/LevelInstance/LevelInstanceActor.LevelInstanceActor_C'
            )
        except:
            helper.log(f"    ERROR: Could not load LevelInstance class!")
            return False
    
    if level_instance_class:
        level_instance_actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            level_instance_class,
            spawn_location,
            unreal.Rotator(0, 0, 0)
        )
        
        if level_instance_actor:
            level_asset = unreal.load_asset(level_path)
            if level_asset:
                level_instance_actor.set_editor_property('world_asset', level_asset)
                level_instance_actor.set_actor_label(f"LI_{instance_name}")
                return True
            else:
                helper.log(f"    ERROR: Could not load level asset: {level_path}")
                return False
        else:
            helper.log(f"    ERROR: Failed to spawn Level Instance actor")
            return False
    
    return False


# ------------------------------------------------------------
# MAIN WORKFLOW
# ------------------------------------------------------------
def process_datasmith_with_grid_chunking():
    """
    Main function to process Datasmith files and create grid-based chunks
    """
    # Get persistent level path
    persistent_world = unreal.EditorLevelLibrary.get_editor_world()
    persistent_level_path = persistent_world.get_path_name().split('.')[0]
    
    helper.log(f"Persistent level: {persistent_level_path}")
    helper.log(f"Starting grid-based chunking process...")
    helper.log(f"Grid size: X={GRID_SIZE_X}, Y={GRID_SIZE_Y}, Z={GRID_SIZE_Z}\n")
    
    # Dictionary to track all chunks created across all imports
    all_chunks = {}
    
    # Process each Datasmith file
    for file_index, datasmith_file in enumerate(DATASMITH_FILES, 1):
        helper.log(f"\n{'='*80}")
        helper.log(f"PROCESSING DATASMITH FILE {file_index}/{len(DATASMITH_FILES)}")
        helper.log(f"File: {datasmith_file}")
        helper.log(f"{'='*80}\n")
        
        # ------------------------------------------------------------
        # STEP 1: IMPORT DATASMITH TO PERSISTENT LEVEL
        # ------------------------------------------------------------
        helper.log("STEP 1: Importing Datasmith to persistent level...")
        
        # Ensure we're in persistent level
        unreal.EditorLevelLibrary.load_level(persistent_level_path)
        
        # Import Datasmith
        task = unreal.AssetImportTask()
        task.filename = datasmith_file
        task.destination_path = DATASMITH_IMPORT_PATH
        task.factory = unreal.DatasmithImportFactory()
        task.automated = True
        task.replace_existing = True
        
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        helper.log("  ✓ Datasmith import completed")
        
        # Save persistent level after import
        unreal.EditorLevelLibrary.save_current_level()
        helper.log("  ✓ Persistent level saved after import")
        
        # ------------------------------------------------------------
        # STEP 2: GET ONLY NEWLY IMPORTED (UNSAVED) ACTORS
        # ------------------------------------------------------------
        helper.log("\nSTEP 2: Getting newly imported (unsaved) actors...")

        # Get all actors in the persistent level
        all_actors = unreal.EditorLevelLibrary.get_all_level_actors()

        # Filter for StaticMeshActors that are in the persistent level and are unsaved (dirty)
        imported_actors = []
        for actor in all_actors:
            if isinstance(actor, unreal.StaticMeshActor):
                
                # Check if the actor's package is dirty (unsaved)
                try:
                    actor_package = actor.get_outer()
                    if actor_package and actor_package.is_dirty():
                        imported_actors.append(actor)
                except:
                    # If we can't check dirty status, include it anyway
                    imported_actors.append(actor)

        helper.log(f"  Found {len(imported_actors)} unsaved StaticMeshActors from import")

        if len(imported_actors) == 0:
            helper.log("  WARNING: No unsaved actors found! Skipping this file.")
            continue
        # ------------------------------------------------------------
        # STEP 3: GROUP ACTORS BY GRID CELL
        # ------------------------------------------------------------
        helper.log("\nSTEP 3: Grouping actors by grid cell...")
        
        actors_by_cell = {}
        
        for actor in imported_actors:
            try:
                # Get bounding box center
                bbox_center = get_actor_bounding_box_center(actor)
                
                # Calculate grid cell
                cell_x, cell_y, cell_z = calculate_grid_cell(
                    bbox_center, 
                    GRID_SIZE_X, 
                    GRID_SIZE_Y, 
                    GRID_SIZE_Z
                )
                
                cell_key = (cell_x, cell_y, cell_z)
                
                if cell_key not in actors_by_cell:
                    actors_by_cell[cell_key] = []
                
                actors_by_cell[cell_key].append(actor)
                
            except Exception as e:
                helper.log(f"  Warning: Could not process actor {actor.get_name()}: {e}")
        
        helper.log(f"  ✓ Actors grouped into {len(actors_by_cell)} cells")
        
        for cell_key, actors in actors_by_cell.items():
            chunk_name = get_chunk_name(*cell_key)
            helper.log(f"    {chunk_name}: {len(actors)} actors")
        
        # ------------------------------------------------------------
        # STEP 4: PROCESS EACH CELL - CREATE/LOAD CHUNK AND MOVE ACTORS
        # ------------------------------------------------------------
        helper.log("\nSTEP 4: Processing each cell...")
        
        for cell_index, (cell_key, actors) in enumerate(actors_by_cell.items(), 1):
            cell_x, cell_y, cell_z = cell_key
            chunk_name = get_chunk_name(*cell_key)
            chunk_path = f"{TARGET_FOLDER}/{chunk_name}"
            
            helper.log(f"\n  [{cell_index}/{len(actors_by_cell)}] Processing {chunk_name}...")
            helper.log(f"    Cell: ({cell_x}, {cell_y}, {cell_z})")
            helper.log(f"    Actors: {len(actors)}")
            
            # Track this chunk
            all_chunks[chunk_name] = cell_key
            
            # Ensure chunk level exists
            if not ensure_chunk_level_exists(chunk_path):
                helper.log(f"    ERROR: Could not create chunk level, skipping...")
                continue
            
            # Return to persistent level
            unreal.EditorLevelLibrary.load_level(persistent_level_path)
            
            # Move actors to chunk
            # moved_count = move_actors_to_chunk_level(actors, chunk_path, persistent_level_path)
            
            helper.log(f"  ✓ {chunk_name}: {moved_count}/{len(actors)} actors moved")
        
        # ------------------------------------------------------------
        # STEP 5: SAVE PERSISTENT LEVEL AFTER PROCESSING THIS FILE
        # ------------------------------------------------------------
        helper.log("\nSTEP 5: Saving persistent level...")
        
        unreal.EditorLevelLibrary.load_level(persistent_level_path)
        unreal.EditorLevelLibrary.save_current_level()
        
        helper.log(f"  ✓ Persistent level saved")
        helper.log(f"\n✓ Completed processing file {file_index}/{len(DATASMITH_FILES)}")
    
    # ------------------------------------------------------------
    # STEP 6: CREATE LEVEL INSTANCES FOR ALL CHUNKS
    # ------------------------------------------------------------
    helper.log(f"\n{'='*80}")
    helper.log("STEP 6: Creating Level Instances in persistent level...")
    helper.log(f"{'='*80}\n")
    
    # Ensure we're in persistent level
    unreal.EditorLevelLibrary.load_level(persistent_level_path)
    
    for chunk_index, (chunk_name, cell_key) in enumerate(all_chunks.items(), 1):
        cell_x, cell_y, cell_z = cell_key
        chunk_path = f"{TARGET_FOLDER}/{chunk_name}"
        
        # Calculate spawn location at chunk center
        spawn_location = get_chunk_center_position(
            cell_x, cell_y, cell_z,
            GRID_SIZE_X, GRID_SIZE_Y, GRID_SIZE_Z
        )
        
        helper.log(f"  [{chunk_index}/{len(all_chunks)}] Creating Level Instance: {chunk_name}")
        helper.log(f"    Position: ({spawn_location.x:.1f}, {spawn_location.y:.1f}, {spawn_location.z:.1f})")
        
        success = create_level_instance(chunk_path, spawn_location, chunk_name)
        
        if success:
            helper.log(f"    ✓ Level Instance created")
        else:
            helper.log(f"    ✗ Failed to create Level Instance")
    
    # ------------------------------------------------------------
    # STEP 7: FINAL SAVE
    # ------------------------------------------------------------
    helper.log("\nSTEP 7: Final save...")
    unreal.EditorLevelLibrary.save_current_level()
    helper.log("  ✓ Persistent level saved")
    
    # ------------------------------------------------------------
    # FINAL SUMMARY
    # ------------------------------------------------------------
    helper.log(f"\n{'='*80}")
    helper.log("PROCESS COMPLETED SUCCESSFULLY!")
    helper.log(f"{'='*80}")
    helper.log(f"Total Datasmith files processed: {len(DATASMITH_FILES)}")
    helper.log(f"Total chunks created: {len(all_chunks)}")
    helper.log(f"Grid size: X={GRID_SIZE_X}, Y={GRID_SIZE_Y}, Z={GRID_SIZE_Z}")
    helper.log(f"\nChunk list:")
    for chunk_name in sorted(all_chunks.keys()):
        cell_key = all_chunks[chunk_name]
        helper.log(f"  - {chunk_name} at cell {cell_key}")
    
    helper.log(f"\n✓ All done! Check your persistent level for Level Instances.")


# ------------------------------------------------------------
# RUN THE WORKFLOW
# ------------------------------------------------------------
if __name__ == "__main__":
    process_datasmith_with_grid_chunking()