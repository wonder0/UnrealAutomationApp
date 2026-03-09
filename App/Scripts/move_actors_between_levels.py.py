import unreal

from AutomationUtils.automation_helper import AutomationHelper
import AutomationUtils.datasmith_logic as datasmith_logic

# 1. Script Manifest
SCRIPT_MANIFEST = {
    "display_name": "Simple Datasmith Import",
    "inputs": [
        
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

def cut_actors_to_clipboard(selected_actors):

    if selected_actors:
        # Use the EditorLevelLibrary context if console commands are crashing
        # Ensure the focus is on the editor world
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        log("trying")
        # Alternative to raw console command: Trigger through the specific Actor Subsystem if available, 
        # or wrap the command in a way that doesn't conflict with the UI thread.
        try:
            # We use 'EDIT COPY' but ensure we are targeting the correct context
            unreal.SystemLibrary.execute_console_command(world, "EDIT COPY")
            actor_ss.destroy_actors(selected_actors)
            log(f"Cut {len(selected_actors)} actors.")
        except Exception as e:
            log(f"Failed to cut actors: {e}")

def paste_actors_from_clipboard():
    """
    Pastes actors from the clipboard into the current editor world.
    """
    # Get the editor world context
    editor_ss = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor_ss.get_editor_world()
    
    if world:
        try:
            # Executes the native Unreal "Paste" command
            unreal.SystemLibrary.execute_console_command(world, "EDIT PASTE")
            
            # Retrieve the newly pasted actors (they will be the new selection)
            actor_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            pasted_actors = actor_ss.get_selected_level_actors()
            
            log(f"Successfully pasted {len(pasted_actors)} actors.")
            return pasted_actors
        except Exception as e:
            log(f"Failed to paste actors: {e}")
    else:
        log("Paste failed: No active editor world found.")
    return []




def move_selected_actors_to_level(target_level_path):
    level_editor_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    
    persistent_level_path = level_editor_subsystem.get_current_level().get_path_name()
    
    selected_actors = editor_actor_subsystem.get_selected_level_actors()
    
    if not selected_actors:
        log("No actors selected.")
        return
    
    cut_actors_to_clipboard(selected_actors)
    level_editor_subsystem.save_current_level() 
    
    level_editor_subsystem.load_level(target_level_path)
    
    paste_actors_from_clipboard()
    level_editor_subsystem.save_current_level()    
    
    level_editor_subsystem.load_level(persistent_level_path)
    
    log(f"Moved {len(selected_actors)} actors to {target_level_path}")

if __name__ == '__main__':
    target_path = "/Game/PackedLevelActors/MyPackedLevelActor_Level"
    move_selected_actors_to_level(target_path)