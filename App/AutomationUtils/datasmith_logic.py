import unreal
import os

def get_udatasmith_files(root_folder):
    files = []
    if not root_folder or not os.path.exists(root_folder):
        return files
        
    for root, _, f in os.walk(root_folder):
        for file in f:
            if file.endswith(".udatasmith"):
                files.append(os.path.join(root, file))
    return files

def has_translucent_or_masked_material(static_mesh):
    num_sections = static_mesh.get_num_sections(0)
    for section_index in range(num_sections):
        material = static_mesh.get_material(section_index)
        if not material:
            continue

        blend_mode = None
        if isinstance(material, unreal.MaterialInstanceConstant):
            parent_material = material.get_editor_property("parent")
            if parent_material:
                blend_mode = parent_material.get_editor_property("blend_mode")
            else:
                continue
        elif isinstance(material, unreal.Material):
            blend_mode = material.get_editor_property("blend_mode")
        else:
            continue

        if blend_mode in [unreal.BlendMode.BLEND_TRANSLUCENT, unreal.BlendMode.BLEND_MASKED]:
            return True
    
    return False

def save_the_levels(path, helper):
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    assets = asset_registry.get_assets_by_path(path, recursive=True)

    for asset_data in assets:
        asset = asset_data.get_asset()
        asset_path = asset.get_path_name()

        if "/Geometries/" in asset_path or asset_path.endswith("/Geometries"):
            continue

        if "/Materials/" in asset_path or asset_path.endswith("/Materials"):
            continue

        unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
        helper.log(f"Saved asset: {asset_path}")

    level_editor_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    level_editor_subsystem.save_current_level()

def find_in_memory_duplicate_meshes(folder_path, helper):
    asset_paths = unreal.EditorAssetLibrary.list_assets(folder_path, recursive=True, include_folder=False)
    
    mesh_assets = []
    for path in asset_paths:
        try:
            asset = unreal.EditorAssetLibrary.load_asset(path)
            if isinstance(asset, unreal.StaticMesh):
                mesh_assets.append(asset)
        except Exception as e:
            helper.log(f"Could not load asset at path {path}: {e}")

    if not mesh_assets:
        helper.log(f"No in-memory Static Mesh assets found to analyze in: {folder_path}")
        return {}

    helper.log(f"Analyzing {len(mesh_assets)} in-memory static meshes for duplicates...")
    unique_meshes_map = {}
    
    for mesh in mesh_assets:
        try:
            if mesh.get_num_lods() == 0:
                continue
            
            num_triangles = mesh.get_static_mesh_description(0).get_triangle_count()
            bounds = mesh.get_bounding_box()
            bounds_str = f"({bounds.min.x:.4f},{bounds.min.y:.4f},{bounds.min.z:.4f})-({bounds.max.x:.4f},{bounds.max.y:.4f},{bounds.max.z:.4f})"
            fingerprint = (num_triangles, bounds_str)

            if fingerprint not in unique_meshes_map:
                unique_meshes_map[fingerprint] = []
            unique_meshes_map[fingerprint].append(mesh)
        except Exception as e:
            helper.log(f"Error analyzing {mesh.get_name()}: {e}")

    consolidation_map = {}
    for fingerprint, mesh_group in unique_meshes_map.items():
        master_mesh = mesh_group[0]
        duplicates = mesh_group[1:]
        consolidation_map[master_mesh] = duplicates

    helper.log(f"Consolidation map prepared with {len(consolidation_map)} master meshes.")
    return consolidation_map

def save_non_duplicate_geometries(consolidation_map, root_actor_label, destination_path, helper):
    helper.log("--- Saving Non-Duplicate Geometry Assets with Materials ---")

    master_meshes = list(consolidation_map.keys())
    saved_geometry_count = 0
    saved_material_count = 0
    replaced_material_count = 0

    # Define the target folder for material instances
    target_material_folder = f"{destination_path}/Materials"
    # Define the references folder for parent materials
    references_folder = f"{target_material_folder}/References"

    # Ensure the material folders exist
    if not unreal.EditorAssetLibrary.does_directory_exist(target_material_folder):
        unreal.EditorAssetLibrary.make_directory(target_material_folder)
        helper.log(f"Created material folder: {target_material_folder}")

    if not unreal.EditorAssetLibrary.does_directory_exist(references_folder):
        unreal.EditorAssetLibrary.make_directory(references_folder)
        helper.log(f"Created references folder: {references_folder}")

    for master_mesh in master_meshes:
        asset_path = master_mesh.get_path_name()
        num_materials = master_mesh.get_num_sections(0)

        for mat_index in range(num_materials):
            material = master_mesh.get_material(mat_index)

            if material:
                material_name = material.get_name()
                material_path = material.get_path_name()

                # Handle material instances
                if isinstance(material, unreal.MaterialInstance):
                    target_material_path = f"{target_material_folder}/{material_name}"

                    if material_path.startswith(target_material_folder) and not material_path.startswith(references_folder):
                        continue

                    existing_material = unreal.EditorAssetLibrary.find_asset_data(target_material_path)

                    if existing_material.is_valid():
                        existing_material_asset = existing_material.get_asset()
                        master_mesh.set_material(mat_index, existing_material_asset)
                        replaced_material_count += 1
                    else:
                        try:
                            parent_material = material.parent

                            if parent_material:
                                parent_name = parent_material.get_name()
                                parent_target_path = f"{references_folder}/{parent_name}"

                                parent_asset_data = unreal.EditorAssetLibrary.find_asset_data(parent_target_path)

                                if not parent_asset_data.is_valid():
                                    parent_duplicate = unreal.EditorAssetLibrary.duplicate_asset(
                                        parent_material.get_path_name(),
                                        parent_target_path
                                    )
                                    if parent_duplicate:
                                        saved_material_count += 1
                                else:
                                    parent_duplicate = parent_asset_data.get_asset()

                                new_material_instance = unreal.EditorAssetLibrary.duplicate_asset(
                                    material_path,
                                    target_material_path
                                )

                                if new_material_instance:
                                    new_material_instance.set_editor_property('parent', parent_duplicate)
                                    master_mesh.set_material(mat_index, new_material_instance)
                                    saved_material_count += 1

                        except Exception as e:
                            helper.log(f"Failed to save material instance {material_name}: {str(e)}")
                else:
                    # Regular material
                    target_material_path = f"{references_folder}/{material_name}"

                    if material_path.startswith(references_folder):
                        continue

                    existing_material = unreal.EditorAssetLibrary.find_asset_data(target_material_path)

                    if existing_material.is_valid():
                        existing_material_asset = existing_material.get_asset()
                        master_mesh.set_material(mat_index, existing_material_asset)
                        replaced_material_count += 1
                    else:
                        try:
                            new_material = unreal.EditorAssetLibrary.duplicate_asset(
                                material_path,
                                target_material_path
                            )

                            if new_material:
                                master_mesh.set_material(mat_index, new_material)
                                saved_material_count += 1

                        except Exception as e:
                            helper.log(f"Failed to save material {material_name}: {str(e)}")

        # Save the geometry asset
        if unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False):
            saved_geometry_count += 1
        else:
            helper.log(f"Failed to save geometry: {asset_path}")

    unreal.EditorAssetLibrary.save_directory(target_material_folder)
    unreal.EditorAssetLibrary.save_directory(references_folder)

    helper.log(f"--- Finished: Saved {saved_geometry_count} geometries, {saved_material_count} new materials, replaced {replaced_material_count} materials. ---")

