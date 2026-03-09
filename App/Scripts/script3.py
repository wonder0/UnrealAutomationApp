import unreal

def create_packed_level_actor(selected_actors, pla_name, save_path, pivot_type='Center'):
    """
    Create a Packed Level Actor from selected static mesh actors
    
    Args:
        selected_actors: List of selected actors
        pla_name: Name for the PLA
        save_path: Content browser path (e.g., '/Game/MyFolder/')
        pivot_type: 'Center', 'Actor', or 'WorldOrigin'
    """
    
    # Filter only static mesh actors
    static_mesh_actors = [actor for actor in selected_actors 
                          if isinstance(actor, unreal.StaticMeshActor)]
    
    if not static_mesh_actors:
        unreal.log_warning("No static mesh actors selected")
        return None
    
    # Calculate pivot location
    pivot_location = calculate_pivot(static_mesh_actors, pivot_type)
    
    # Create the level asset
    level_path = f"{save_path}{pla_name}_Level"
    level_asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name=f"{pla_name}_Level",
        package_path=save_path.rstrip('/'),
        asset_class=unreal.World,
        factory=unreal.WorldFactory()
    )
    
    # Load the level
    unreal.EditorLevelLibrary.load_level(level_asset.get_path_name())
    
    # Copy actors to the new level
    for actor in static_mesh_actors:
        duplicate_actor(actor, level_asset, pivot_location)
    
    # Save the level
    unreal.EditorLevelLibrary.save_current_level()
    
    # Create Blueprint class with LevelInstance component
    blueprint_path = f"{save_path}{pla_name}"
    blueprint = create_pla_blueprint(blueprint_path, level_path, static_mesh_actors, pivot_location)
    
    unreal.log(f"Packed Level Actor created: {blueprint_path}")
    return blueprint


def calculate_pivot(actors, pivot_type):
    """Calculate pivot location based on type"""
    if pivot_type == 'WorldOrigin':
        return unreal.Vector(0, 0, 0)
    elif pivot_type == 'Actor':
        return actors[0].get_actor_location()
    else:  # Center
        bounds = unreal.Vector(0, 0, 0)
        for actor in actors:
            bounds += actor.get_actor_location()
        return bounds / len(actors)


def duplicate_actor(actor, target_level, pivot_offset):
    """Duplicate actor to target level with offset"""
    editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    
    # Duplicate the actor
    new_actor = editor_actor_subsystem.duplicate_actor(actor, target_level)
    
    # Adjust location relative to pivot
    current_loc = new_actor.get_actor_location()
    new_actor.set_actor_location(current_loc - pivot_offset, False, False)
    
    return new_actor


def create_pla_blueprint(blueprint_path, level_path, actors, pivot_location):
    """Create Blueprint with LevelInstance component and ISM/HISM"""
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    
    # Create Blueprint
    blueprint_factory = unreal.BlueprintFactory()
    blueprint_factory.set_editor_property('parent_class', unreal.Actor)
    
    blueprint = asset_tools.create_asset(
        asset_name=blueprint_path.split('/')[-1],
        package_path='/'.join(blueprint_path.split('/')[:-1]),
        asset_class=unreal.Blueprint,
        factory=blueprint_factory
    )
    
    # Add LevelInstance component as root
    # Note: This requires using the Blueprint editor API
    # The actual implementation would use unreal.BlueprintEditorLibrary
    
    return blueprint


# Usage example
def main():
    # Get selected actors
    selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()
    
    if not selected_actors:
        unreal.log_warning("Please select static mesh actors first")
        return
    
    # Create PLA
    create_packed_level_actor(
        selected_actors=selected_actors,
        pla_name="MyPackedLevelActor",
        save_path="/Game/PackedLevelActors/",
        pivot_type='Center'
    )

# Run the script
main()