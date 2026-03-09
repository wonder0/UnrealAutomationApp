import unreal


def get_unloaded_actors_in_persistent_level():
    editor_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_subsystem.get_editor_world()
    
    # Get the world partition subsystem
    # world_partition_subsystem = unreal.get_editor_subsystem(unreal.WorldPartitionEditorLoaderAdapter)
    
    # Get all actor descriptors from World Partition
    actor_descs = unreal.WorldPartitionBlueprintLibrary.get_actor_descs()
    
    if actor_descs is None:
        print("No actor descriptors found. Are you in a World Partition level?")
        return []
    
    unloaded_actors = []
    print(len(actor_descs))
    for desc in actor_descs:
        # Check if the actor is NOT spatially loaded (meaning it's unloaded)
        if desc.is_spatially_loaded:
            # Get more details about the actor
            actor_info = {
                "label": desc.label,
                "path": desc.actor_path,
                "package": desc.actor_package,
                "class": desc.native_class,
                "guid": desc.guid,
                "bounds": str(desc.bounds)
            }
            unloaded_actors.append(actor_info)
    
    return unloaded_actors

if __name__ == '__main__':
    unloaded = get_unloaded_actors_in_persistent_level()

    print("--- UNLOADED ACTORS IN PERSISTENT LEVEL ---")

    if unloaded:
        # Create array for actors whose name starts with "Cube"
        cube_actors = []

        for actor in unloaded:
            if str(actor['label']).startswith('Cube'):
                cube_actors.append(actor)

        # Print all cube actors
        if cube_actors:
            print(f"\nFound {len(cube_actors)} actors starting with 'Cube':")
            for actor in cube_actors:
                print(f"Label: {actor['label']}")
                print(f"  Class: {actor['class']}")
                print(f"  Path: {actor['path']}")
                print(f"  Package: {actor['package']}")
                print(f"  GUID: {actor['guid']}")
                print(f"  Bounds: {actor['bounds']}")
                print("-" * 60)

            # Extract GUIDs for loading
            cube_guids = [actor['guid'] for actor in cube_actors]
            unreal.WorldPartitionBlueprintLibrary.load_actors(cube_guids)
        else:
            print("No actors starting with 'Cube' found.")
    else:
        print("No unloaded actors found.")

    print(f"\nTotal unloaded actors: {len(unloaded)}")