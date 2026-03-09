
import unreal

# Get the editor subsystem
editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# Get selected actors
selected_actors = editor_actor_subsystem.get_selected_level_actors()

# Iterate through selected actors
for actor in selected_actors:
    # Get the actor's tags
    tags = actor.tags
    
    # If the actor has at least one tag
    if len(tags) > 0:
        # Set the actor label to the first tag
        actor.set_actor_label(str(tags[1]))
        unreal.log(f"Renamed {actor.get_name()} to {tags[1]}")
    else:
        unreal.log_warning(f"{actor.get_name()} has no tags")
