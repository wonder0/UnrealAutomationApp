# "/Game/Temp_Import/EUW_MakeLevels.EUW_MakeLevels"

import unreal

# editor_utility_subsystem = unreal.EditorUtilitySubsystem()

# # Use the correct asset path format
# widget_asset_path = "/Game/Temp_Import/EUW_MakeLevels.EUW_MakeLevels"
# widget_asset = unreal.load_asset(widget_asset_path)

# if widget_asset:
#     spawned_widget = editor_utility_subsystem.spawn_and_register_tab(widget_asset)

#     # Use call_method to invoke Blueprint functions
#     if spawned_widget:
#         unreal.BlueprintFunctionLibrary.call_method(spawned_widget, "PrintFunc")


# import unreal

# # Fix 1: Use get_editor_subsystem (UE 5.2+)
# editor_utility_subsystem = unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem)
# widget_asset = unreal.load_asset("/Game/Temp_Import/EUW_MakeLevels.EUW_MakeLevels")

# if widget_asset:
#     spawned_widget = editor_utility_subsystem.spawn_and_register_tab(widget_asset)

#     if spawned_widget:
#         # Fix 2: Pass parameters as a list/tuple
#         unreal.BlueprintFunctionLibrary.call_method(
#             spawned_widget,
#             "PrintFunc",
#             ("John Doe", "Captain", 1500, True)  # All parameters in a list
#         )


# import unreal

# editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
# selected_actors = editor_actor_subsystem.get_selected_level_actors()

# if selected_actors:
#     editor_utility_subsystem = unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem)
#     widget_asset = unreal.load_asset("/Game/Temp_Import/EUW_MakeLevels.EUW_MakeLevels")
    
#     if widget_asset:
#         spawned_widget = editor_utility_subsystem.spawn_and_register_tab(widget_asset)
        
#         if spawned_widget:
#             unreal.BlueprintFunctionLibrary.call_method(
#                 spawned_widget,
#                 "PrintFunc",
#                 (selected_actors[0],)  # Note the comma for single-item tuple