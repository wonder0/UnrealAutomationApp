import unreal
import math
from collections import defaultdict

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
# Define the size of the grid in each dimension (in meters).
# The script will convert these values to Unreal Units (1 meter = 100 UU).
GRID_SIZE_METERS = unreal.Vector(50.0, 50.0, 20.0)

# The base name for the folders created in the World Outliner.
# Folders will be named like: /Grid_X0_Y1_Z2
FOLDER_PREFIX = "Grid"

# -----------------------------------------------------------------------------
# SCRIPT LOGIC (No need to edit below this line)
# -----------------------------------------------------------------------------

def get_grid_coordinates_3d(location, grid_size_uu):
    """
    Calculates the 3D grid coordinates for a given world location.

    Args:
        location (unreal.Vector): The actor's world location.
        grid_size_uu (unreal.Vector): The size of the grid cells in Unreal Units.

    Returns:
        tuple: A tuple containing the (x, y, z) grid coordinates.
    """
    if grid_size_uu.x == 0 or grid_size_uu.y == 0 or grid_size_uu.z == 0:
        unreal.log_error("Grid size cannot be zero in any dimension.")
        return (0, 0, 0)

    grid_x = math.floor(location.x / grid_size_uu.x)
    grid_y = math.floor(location.y / grid_size_uu.y)
    grid_z = math.floor(location.z / grid_size_uu.z)
    
    return (grid_x, grid_y, grid_z)

def get_folder_path(grid_coords, prefix):
    """
    Generates the folder path string from grid coordinates.

    Args:
        grid_coords (tuple): The (x, y, z) grid coordinates.
        prefix (str): The prefix for the folder name.

    Returns:
        str: The final folder path as a string.
    """
    return f"{prefix}_X{grid_coords[0]}_Y{grid_coords[1]}_Z{grid_coords[2]}_"

def organize_static_meshes_by_grid():
    """
    Finds all Static Mesh Actors in the current level and moves them into
    folders in the World Outliner based on their 3D grid position.
    """
    unreal.log("Starting script: Organize Static Meshes by Grid Location...")
    
    # Convert grid size from meters to Unreal Units
    grid_size_uu = GRID_SIZE_METERS * 100.0

    # Get all actors from the current level and filter for StaticMeshActors
    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    static_mesh_actors = [actor for actor in all_actors if isinstance(actor, unreal.StaticMeshActor)]

    if not static_mesh_actors:
        unreal.log_warning("No Static Mesh Actors found in the current level. Nothing to do.")
        return

    num_actors_total = len(static_mesh_actors)
    unreal.log(f"Found {num_actors_total} Static Mesh Actors to organize.")

    # Group actors by folder path
    actors_by_folder = defaultdict(list)
    for actor in static_mesh_actors:
        location = actor.get_actor_location()
        grid_coords = get_grid_coordinates_3d(location, grid_size_uu)
        folder_path = get_folder_path(grid_coords, FOLDER_PREFIX)
        actors_by_folder[folder_path].append(actor)

    # Group all operations into a single undoable transaction
    with unreal.ScopedEditorTransaction("Organize Static Meshes into Grid Folders") as transaction:
        num_folders = len(actors_by_folder)
        with unreal.ScopedSlowTask(num_folders, "Moving actors into folders...") as slow_task:
            slow_task.make_dialog(True)

            for i, (folder_path, actors_in_folder) in enumerate(actors_by_folder.items()):
                if slow_task.should_cancel():
                    unreal.log_warning("Operation cancelled by user.")
                    break
                
                num_actors_in_folder = len(actors_in_folder)
                slow_task.enter_progress_frame(1, f"Moving {num_actors_in_folder} actors to '{folder_path}' ({i+1}/{num_folders})")
                
                # Move all actors for the current folder path at once
                for actor in actors_in_folder:
                    actor.set_folder_path(folder_path)

    unreal.log(f"Script finished. Organized {num_actors_total} actors into {len(actors_by_folder)} folders.")

# -----------------------------------------------------------------------------
# SCRIPT EXECUTION
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    organize_static_meshes_by_grid()
    unreal.EditorLevelLibrary.save_current_level()