def change_actor_meshes_to_master(consolidation_map, actors_to_process, root_actor_label, destination_path, helper):
    helper.log("--- Starting to change Static Mesh assignments on Actors ---")

    duplicate_to_master_map = {
        dup.get_path_name(): master for master, dups in consolidation_map.items() for dup in dups
    }
    
    helper.log(f"Found {len(duplicate_to_master_map)} duplicate meshes to consolidate.")
    if not duplicate_to_master_map:
        return

    static_mesh_editor_subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    actors_changed_count = 0

    master_meshes = set(consolidation_map.keys())
    index = 0
    
    for master_mesh in master_meshes:
        bounds = master_mesh.get_bounding_box()
        size_x = bounds.max.x - bounds.min.x
        size_y = bounds.max.y - bounds.min.y
        size_z = bounds.max.z - bounds.min.z

        index += 1
        
        if size_x < 11 or size_y < 11 or size_z < 11:
            unreal.EditorAssetLibrary.save_asset(master_mesh.get_path_name(), only_if_is_dirty=False)
            continue

        if has_translucent_or_masked_material(master_mesh):
            unreal.EditorAssetLibrary.save_asset(master_mesh.get_path_name(), only_if_is_dirty=False)
            continue

        nanite_settings = static_mesh_editor_subsystem.get_nanite_settings(master_mesh)
        if not nanite_settings.enabled:
            nanite_settings.enabled = True
            static_mesh_editor_subsystem.set_nanite_settings(master_mesh, nanite_settings, True)
            unreal.EditorAssetLibrary.save_asset(master_mesh.get_path_name(), only_if_is_dirty=False)
        
    with unreal.ScopedEditorTransaction("Consolidate Actor Meshes") as transaction:
        for actor in actors_to_process:
            smc = actor.static_mesh_component

            if smc and smc.static_mesh:
                current_mesh_path = smc.static_mesh.get_path_name()

                if current_mesh_path in duplicate_to_master_map:
                    master_mesh = duplicate_to_master_map[current_mesh_path]
                    smc.set_static_mesh(master_mesh)
                    actors_changed_count += 1

    save_the_levels(f"{destination_path}/{root_actor_label}", helper)
    helper.log(f"--- Finished: Changed mesh assignment on {actors_changed_count} actors. ---")

def remove_cameras_from_scene(helper):
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in actors:
        if isinstance(actor, unreal.CameraActor) or isinstance(actor, unreal.CineCameraActor):
            unreal.EditorLevelLibrary.destroy_actor(actor)
            helper.log(f"Removed camera: {actor.get_name()}")

def get_imported_actors(root_name, helper):
    all_actors = unreal.EditorLevelLibrary.get_all_level_actors()
    root_actor = next((actor for actor in all_actors if actor.get_actor_label() == root_name), None)
    
    if not root_actor:
        helper.log(f"Could not find imported root actor '{root_name}' in the level.")
        return None, []

    def collect_descendants(actor):
        collected = []
        for child in actor.get_attached_actors():
            if isinstance(child, unreal.StaticMeshActor):
                collected.append(child)
            collected.extend(collect_descendants(child))
        return collected

    return root_actor, collect_descendants(root_actor)

def import_datasmith(file_path, destination_path, helper):
    # Note: Logic imported from updatedHoly.py does NOT save automatically here
    # to allow for mesh deduplication before saving.
    task = unreal.AssetImportTask()
    task.filename = file_path
    task.destination_path = destination_path
    task.factory = unreal.DatasmithImportFactory()
    task.automated = True
    task.replace_existing = True
    # task.save = True # Disabled to allow deduplication first
    
    # Import the asset
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    
    helper.log(f"Imported '{os.path.basename(file_path)}' to {destination_path}")