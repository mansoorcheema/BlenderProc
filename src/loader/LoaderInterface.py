import bpy
import numpy as np

from src.main.Module import Module
from src.utility.BlenderUtility import get_bounds


class LoaderInterface(Module):
    """
    **Configuration**:

    .. list-table:: 
        :widths: 25 100 10
        :header-rows: 1

        * - Parameter
          - Description
          - Type
        * - add_properties
          - Custom properties to set for loaded objects. Use `cp_` prefix for keys.
          - dict
        * - cf_set_shading
          - Custom function to set the shading of the loaded objects. Available: ["FLAT", "SMOOTH"]
          - string
        * - cf_apply_transformation
          - Loaded objects, sometimes contain transformations, these can be applied to the mesh, so that setting a
            new location, has the expected behavior. Else the prior location, will be replaced. Default: False.
          - bool
        * - cf_set_obj_material
          - Change the material of the object
          - string
        
    """

    def __init__(self, config):
        Module.__init__(self, config)

    def _set_properties(self, objects: [bpy.types.ID]):
        """ Sets all custom properties of all given resources according to the configuration.

        Also runs all custom property functions.

        Note: Some datablock types like bpy.types.Light, bpy.types.Mesh, bpy.types.Camera etc
        are wrapped in bby.types.Object which act as a container of these object. In that case
        setting the properties of the container object does not set the properties of underlying datablock like
        camera and vice versa. Setting the bpy.data.objects["Light"] and bpy.data.lights["Light"] is different and each
        has its own properties. This function sets properties of all types materials, lights,
        cameras even if they are loaded as an object.

        :param objects: A list of objects which should receive the custom properties. Type: [bpy.types.ID]
        """

        properties = self.config.get_raw_dict("add_properties", {})

        for obj in objects:
            for key, value in properties.items():
                if key.startswith("cp_"):
                    key = key[3:]
                    obj[key] = value
                else:
                    raise RuntimeError(
                        "Loader modules support setting only custom properties. Use 'cp_' prefix for keys. "
                        "Use manipulators.Entity for setting object's attribute values.")
            
            # only meshes have polygons/faces 
            if hasattr(obj, 'type') and obj.type == 'MESH':
                if self.config.has_param("cf_set_shading"):
                    mode = self.config.get_string("cf_set_shading")
                    LoaderInterface.change_shading_mode([obj], mode)

                if self.config.has_param("cf_set_obj_material"):
                    material_name = self.config.get_string("cf_set_obj_material")
                    LoaderInterface.change_material([obj], material_name)

            # only bpy.types.Object (subclass of bpy.types.ID) have transformation 
            if isinstance(obj, bpy.types.Object): 
                apply_transformation = self.config.get_bool("cf_apply_transformation", False)
                if apply_transformation:
                    LoaderInterface.apply_transformation_to_objects([obj])

    @staticmethod
    def apply_transformation_to_objects(objects: [bpy.types.Object]):
        """
        Apply the current transformation of the object, which are saved in the location, scale or rotation attributes
        to the mesh and sets them to their init values.

        :param objects: List of objects, which should be changed
        """
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            obj.select_set(False)
        bpy.ops.object.select_all(action='DESELECT')

    @staticmethod
    def change_shading_mode(objects: [bpy.types.Object], mode: str):
        """
        Changes the shading mode of all objects to either flat or smooth. All surfaces of that object are changed.

        :param objects: A list of objects which should receive the custom properties. Type: [bpy.types.Object]
        :param mode: Desired mode of the shading. Available: ["FLAT", "SMOOTH"]. Type: str
        """
        if mode.lower() == "flat":
            is_smooth = False
        elif mode.lower() == "smooth":
            is_smooth = True
        else:
            raise Exception("This shading mode is unknown: {}".format(mode))

        for obj in objects:
            for face in obj.data.polygons:
                face.use_smooth = is_smooth

    @staticmethod
    def change_material(objects: [bpy.types.Object], material_name: str):
        """
        Changes the material of target objects. The material should have previously been
        loaded.

        :param objects: A list of objects which to apply the material. Type: [bpy.types.Object]
        :param material_name: Name of the material to apply to the objects. Type: str
        """

        if material_name not in bpy.data.materials:
            raise Exception("Material {} is not Loaded. Please load the material first".format(material_name))

        material = bpy.data.materials[material_name]
        
        for obj in objects:
            obj.active_material = material

    @staticmethod
    def remove_x_axis_rotation(objects: [bpy.types.Object]):
        """
        Removes the 90 degree X-axis rotation found, when loading from `.obj` files. This function rotates the mesh
        itself not just the object, this will set the `rotation_euler` to `[0, 0, 0]`.

        :param objects: list of objects, which mesh should be rotated
        """

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            # convert object rotation into internal rotation
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            obj.rotation_euler = [0, 0, 0]
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.transform.rotate(value=np.pi * 0.5, orient_axis="X")
            bpy.ops.object.mode_set(mode='OBJECT')
            obj.select_set(False)
        bpy.context.view_layer.update()

    @staticmethod
    def move_obj_origin_to_bottom_mean_point(objects: [bpy.types.Object]):
        """
        Moves the object center to bottom of the bounding box in Z direction and also in the middle of the X and Y
        plane. So that all objects have a similar origin, which then makes the placement easier.

        :param objects: list of objects, which origin should be moved
        """

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            # move the object to the center
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bb = get_bounds(obj)
            bb_center = np.mean(bb, axis=0)
            bb_min_z_value = np.min(bb, axis=0)[2]
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.transform.translate(value=[-bb_center[0], -bb_center[1], -bb_min_z_value])
            bpy.ops.object.mode_set(mode='OBJECT')
            obj.select_set(False)
        bpy.context.view_layer.update()
