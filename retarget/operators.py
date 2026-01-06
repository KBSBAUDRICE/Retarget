from math import pi, ceil, floor

import bpy
from bpy.props import BoolProperty
from bpy.props import EnumProperty
from bpy.props import FloatProperty
from bpy.props import IntProperty
from bpy.props import StringProperty
from bpy.props import FloatVectorProperty
from bpy.types import Operator
from bpy_extras import anim_utils

from itertools import chain

from .rig_mapping import bone_mapping
from . import preset_handler
from . import bone_utils

from mathutils import Vector
from mathutils import Matrix


CONSTR_STATUS = (
    ('enable', "Enable", "Enable All Constraints"),
    ('apply', "Apply", "Apply All Constraints"),
    ('disable', "Disable", "Disable All Constraints"),
    ('remove', "Remove", "Remove All Constraints")
)


CONSTR_TYPES = bpy.types.PoseBoneConstraints.bl_rna.functions['new'].parameters['type'].enum_items.keys()
CONSTR_TYPES.append('ALL_TYPES')


class ConstraintStatus(Operator):
    """Apply/Disable/Remove bone constraints."""
    bl_idname = "object.retarget_set_constraints_status"
    bl_label = "Apply/Disable/Remove Constraints"
    bl_options = {'REGISTER', 'UNDO'}

    set_status: EnumProperty(items=CONSTR_STATUS,
                             name="Status",
                             default='enable')
    custom_Frame: IntProperty(name="Frame", description="Select the Frame To Apply ", default=1)

    selected_only: BoolProperty(name="Only Selected",
                                default=False)
    
    constr_type: EnumProperty(items=[(ct, ct.replace('_', ' ').title(), ct) for ct in CONSTR_TYPES],
                              name="Constraint Type",
                              default='ALL_TYPES')

    def draw(self, context):

        layout = self.layout
        column = layout.column()

        row = column.row()
        row.prop(self, 'set_status', text = "Status")

        if self.set_status == 'apply':
            row = column.row()
            row.prop(self, "custom_Frame", text="Frame")
    
        row = column.row()
        row.prop(self, 'selected_only', text = "Only Selected")

        row = column.row()
        row.prop(self, 'constr_type', text = "Constraint Type")

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True
    
    def invoke(self, context, event):  
        #init the custom_Frame
        self.custom_Frame = context.scene.frame_current
        return self.execute(context) 


    def execute(self, context):

        current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')

        if self.set_status == 'apply':
            context.scene.frame_current = self.custom_Frame

        armatures = context.selected_objects
        for armature in armatures:

            if armature.type != 'ARMATURE':
                continue

            bones = context.selected_pose_bones if self.selected_only else armature.pose.bones
            if self.set_status == 'remove':
                for bone in bones:
                    for constr in reversed(bone.constraints):
                        if self.constr_type != 'ALL_TYPES' and constr.type != self.constr_type:
                            continue

                        bone.constraints.remove(constr)
            
            elif self.set_status == 'enable' or self.set_status == 'disable':
                for bone in bones:
                    for constr in bone.constraints:
                        if self.constr_type != 'ALL_TYPES' and constr.type != self.constr_type:
                            continue
                        constr.mute = self.set_status == 'disable'
            # apply Constraints
            else:
                for bone in bones:
                    armature.data.bones.active = bone.bone
                    bone.select = True
                    for constr in reversed(bone.constraints):
                        if self.constr_type != 'ALL_TYPES' and constr.type != self.constr_type:
                            continue
                        bpy.ops.constraint.apply(constraint = constr.name, owner = 'BONE')


        bpy.ops.object.mode_set(mode= current_m)
        return {'FINISHED'}


class SelectConstrainedControls(Operator):
    bl_idname = "armature.retarget_select_constrained_ctrls"
    bl_label = "Select constrained controls"
    bl_description = "Select bone controls with constraints or animations"
    bl_options = {'REGISTER', 'UNDO'}

    select_type: EnumProperty(items=[
        ('constr', "Constrained", "Select constrained controls"),
        ('anim', "Animated", "Select animated controls"),
    ],
        name="Select if",
        default='constr')
    
    skip_deform: BoolProperty(name="Skip Deform Bones",
                              description="Bones that deform the mesh",
                               default=False)
    has_shape: BoolProperty(name="Only Control Shapes", 
                            description="Bones that have a custom display",
                            default=False)

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):

        bpy.ops.object.mode_set(mode='POSE')

        armatures = context.selected_objects
        for ob in armatures:

            if ob.type != 'ARMATURE':
                continue

            bpy.ops.pose.select_all(action='DESELECT')

            if self.select_type == 'constr':
                for pb in bone_utils.get_constrained_controls(ob, unselect=True, use_deform=not self.skip_deform):
                    pb.select = bool(pb.custom_shape) if self.has_shape else True

            elif self.select_type == 'anim':
                if not ob.animation_data:
                    continue
                if not ob.animation_data.action:
                    continue
                
                for slot in ob.animation_data.action.slots:

                    if slot.target_id_type != 'OBJECT':
                        continue

                    if not ob in slot.users(): 
                        continue

                    channelbag = anim_utils.action_get_channelbag_for_slot(ob.animation_data.action, slot)
                  
                    for gp in channelbag.groups:

                        if gp.name in ob.pose.bones:

                            try:
                                bone = ob.pose.bones[gp.name]
                            except KeyError:
                                continue

                            if self.skip_deform and bone.bone.use_deform:
                                continue

                            bone.select = bool(bone.custom_shape) if self.has_shape else True

        return {'FINISHED'}

class AlignBone(Operator):
    bl_idname = "armature.retarget_transfert_bone"
    bl_label = "Align Bones"
    bl_description = "Align the rest positions, it does not affect the mesh (select at least 2 armatures) (apply the scale in case of problem) (extremity bones will cause some issue) IT WILL BREACK THE ACTIONS OF THIS ARMATURE"
    bl_options = {'REGISTER', 'UNDO'}

    same_bone_names: BoolProperty(name="Same Bone Names", 
                                 description="When two armatures have the same bones names (set these Armature to the same position)",
                                 default=False)
    
    bind_by_name: BoolProperty(name="Bind bones by name", 
                            description= "Look for bones present in both",
                            default=False)

    name_prefix: StringProperty(name="Add prefix to name", 
                                description= "Add prefix to source bone name",
                                default="")
    name_replace: StringProperty(name="Replace in name", 
                                  description= "Replace in source bone name",
                                 default="")
    name_replace_with: StringProperty(name="Replace in name with", 
                                       description= "Replace with",
                                      default="")
    name_suffix: StringProperty(name="Add suffix to name", 
                                 description= "Add suffix to source bone name",
                                default="")
    
    src_preset: EnumProperty(items=preset_handler.iterate_presets_with_current,
                             description="Other Armature",
                             name="Source Preset",
                             )

    trg_preset: EnumProperty(items=preset_handler.iterate_presets,
                             description="Active Armature",
                             name="Target Preset",
                             )
    
    only_rotate: BoolProperty(name="Only Rotation", 
                              description="Align only the Rotation",
                              default=False)
    
    Preserve_Height: BoolProperty(name="Preserve Height", 
                                  description="Preserve The Height Of The Armature",
                              default=True)
    head_bone: StringProperty(name = "Head Bone",
                              default="")
    
    Preserve_Width: BoolProperty(name="Preserve Width", 
                                  description="Preserve The Width Of The Armature",
                              default=False)
    
    Preserve_Depth: BoolProperty(name="Preserve Depth", 
                                  description="Preserve The Depth Of The Armature",
                              default=False)
    
    align: BoolProperty(name="Align Bones", default=True)

    def draw(self, context):

        layout = self.layout
        column = layout.column()

        row = column.split(factor=0.10, align=True)
        row.label(text="")
        row.prop(self, 'same_bone_names')

        if not self.same_bone_names:

            row = column.split(factor=0.10, align=True)
            row.label(text="")
            row.prop(self, 'src_preset', text="To Bind")
        
            row = column.split(factor=0.10, align=True)
            row.label(text="")
            row.prop(self, 'trg_preset', text="Bind To")


        else:
            row = column.split(factor=0.10, align=True)
            row.label(text="")
            row.prop(self, 'bind_by_name', text="Also by Name")
            if self.bind_by_name:
                row = column.row()
                col = row.column()
                col.label(text="Prefix")
                col.prop(self, 'name_prefix', text="")

                col = row.column()
                col.label(text="Replace:")
                col.prop(self, 'name_replace', text="")

                col = row.column()
                col.label(text="With:")
                col.prop(self, 'name_replace_with', text="")

                col = row.column()
                col.label(text="Suffix:")
                col.prop(self, 'name_suffix', text="")

            row = column.row()
            row.label(text = "")

        
        row = column.split(factor=0.10, align=True)
        row.label(text="")
        row.prop(self, 'only_rotate')

        row = column.split(factor=0.10, align=True)
        row.label(text="")
        row.prop(self, 'Preserve_Height')

        if self.same_bone_names and self.Preserve_Height:
            sr_ob = None
            for ob in context.selected_objects:
                if ob != context.active_object:
                    sr_ob = ob
                    break
            if sr_ob:
                row = column.split(factor=0.10, align=True)
                row.label(text="")
                row.prop_search(self, 'head_bone',
                            sr_ob.data,
                            "bones", text="Head Bone")


        row = column.split(factor=0.10, align=True)
        row.label(text="")
        row.prop(self, 'Preserve_Width')

       
        row = column.split(factor=0.10, align=True)
        row.label(text="")
        row.prop(self, 'Preserve_Depth')

        row = column.split(factor=0.10, align=True)
        row.label(text="")
        row.prop(self, 'align', toggle = True)

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.object.type != 'ARMATURE':
            return False
        if len(context.selected_objects) < 2:
            return False
        
        #At least 2 Armatures
        i = 0
        for ob in context.selected_objects:
            if ob.type == 'ARMATURE':
                i = i + 1
            if i >= 2:
                return True
        
        return False
        
    @staticmethod
    def convert_presets(src_settings, target_settings):
        src_skeleton = preset_handler.get_preset_skel(src_settings)
        trg_skeleton = preset_handler.get_preset_skel(target_settings)

        return src_skeleton, trg_skeleton

    @staticmethod
    def convert_settings(current_settings, target_settings, context, validate=True):
        src_settings = preset_handler.PresetSkeleton()
        src_settings.copy(current_settings)

        src_skeleton = preset_handler.get_settings_skel(src_settings)
        trg_skeleton = preset_handler.set_preset_skel(target_settings, context, validate)

        return src_skeleton, trg_skeleton
    
    def execute(self, context):
        current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')

        # action to range
        if context.active_object.animation_data and context.active_object.animation_data.action:
            bpy.ops.object.retarget_action_to_range()

        trg_ob = context.active_object
        tmp_ob = trg_ob
       
        if trg_ob.type != 'ARMATURE':
            bpy.ops.object.mode_set(mode=current_m)
            return {'FINISHED'}
    
        if not self.same_bone_names:
            if self.src_preset == "--Current--" and trg_ob.data.retarget_retarget.has_settings():
                trg_settings = trg_ob.data.retarget_retarget
                trg_skeleton = preset_handler.get_settings_skel(trg_settings)
            else:
                trg_skeleton = preset_handler.set_preset_skel(self.trg_preset,  context)
            
            if not trg_skeleton:
                bpy.ops.object.mode_set(mode=current_m)
                return {'FINISHED'}
        
        armatures = context.selected_objects
        for ob in armatures:
            if ob == trg_ob:
                continue

            if ob.type != 'ARMATURE':
                continue

            context.view_layer.objects.active = ob
            bpy.ops.object.mode_set(mode='POSE')

            bone_names_map = dict()

            if not self.same_bone_names:

                src_settings = ob.data.retarget_retarget
                if self.src_preset == '--Current--' and ob.data.retarget_retarget.has_settings():    
                    if not src_settings.has_settings():
                        continue
                    src_skeleton = preset_handler.get_settings_skel(src_settings)
                else:
                    src_skeleton = preset_handler.get_preset_skel(self.src_preset, src_settings)
                
                if not src_skeleton:
                    continue

                root_prefix = ""
                for bone in ob.pose.bones:
                    if ":" in bone.name and ":" not in src_skeleton.root:
                        root_prefix = bone.name.split(":")[0] + ":"
                    break
                # root prefix
                src_skeleton.root = root_prefix + src_skeleton.root

                bone_names_map = src_skeleton.conversion_map(trg_skeleton)
            
            else:
               
                for bone in ob.pose.bones:

                    try:
                        pb = trg_ob.pose.bones[bone.name]
                    except KeyError:
                        continue

                    bone_names_map[bone.name] = bone.name

                if self.bind_by_name:
                    # Look for bones present in both
                    for bone in ob.pose.bones:
                        bone_name = bone.name
                        bone_look_up = self.name_prefix + bone_name.replace(self.name_replace, self.name_replace_with) + self.name_suffix
                        
                        if bone_look_up in bone_names_map:
                            continue
                        if bone_utils.is_pose_bone_all_locked(bone):
                            continue
                        if bone_look_up in trg_ob.pose.bones:
                            bone_names_map[bone_name] = bone_look_up

                
            if self.Preserve_Height:
                try:
                   
                    bpy.ops.object.mode_set(mode='OBJECT')

                    # duplic Oject
                    bpy.ops.object.select_all(action='DESELECT')
                    bpy.ops.object.select_pattern( pattern=trg_ob.name, case_sensitive=True, extend=False)
                    #prevent the duplication of action
                    if ob.animation_data and ob.animation_data.action:
                        action = ob.animation_data.action
                        ob.animation_data.action = None

                    bpy.ops.object.duplicate()

                    if ob.animation_data and ob.animation_data.action:
                        ob.animation_data.action = action

                    tmp_ob = context.selected_objects[0]

                    if self.same_bone_names:
                        if self.head_bone:
                            trg_bone = tmp_ob.pose.bones[self.head_bone]
                        else:
                            break
                    else:
                        trg_bone = tmp_ob.pose.bones[getattr(trg_skeleton.spine, 'head')]

                    trg_height = (tmp_ob.matrix_world @ trg_bone.bone.head_local)

                    if self.same_bone_names:
                        if self.head_bone:
                            ob_height = (ob.matrix_world @ ob.pose.bones[self.head_bone].bone.head_local)
                        else:
                            break
                    else:
                        ob_height = (ob.matrix_world @ ob.pose.bones[getattr(src_skeleton.spine, 'head')].bone.head_local)

                    height_ratio = ob_height[2] / trg_height[2]
                    
                    tmp_ob.scale *= height_ratio
                    # Apply scale
                    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

                    for armature in armatures:
                        bpy.ops.object.select_pattern( pattern=armature.name, case_sensitive=True, extend=True)
                    context.view_layer.objects.active = ob
                except KeyError:
                    pass

            bpy.ops.object.mode_set(mode='EDIT')
            
            if self.align:
                for src_name, trg_name in bone_names_map.items():
                    
                    if not src_name:
                        continue
                    try:
                        sr_bone = ob.data.edit_bones[src_name]

                        if self.Preserve_Height:
                            tj_bone = tmp_ob.data.edit_bones[trg_name]
                        else:
                            tj_bone = trg_ob.data.edit_bones[trg_name]

                        matrix = tj_bone.matrix.copy()

                        if self.Preserve_Width:
                            matrix_sr = sr_bone.matrix

                            matrix[0][0] = matrix_sr[0][0]
                            matrix[0][1] = matrix_sr[0][1]
                            matrix[0][2] = matrix_sr[0][2]
                            matrix[0][3] = matrix_sr[0][3]

                        if self.Preserve_Depth:
                            matrix_sr = sr_bone.matrix

                            matrix[1][0] = matrix_sr[1][0]
                            matrix[1][1] = matrix_sr[1][1]
                            matrix[1][2] = matrix_sr[1][2]
                            matrix[1][3] = matrix_sr[1][3]

                        if self.only_rotate:
                            matrix_sr = sr_bone.matrix
                            #LOCATIiON
                            matrix[0][3] = matrix_sr[0][3]
                            matrix[1][3] = matrix_sr[1][3]
                            matrix[2][3] = matrix_sr[2][3]
                            matrix[3][3] = matrix_sr[3][3]

                        else:
                            sr_bone.head = tj_bone.head
                            sr_bone.tail = tj_bone.tail

                        sr_bone.matrix = matrix
                        sr_bone.roll = tj_bone.roll
                        
                    except KeyError:
                        continue
            #delete the tmp
        if self.Preserve_Height and tmp_ob != trg_ob:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.select_pattern( pattern=tmp_ob.name, case_sensitive=True, extend=False)
            bpy.ops.object.delete(use_global=False)
            for armature in armatures:
                bpy.ops.object.select_pattern( pattern=armature.name, case_sensitive=True, extend=True)

            context.view_layer.objects.active = trg_ob


        context.view_layer.objects.active = trg_ob
        bpy.ops.object.mode_set(mode=current_m)
        return {'FINISHED'}


class AdjustAnimation(Operator):
    bl_idname = "armature.retarget_adjust_animation"
    bl_label = "Adjust Animation"
    bl_options = {'REGISTER', 'UNDO'}

#Ajust
    adjust_animation: BoolProperty(name="Adjust Animation", 
                               description="Create a Armature that will be used for the Adjustment, ( you'll need to bake to save the change)",
                               default=False)
    
    only_animated_Bone: BoolProperty(name="Only Animated Bone", 
                               description="Add Constrain Only on Animated Bone (Recommended)",
                               default=True)
    
    bind_floating: BoolProperty(name="Bind Floating",
                                description="Always bind unparented bones Location and Rotation",
                                default=True)
    
    detect_ik_bones:  BoolProperty(name="Detect All Ik Bone",  
                                   description="(Bone that the name contain 'ik')",
                                   default=False)
    
    ik_bones:  StringProperty(name = "IK Bones", 
                              description="IK Bones List",
                              default="", options = {'SKIP_SAVE'})
    
    clean_all:  BoolProperty(name="",  
                              description="Delete All",
                             default=False, options = {'SKIP_SAVE'})
    
    clean_last:  BoolProperty(name="",  
                              description="Delete the last one",
                              default=False, options = {'SKIP_SAVE'})
    
    ik_collection = []
    

    root_motion_a: StringProperty(name = "Root", default="")

    root_cp_loc_x: BoolProperty(name="Root Copy Loc X", description="Copy Root X Location", default=True)
    root_cp_loc_y: BoolProperty(name="Root Copy Loc y", description="Copy Root Y Location", default=True)
    root_cp_loc_z: BoolProperty(name="Root Copy Loc Z", description="Copy Root Z Location", default=True)

    root_use_loc_min_x: BoolProperty(name="Use Root Min X", description="Use Minimum Root X Location", default=False)
    root_use_loc_min_y: BoolProperty(name="Use Root Min Y", description="Use Minimum Root Y Location", default=False)
    root_use_loc_min_z: BoolProperty(name="Use Root Min Z", description="Use Minimum Root Z Location", default=False)

    root_loc_min_x: FloatProperty(name="Root Min X", description="Minimum Root X Location", default=0.0)
    root_loc_min_y: FloatProperty(name="Root Min Y", description="Minimum Root Y Location", default=0.0)
    root_loc_min_z: FloatProperty(name="Root Min Z", description="Minimum Root Z Location", default=0.0)

    root_use_loc_max_x: BoolProperty(name="Use Root Max X", description="Use Maximum Root X Location", default=False)
    root_use_loc_max_y: BoolProperty(name="Use Root Max Y", description="Use Maximum Root Y Location", default=False)
    root_use_loc_max_z: BoolProperty(name="Use Root Max Z", description="Use Maximum Root Z Location", default=False)

    root_loc_max_x: FloatProperty(name="Root Max X", description="Maximum Root X Location", default=0.0)
    root_loc_max_y: FloatProperty(name="Root Max Y", description="Maximum Root Y Location", default=0.0)
    root_loc_max_z: FloatProperty(name="Root Max Z", description="Maximum Root Z Location", default=0.0)

    root_cp_rot_x: BoolProperty(name="Root Copy Rot X", description="Copy Root X Rotation", default=False)
    root_cp_rot_y: BoolProperty(name="Root Copy Rot y", description="Copy Root Y Rotation", default=False)
    root_cp_rot_z: BoolProperty(name="Root Copy Rot Z", description="Copy Root Z Rotation", default=False)

    root_cp_scal_x: BoolProperty(name="Root Copy Scal X", description="Copy Root X Scale", default=False)
    root_cp_scal_y: BoolProperty(name="Root Copy Scal y", description="Copy Root Y Scale", default=False)
    root_cp_scal_z: BoolProperty(name="Root Copy Scal Z", description="Copy Root Z Scale", default=False)


    root_cp_rot_x: BoolProperty(name="Root Copy Rot X", description="Copy Root X Rotation", default=False)
    root_cp_rot_y: BoolProperty(name="Root Copy Rot y", description="Copy Root Y Rotation", default=False)
    root_cp_rot_z: BoolProperty(name="Root Copy Rot Z", description="Copy Root Z Rotation", default=False)

    root_cp_scal_x: BoolProperty(name="Root Copy Scal X", description="Copy Root X Scale", default=False)
    root_cp_scal_y: BoolProperty(name="Root Copy Scal y", description="Copy Root Y Scale", default=False)
    root_cp_scal_z: BoolProperty(name="Root Copy Scal Z", description="Copy Root Z Scale", default=False)
                   
    
    ret_bones_collection: StringProperty(name="Layer",
                                             default="Retarget Bones",
                                             description="Armature collection to use for connection bones (Usefull to ADD modification to the Animation)")
    
    apply:BoolProperty(name="APPLY",  description="APPLY", default=False , options = {'SKIP_SAVE'})
#-------------------------------------------------------------------------
    speed: FloatProperty(name="Speed", default=1)
    
    repeat: FloatProperty(name="Repeat", default=1)
    
# in place ------------------------
    in_place: BoolProperty(name="In Place", 
                           description="the animation don't move",
                           default=False)
    
    root_motion: StringProperty(name = "Root Motion", default="")

    position_x: BoolProperty(name="X", 
                               description="Delete the Position X",
                               default=True)
    
    position_y: BoolProperty(name="Y", 
                               description="Delete the Position Y",
                               default=True)
    
    position_z: BoolProperty(name="Z", 
                               description="Delete the Position Z",
                               default=True)
    
    rotation_x: BoolProperty(name="X", 
                               description="Delete the Rotation X",
                               default=False)
    
    rotation_y: BoolProperty(name="Y", 
                               description="Delete the Rotation Y",
                               default=False)
    
    rotation_z: BoolProperty(name="Z", 
                               description="Delete the Rotation Z",
                               default=False)
    
    scale_freeze: BoolProperty(name="Delete the scale", 
                               description="Delete the Scale",
                               default=False)


    all_slots:BoolProperty(name="All Slots", 
                               description="Apply these effects in all slots",
                               default=False)


    action_range: BoolProperty(name= "Action Range to Scene", 
                               description="Set Playback range to current action Start/End",
                               default=True)
    
    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.split(factor=0.050, align=True)
        row.label(text="")
        row.prop(self, "adjust_animation")

        if self.adjust_animation:

            row = column.split(factor=0.20, align=True)
            row.label(text="")
            row.prop(self, 'bind_floating')

            row = column.split(factor=0.20, align=True)
            row.label(text="")
            row.prop(self, 'only_animated_Bone')

            row = column.split(factor=0.20, align=True)
            row.label(text="")
            row.prop(self, 'detect_ik_bones')

            #ik bone collection
            row = column.row()
            row.label(text="")

            row = column.split(factor=0.80, align=True)
            row.prop_search(self, 'ik_bones',
                        context.active_object.data,
                        "bones")
            row.prop(self, 'clean_all', toggle=True, icon='PANEL_CLOSE')
            row.prop(self, 'clean_last',toggle=True, icon='TRACKING_CLEAR_BACKWARDS')

            i = 0
            row = column.split(factor=0.25, align=True)

            for ik in self.ik_collection:
                if i == 3:
                    row = column.split(factor=0.25, align=True)
                    i = 0
                
                row.label(text=ik, icon='BONE_DATA')

                i += 1

            row = column.row()
            row.label(text="")


            row = column.split(factor=0.20, align=True)
            row.label(text="")
            row.prop_search(self, 'root_motion_a',
                            context.active_object.data,
                            "bones")
            
            if self.root_motion_a:
                row = column.row(align=True)
                row.label(text="Location")
                row.prop(self, "root_cp_loc_x", text="X", toggle=True)
                row.prop(self, "root_cp_loc_y", text="Y", toggle=True)
                row.prop(self, "root_cp_loc_z", text="Z", toggle=True)

                if any((self.root_cp_loc_x, self.root_cp_loc_y, self.root_cp_loc_z)):
                    column.separator()

                    # Min/Max X
                    if self.root_cp_loc_x:
                        row = column.row(align=True)
                        row.prop(self, "root_use_loc_min_x", text="Min X")

                        subcol = row.column()
                        subcol.prop(self, "root_loc_min_x", text="")
                        subcol.enabled = self.root_use_loc_min_x

                        row.separator()
                        row.prop(self, "root_use_loc_max_x", text="Max X")
                        subcol = row.column()
                        subcol.prop(self, "root_loc_max_x", text="")
                        subcol.enabled = self.root_use_loc_max_x
                        row.enabled = self.root_cp_loc_x

                    # Min/Max Y
                    if self.root_cp_loc_y:
                        row = column.row(align=True)
                        row.prop(self, "root_use_loc_min_y", text="Min Y")

                        subcol = row.column()
                        subcol.prop(self, "root_loc_min_y", text="")
                        subcol.enabled = self.root_use_loc_min_y

                        row.separator()
                        row.prop(self, "root_use_loc_max_y", text="Max Y")
                        subcol = row.column()
                        subcol.prop(self, "root_loc_max_y", text="")
                        subcol.enabled = self.root_use_loc_max_y
                        row.enabled = self.root_cp_loc_y

                    # Min/Max Z
                    if self.root_cp_loc_z:
                        row = column.row(align=True)
                        row.prop(self, "root_use_loc_min_z", text="Min Z")

                        subcol = row.column()
                        subcol.prop(self, "root_loc_min_z", text="")
                        subcol.enabled = self.root_use_loc_min_z

                        row.separator()
                        row.prop(self, "root_use_loc_max_z", text="Max Z")
                        subcol = row.column()
                        subcol.prop(self, "root_loc_max_z", text="")
                        subcol.enabled = self.root_use_loc_max_z
                        row.enabled = self.root_cp_loc_z

                    column.separator()

                row = column.row(align=True)
                row.label(text="Rotation")
                row.prop(self, "root_cp_rot_x", text="X", toggle=True)
                row.prop(self, "root_cp_rot_y", text="Y", toggle=True)
                row.prop(self, "root_cp_rot_z", text="Z", toggle=True)

                row = column.row(align=True)
                row.label(text="Scale")
                row.prop(self, "root_cp_scal_x", text="X", toggle=True)
                row.prop(self, "root_cp_scal_y", text="Y", toggle=True)
                row.prop(self, "root_cp_scal_z", text="Z", toggle=True)

                row = column.row()
                row.label(text="")

            row = column.split(factor=0.20, align=True)
            row.label(text="")
            row.prop(self, "ret_bones_collection")

            row = column.row(align=True)
            row.prop(self, "apply",  toggle=True)

        row = column.split(factor=0.05, align=True)
        row.label(text="")
        row.prop(self, "speed")

        row = column.split(factor=0.05, align=True)
        row.label(text="")
        row.prop(self, "repeat")

        row = column.split(factor=0.05, align=True)
        row.label(text="")
        row.prop(self, "in_place")

        if self.in_place and context.active_object.type == 'ARMATURE':
            row = column.split(factor=0.20, align=True)
            row.label(text="Root Motion")
            row.prop_search(self, 'root_motion',
                        context.active_object.data,
                        "bones", text="")
            
            row = column.row(align=True)
            row.label(text="Location")
            row.prop(self, "position_x", toggle=True)
            row.prop(self, "position_y", toggle=True)
            row.prop(self, "position_z", toggle=True)

            row = column.row(align=True)
            row.label(text="Rotation")
            row.prop(self, "rotation_x", text="X", toggle=True)
            row.prop(self, "rotation_y", text="Y", toggle=True)
            row.prop(self, "rotation_z", text="Z", toggle=True)

            row = column.split(factor=0.20, align=True)
            row.label(text="Scale")
            row.prop(self, "scale_freeze", text="Delete the Scale", toggle=True)
            
        row = column.split(factor=0.05, align=True)
        row.label(text="")
        row.prop(self, "all_slots", toggle = True)

        row = column.split(factor=0.05, align=True)
        row.label(text="")
        row.prop(self, "action_range", toggle=True, icon='PREVIEW_RANGE')
    
    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if not context.active_object.animation_data:
            return False 
        if not context.active_object.animation_data.action:
            return False 
        return True
    
    def invoke(self, context, event):
        if self.root_motion and not self.root_motion in context.object.pose.bones:
            self.root_motion = ""
        if self.root_motion_a and not self.root_motion_a in context.object.pose.bones:
            self.root_motion_a = ""
        
        return self.execute(context)
    
    def execute(self, context):

        armatures = context.selected_objects
       
        current_m = context.mode

        #// update value ik bones
        if self.adjust_animation:

            if self.clean_all:
                if len(self.ik_collection) > 0 :
                    self.ik_collection.clear()
                self.clean_all = False
                
            if self.clean_last:
                if len(self.ik_collection) > 0 :
                    self.ik_collection.pop()
                self.clean_last = False

            if self.ik_bones:
                if not self.ik_bones in self.ik_collection:
                    self.ik_collection.append(self.ik_bones)
                self.ik_bones = ""
        
        for ob in armatures:

            if not ob.animation_data:
                continue 
            if not ob.animation_data.action:
                continue
            
            context.view_layer.objects.active = ob

            #IN PLACE
            if ob.type == 'ARMATURE' and self.in_place and self.root_motion and self.root_motion in ob.pose.bones:
                
                action = ob.animation_data.action
                for slot in action.slots:
                     
                    if slot.target_id_type != 'OBJECT':
                        continue

                    #slot
                    if not self.all_slots:
                        if not ob in slot.users():
                            continue

                    channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                    
                    if self.root_motion in channelbag.groups:
                        group = channelbag.groups[self.root_motion]

                        pl = -1
                        pr = -1
                        del_fc = []
                        for fcurve in group.channels:
                            data_path = fcurve.data_path

                            if not self.root_motion in data_path:
                                continue
                            
                            if data_path.endswith('location'):
                                pl += 1

                                if pl == 0 and not self.position_x:
                                    continue
                                
                                if pl == 1 and not self.position_y:
                                    continue

                                if pl == 2 and not self.position_z:
                                    continue

                            if 'rotation' in data_path:
                                pr += 1

                                if data_path.endswith('rotation_quaternion'):

                                    if pr == 0 and (not self.rotation_x or not self.rotation_y or not self.rotation_z):
                                        continue

                                    if pr == 1 and not self.rotation_x:
                                        continue
                                    
                                    if pr == 2 and not self.rotation_y:
                                        continue

                                    if pr == 3 and not self.rotation_z:
                                        continue
                                else:
                                    if pr == 0 and not self.rotation_x:
                                        continue
                                    
                                    if pr == 1 and not self.rotation_y:
                                        continue

                                    if pr == 2 and not self.rotation_z:
                                        continue

                            if data_path.endswith('scale') and not self.scale_freeze:
                                continue
                            
                            del_fc.append(fcurve)
                            
                        for fc in del_fc:
                            channelbag.fcurves.remove(fc)
                    
                        bone = ob.pose.bones[self.root_motion]

                        bone.location[0] = 0
                        bone.location[1] = 0
                        bone.location[2] = 0
            
            #ajust_animation
            if self.apply and ob.type == 'ARMATURE' and self.adjust_animation:

                #Duplique object
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.select_all(action='DESELECT')
                bpy.ops.object.select_pattern( pattern=ob.name, case_sensitive=True, extend=False)
                action = ob.animation_data.action
                ob.animation_data.action = None
                bpy.ops.object.duplicate()
                new_ob = context.selected_objects[0]
                new_ob.animation_data.action = action

                #retargeting -----
                bpy.ops.object.mode_set(mode='POSE')
                bone_names_map = []

                channelbag = None
                for slot in action.slots:

                    if slot.target_id_type != 'OBJECT':
                        continue
                    if not  (new_ob in slot.users() ):
                        continue
                    channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                    break
                
                for bone in ob.pose.bones:

                    if self.only_animated_Bone and channelbag :
                        if channelbag and bone.name in channelbag.groups:
                            bone_names_map.append(bone.name)
                    
                    elif not bone_utils.is_pose_bone_all_locked(bone):
                        bone_names_map.append(bone.name)
                
                try:
                    ret_collection = new_ob.data.collections[self.ret_bones_collection]
                except KeyError:
                    ret_collection = new_ob.data.collections.new(self.ret_bones_collection)
                    ret_collection.is_visible = False

                # create Retarget bones collection
                cp_suffix = 'RET'
                prefix = ""

                bpy.ops.object.mode_set(mode='EDIT')
                for name in bone_names_map:
                    name = str(prefix) + str(name)
                    new_bone_name = bone_utils.copy_bone_to_arm(ob, new_ob, name, suffix=cp_suffix)

                    if not new_bone_name:
                        continue
                    try:
                        new_parent = new_ob.data.edit_bones[name]
                    except KeyError:
                        self.report({'WARNING'}, f"{name} not found in target")
                        continue

                    new_bone = new_ob.data.edit_bones[new_bone_name]
                    new_bone.parent = new_parent
                    new_bone.roll = new_ob.data.edit_bones[name].roll
                    #unassign the new bone to all collection
                    for coll in new_bone.collections:
                        coll.unassign(new_bone)
                    ret_collection.assign(new_bone)

                #-----
                bpy.ops.object.mode_set(mode='POSE')

                #add constrain / shape
                #find hips bone 
                hip_bone = None
                for bone in ob.pose.bones:
                    hip_bone = bone
                    break
                    
                for name in bone_names_map:
                    
                    try:
                        src_pbone = ob.pose.bones[name]
                        
                    except KeyError:
                        continue

                    constr_types = []
                    
                   
                    if name == self.root_motion_a or (self.detect_ik_bones and "ik" in name) or (name in self.ik_collection) or (self.bind_floating and is_bone_floating(src_pbone, hip_bone.name)):
                        constr_types.append('COPY_LOCATION')

                    constr_types.append('COPY_ROTATION')
                    constr_types.append('COPY_SCALE')

                    subtarget_name = f'{name}_{cp_suffix}'

                    if subtarget_name in new_ob.data.bones:
                
                        for constr_type in constr_types:
                            constr = src_pbone.constraints.new(type=constr_type)
                            constr.target = new_ob
                            
                            constr.subtarget = subtarget_name

                        #//shape
                        new_ob_bone = new_ob.pose.bones[subtarget_name]
                        new_ob_bone.custom_shape = src_pbone.custom_shape
                        new_ob_bone.custom_shape_transform = src_pbone.custom_shape_transform
                        new_ob_bone.custom_shape_rotation_euler = src_pbone.custom_shape_rotation_euler
                        new_ob_bone.custom_shape_scale_xyz = src_pbone.custom_shape_scale_xyz
                        new_ob_bone.custom_shape_translation = src_pbone.custom_shape_translation
                        new_ob_bone.custom_shape_wire_width = src_pbone.custom_shape_wire_width
                        new_ob_bone.color.palette = src_pbone.color.palette
                        new_ob_bone.color.custom.normal = src_pbone.color.custom.normal
                        new_ob_bone.color.custom.select = src_pbone.color.custom.select 
                        new_ob_bone.color.custom.active = src_pbone.color.custom.active

                #root transform

                _constrained_root = ob.pose.bones[self.root_motion_a] if self.root_motion_a else None
                if self.root_motion_a and _constrained_root:
                    #position
                    constr = None
                    loc_constr = None
                    for cons in reversed(_constrained_root.constraints):
                        if cons.type == 'LIMIT_LOCATION':
                            constr = cons
                        if cons.type == 'COPY_LOCATION':
                            loc_constr = cons

                    #create a contraint if not found
                    if not loc_constr:
                        loc_constr = _constrained_root.constraints.new('COPY_LOCATION')
                        loc_constr.target = new_ob
                        loc_constr.subtarget = self.root_motion_a

                    if not constr:
                        constr = _constrained_root.constraints.new('LIMIT_LOCATION')
                    
                    constr.use_min_x = self.root_use_loc_min_x or not self.root_cp_loc_x
                    constr.use_min_y = self.root_use_loc_min_y or not self.root_cp_loc_y
                    constr.use_min_z = self.root_use_loc_min_z or not self.root_cp_loc_z

                    constr.use_max_x = self.root_use_loc_max_x or not self.root_cp_loc_x
                    constr.use_max_y = self.root_use_loc_max_y or not self.root_cp_loc_y
                    constr.use_max_z = self.root_use_loc_max_z or not self.root_cp_loc_z

                    constr.min_x = self.root_loc_min_x if self.root_cp_loc_x and self.root_use_loc_min_x else 0.0
                    constr.min_y = self.root_loc_min_y if self.root_cp_loc_y and self.root_use_loc_min_y else 0.0
                    constr.min_z = self.root_loc_min_z if self.root_cp_loc_z and self.root_use_loc_min_z else 0.0

                    constr.max_x = self.root_loc_max_x if self.root_cp_loc_x and self.root_use_loc_max_x else 0.0
                    constr.max_y = self.root_loc_max_y if self.root_cp_loc_y and self.root_use_loc_max_y else 0.0
                    constr.max_z = self.root_loc_max_z if self.root_cp_loc_z and self.root_use_loc_max_z else 0.0

                    #rotation
                    constr = None
                    for cons in reversed(_constrained_root.constraints):
                        if cons.type == 'COPY_ROTATION':
                            constr = cons
                            break
                    if not constr:
                        constr = _constrained_root.constraints.new('COPY_ROTATION')
                        constr.target = new_ob

                        constr.subtarget = self.root_motion_a

                    constr.use_x = self.root_cp_rot_x
                    constr.use_y = self.root_cp_rot_y
                    constr.use_z = self.root_cp_rot_z

                    #Scale
                    constr = None
                    for cons in reversed(_constrained_root.constraints):
                        if cons.type == 'COPY_SCALE':
                            constr = cons
                            break
                    if not constr:
                        constr = _constrained_root.constraints.new('COPY_SCALE')
                        constr.target = new_ob

                        constr.subtarget = self.root_motion_a
                    
                    constr.use_x = self.root_cp_scal_x
                    constr.use_y = self.root_cp_scal_y
                    constr.use_z = self.root_cp_scal_z

                #Show retarget bone
                bpy.ops.pose.select_all(action='SELECT')
                bpy.ops.pose.hide(unselected=False)
                ret_collection.is_visible = True

                ob = new_ob
                bpy.ops.object.mode_set(mode='POSE')

            #speed
            if self.speed != 1:

                action = action = ob.animation_data.action

                #int current frame

                frame_start, frame_end = action.frame_range
    
                lenght = abs(frame_start) - abs(frame_end)

                action = ob.animation_data.action

                for slot in action.slots:
                    
                    if not self.all_slots:
                        if not ob in slot.users(): 
                            continue

                    channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)

                    if self.speed >= 0:
                        
                        for fc in channelbag.fcurves:
                            for keyframe_point in fc.keyframe_points:
                                new_time = frame_start + (keyframe_point.co[0] - frame_start) * self.speed
                                keyframe_point.co[0] = new_time
                            fc.keyframe_points.deduplicate()
                            fc.update()
                    
                    else:
                        for fc in channelbag.fcurves:
                            for kp in fc.keyframe_points:
                                kp.co.x = frame_start + (kp.co.x - frame_start) * self.speed
                
                            # Ensure the f-curve handles are updated after keyframe modification
                            fc.update()

                        #translation
                        pivot_frame = abs(int(lenght * self.speed))
                        for fc in channelbag.fcurves:
                            for kp in fc.keyframe_points:
                                kp.co.x += pivot_frame
                                if kp.handle_left_type != 'FREE': # Only adjust if not auto/vector
                                    kp.handle_left.x += pivot_frame
                                if kp.handle_right_type != 'FREE':
                                    kp.handle_right.x += pivot_frame
                            fc.keyframe_points.deduplicate()
                            fc.update()

            #repeat
            self.repeat = abs(self.repeat)
            if self.repeat != 1:

                
                action = ob.animation_data.action

                #int current frame

                frame_start, frame_end = action.frame_range
    
                lenght = int(abs(abs(frame_start) - abs(frame_end)))

                # %1 partie decimal
                new_leght = lenght * floor(self.repeat) + lenght * (self.repeat % 1)

                n_repeat = ceil(new_leght / lenght)

                for slot in action.slots:
                    
                    if not self.all_slots:
                        if not ob in slot.users(): 
                            continue

                    channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)

                    repeat = 1
                    offset = 1

                    while repeat <= n_repeat:

                        for fc in channelbag.fcurves:

                                prev_kp = None
                                curent_legth = lenght * repeat

                                key_x = []
                                key_y = []
                        
                                for kp in fc.keyframe_points:

                                    if curent_legth >= new_leght:
                                        break
                                    
                                    if not prev_kp:
                                        curent_legth += offset
                                    
                                    elif (kp.co[0] - frame_start) % lenght == 0:
                                        curent_legth += offset

                                    else:
                                        kp_dif = kp.co[0] - prev_kp
                                        curent_legth += kp_dif

                                    key_x.append(curent_legth)
                                    key_y.append(kp.co[1])
                                    
                                    prev_kp = kp.co[0]

                                i = 0
                                while i < len(key_x):
                                    fc.keyframe_points.insert(key_x[i], key_y[i])
                                    i += 1

                                fc.keyframe_points.deduplicate()

                                fc.update()
                    
                        repeat += 1

            #action range       
            if self.action_range:
                context.view_layer.objects.active = ob
                bpy.ops.object.retarget_action_to_range()

        bpy.ops.object.mode_set(mode= current_m)
        return {'FINISHED'}

class ConvertBoneNaming(Operator):
    """Convert Bone Names between Naming Convention"""
    bl_idname = "object.retarget_convert_bone_names"
    bl_label = "Rename Bones"
    bl_options = {'REGISTER', 'UNDO'}

    src_preset: EnumProperty(items=preset_handler.iterate_presets_with_current,
                             name="Source Preset",
                             )

    trg_preset: EnumProperty(items=preset_handler.iterate_presets,
                             name="Target Preset",
                             )

    anim_tracks: BoolProperty(
        name="Rename Slots",
        description="Rename the channel of all the SLOTS of the curent Action",
        default=False
    )
    prev_anim_tracks = False
    anim_name_tracks: StringProperty(
        name="Rename Action Start With",
        description="Rename the channel of this Action and to all actions whose name starts with this value  (Empty value is ignored)",
        default=""
    )
    prev_anim_name_tracks = False
    anim_all_tracks: BoolProperty(
        name="Rename similar Actions",
        description="Rename the channel of All Action with same rig type ( IF THERE'S OTHERS AMATURES WiTH THE SAME RIG TYPE, IT WILL BREAK THIER ANIMATION )",
        default=False
    )


    prefix_separator: StringProperty(
        name="Prefix ",
        description="Prefix of the bone name , i.e: MyCharacter:head",
        default=""
    )

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    @staticmethod
    def convert_presets(src_settings, target_settings):
        src_skeleton = preset_handler.get_preset_skel(src_settings)
        trg_skeleton = preset_handler.get_preset_skel(target_settings)

        return src_skeleton, trg_skeleton

    @staticmethod
    def convert_settings(current_settings, target_settings, context, validate=True):
        src_settings = preset_handler.PresetSkeleton()
        src_settings.copy(current_settings)

        src_skeleton = preset_handler.get_settings_skel(src_settings)
        trg_skeleton = preset_handler.set_preset_skel(target_settings, context, validate)

        return src_skeleton, trg_skeleton

    @staticmethod
    def rename_bones(obj, src_skeleton, trg_skeleton, separator="", skip_ik=False, reset=True):
        
        bone_names_map = src_skeleton.conversion_map(trg_skeleton, skip_ik=skip_ik)

        if reset:
            for bone in obj.data.bones:
                if ":" not in bone.name:
                    continue
                bone.name = bone.name.rsplit(":", 1)[1]

        bone_map = dict()
        for src_name, trg_name in bone_names_map.items():
            
            if not trg_name:
                continue
            if not src_name:
                continue
            try:
                src_bone = obj.data.bones.get(src_name, None)
            except SystemError:                    
                continue

            if not src_bone:
                continue

            if(separator != "" and separator != ":"):

                tmp = separator.split(":")
                src_bone.name = tmp[0] + ":" + trg_name
            else:
                src_bone.name = trg_name
            
            #update the map
            bone_map[src_name] = src_bone.name

        return bone_map

    def execute(self, context):
        
        current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')

        #ini animation value

        if self.prev_anim_tracks and self.anim_tracks == False:
            self.anim_name_tracks = ""
            self.anim_all_tracks = False

        if self.prev_anim_name_tracks and self.anim_name_tracks == "":
            self.anim_all_tracks = False

        self.anim_tracks = self.anim_tracks or self.anim_name_tracks != "" or self.anim_all_tracks

        self.prev_anim_tracks = self.anim_tracks
        self.prev_anim_name_tracks = self.anim_name_tracks != ""



        if self.src_preset == "--Current--":
            current_settings = context.object.data.retarget_retarget
            trg_settings = preset_handler.PresetSkeleton()
            trg_settings.copy(current_settings)
            src_skeleton, trg_skeleton = self.convert_settings(trg_settings, context, self.trg_preset, validate=False)

            set_preset = False
        else:
            src_skeleton, trg_skeleton = self.convert_presets(self.src_preset, self.trg_preset)

            set_preset = True

        armatures = context.selected_objects
        for armature in armatures:

            if armature.type != 'ARMATURE':
                continue

            if all((src_skeleton, trg_skeleton, src_skeleton != trg_skeleton)):
                
                if self.anim_tracks:
                    actions = []
                    if self.anim_all_tracks:
                        actions = [action for action in bpy.data.actions if validate_actions(action, armature.path_resolve)]
                    else:
                        if armature.animation_data and armature.animation_data.action:
                            actions.append(armature.animation_data.action)
                        if self.anim_name_tracks != "":
                            for action in bpy.data.actions:
                                if action.name.startswith(self.anim_name_tracks)  and action not in actions:
                                    actions.append(action)

                else:
                    actions = []

                bone_names_map = self.rename_bones(armature, src_skeleton, trg_skeleton,
                                                self.prefix_separator)

                if armature.animation_data and armature.data.animation_data:
                    for driver in chain(armature.animation_data.drivers, armature.data.animation_data.drivers):
                        try:
                            driver_bone = driver.data_path.split('"')[1]
                        except IndexError:
                            continue

                        try:
                            trg_name = bone_names_map[driver_bone]
                        except KeyError:
                            continue

                        driver.data_path = driver.data_path.replace('bones["{0}"'.format(driver_bone),
                                                                    'bones["{0}"'.format(trg_name))

                for action in actions:

                    if not action:
                        continue
                    
                    for slot in action.slots:
                        
                        if slot.target_id_type != 'OBJECT':
                            continue

                        channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)

                        for group in channelbag.groups:
                            try:
                                # Update group data paths
                                gr_name = group.name
                                if ":" in group.name:
                                    old_name = group.name.rsplit(":", 1)[1]
                                else:
                                    old_name = group.name
                                new_name = bone_names_map[old_name]
                                group.name = new_name

                                # Update F-Curve data paths
                                for fcurve in group.channels:
                                    fcurve.data_path = fcurve.data_path.replace(gr_name, new_name)
                            except KeyError:
                                continue

                if set_preset:
                    preset_handler.set_preset_skel(self.trg_preset, context)
                else:
                    preset_handler.validate_preset(armature.data, separator=":")

        bpy.ops.object.mode_set(mode= current_m)

        return {'FINISHED'}

class ApplyAsRestPose(Operator):
    """Apply the pose as a rest pose and align the mesh to this new rest pose"""
    bl_idname = "object.retarget_apply_as_rest_pose"
    bl_label = "Apply As Rest Pose"
    bl_options = {'REGISTER', 'UNDO'}

    only_selected: BoolProperty(name="Only Selected Bone", 
                               description="Apply the pose as a rest pose only on selected bone", 
                               default=False)
    apply_shape_key: BoolProperty(name="Apply All Shape Keys", 
                                   description="The shape keys will prevent this operation",
                                  default=False)
    
    apply: BoolProperty(name="Apply", default=True)

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.object.type != 'ARMATURE':
            return False
        return True
    
    def draw(self, context):
        layout = self.layout
        column = layout.column()

       
        for ob in context.selected_objects:
            if ob.animation_data and ob.animation_data.action:
                row = column.row()
                t = "--It will break the Action--".center(50)
                row.label(text= t, icon='ERROR')
                break

        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "only_selected")

        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "apply_shape_key")
    
        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "apply", toggle=True)
    
    def execute(self, context):

        if not self.apply:
            return {'FINISHED'}

        current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')


        armatures = context.selected_objects
        for ob in armatures:

            if ob.type != 'ARMATURE':
                continue

            context.view_layer.objects.active = ob

            exit = False
            #can't apply the armature with sape key
            for mesh in ob.children:
                if not mesh or not mesh.data:
                    continue
                if mesh.data.shape_keys and len(mesh.data.shape_keys.key_blocks) > 1:
                    if self.apply_shape_key:
                        bpy.ops.object.mode_set(mode='OBJECT')
                        mesh.select_set(True)
                        context.view_layer.objects.active = mesh
                        # select shape key
                        mesh.active_shape_key_index = 0
                        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                        mesh.select_set(False)
                        context.view_layer.objects.active = ob
                        bpy.ops.object.mode_set(mode='POSE')
                    else:
                        self.report({'WARNING'}, f"Apply the shape key in {mesh.name}")
                        exit = True

            
            if exit:
                continue
           
            #duplic mod and apply
            if self.only_selected:
                for bone in ob.pose.bones:
                    if bone.select == True:
                        continue
                    bone.location = [0,0,0]
                    bone.rotation_euler = [0,0,0]
                    bone.scale = [1,1,1]
 
            for mesh in ob.children:
                
                for mod in mesh.modifiers:
                    if mod.type == 'ARMATURE' and mod.object == ob:
                        new_modifier_name = mod.name + "_copy"
                        new_mod = mesh.modifiers.new(name=new_modifier_name, type=mod.type)
                        bone_utils.copy_modifier_properties(mod, new_mod)
                        with context.temp_override(object=mesh):
                            try:
                                bpy.ops.object.modifier_apply( modifier=new_mod.name)
                            except RuntimeError:
                                self.report({'WARNING'}, f"Error applying {new_modifier_name} to {mesh.name}")

                        break

            bpy.ops.pose.armature_apply(selected= self.only_selected)

        bpy.ops.object.mode_set(mode=current_m)
        return {'FINISHED'}


class CreateTransformOffset(Operator):
    """Apply the scale ( without breaking the animation) / Scale the Character and setup an Empty to preserve final transform"""
    bl_idname = "object.retarget_create_offset"
    bl_label = "Apply Scale / Create Scale Offset"
    bl_options = {'REGISTER', 'UNDO'}

    container_name: StringProperty(name="Name", description="Name of the transform container", default="EMP-Offset")
    container_scale: FloatProperty(name="Scale", description="Scale of the transform container", default=1)
    
    fix_animations: BoolProperty(name="Fix Slot", description="Apply Scale only to the current slot of the current action", default=True)
    prev_fix_animations = True
    
    fix_action_animations: BoolProperty(name="Fix Action", description="Apply Scale to all the slots of the current action", default=False)
    prev_fix_action_animations = False
    
    fix_action_name_animations: StringProperty(name="", description="Apply the scale to this action and to all actions whose name starts with this value (Empty value is ignored)", default="")
    prev_fix_action_name_animations = False
    
    fix_all_animations: BoolProperty(name="Fix All Similar Actions", description="Apply Scale to all action with same rig type (   IF THERE'S OTHERS AMATURES WiTH THE SAME RIG TYPE, IT CAN BREAK THIER ANIMATION )", default=False)
    fix_constraints: BoolProperty(name="Fix Constraints", description="Apply Offset to character constraints", default=True)
    apply_scale: BoolProperty(name="Apply Scale", default=True)
    do_parent: BoolProperty(name="Parent to the a Offset", description="Parent to the new offset to preserve final transform",
                            default=False, options={'SKIP_SAVE'})

    _allowed_modes = ['OBJECT', 'POSE']

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        
        #if context.object.parent:
            #return False
        if context.object.type != 'ARMATURE':
            return False
        if context.mode not in cls._allowed_modes:
            return False

        return True

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.split(factor=0.2, align=True)
        row.label(text="Name")
        row.prop(self, 'container_name', text="")

        row = column.split(factor=0.2, align=True)
        row.label(text="Scale")
        row.prop(self, "container_scale", text="")

        row = column.split(factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "fix_animations")
        
        row = column.split(factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "fix_action_animations")
        
        row = column.split(factor=0.4, align=True)
        row.label(text="Action Start With")
        row.prop(self, "fix_action_name_animations")
        
        row = column.split(factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "fix_all_animations")

        row = column.split(factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "fix_constraints")

        row = column.split(factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "apply_scale")


        row = column.split(factor=0.2, align=True)
        row.label(text="")
        row.prop(self, "do_parent", toggle=True)

    def execute(self, context):

        armatures = context.selected_objects

        emp_ob = bpy.data.objects.new(self.container_name, None)
        context.collection.objects.link(emp_ob)

        for arm_ob in armatures:

            if arm_ob.type != 'ARMATURE':
                continue
            
            container_scal = self.container_scale

            if self.apply_scale:
                current_m = context.mode
                bpy.ops.object.mode_set(mode='OBJECT')
                prev = arm_ob.scale[0]

                arm_ob.scale[0] = 1
                arm_ob.scale[1] = 1
                arm_ob.scale[2] = 1

                container_scal = self.container_scale / prev
                
                context.view_layer.objects.active = arm_ob
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                bpy.ops.object.mode_set(mode= current_m)

            transform = Matrix().to_3x3() * container_scal

            emp_ob.matrix_world = transform.to_4x4()

            if self.do_parent:
                arm_ob.parent = emp_ob

            inverted = emp_ob.matrix_world.inverted()
            arm_ob.data.transform(inverted)
            arm_ob.update_tag()

            # bring in metarig if found
            try:
                metarig = next(ob for ob in arm_ob.children if ob.type == 'ARMATURE' and ob.data.rigify_target_rig == arm_ob)
                
            except (StopIteration, AttributeError):  # Attribute Error if Rigify is not loaded
                pass
            else:
                if self.do_parent:
                    metarig.parent = emp_ob
                metarig.data.transform(inverted)
                metarig.update_tag()

            if self.fix_constraints:
                # fix constraints rest lenghts
                for pbone in arm_ob.pose.bones:
                    for constr in pbone.constraints:
                        if constr.type == 'STRETCH_TO':
                            constr.rest_length /= container_scal
                        elif constr.type == 'LIMIT_DISTANCE':
                            constr.distance /= container_scal
                        elif constr.type == 'ACTION':
                            if constr.target == arm_ob and constr.transform_channel.startswith('LOCATION'):
                                if constr.target_space != 'WORLD':
                                    constr.min /= container_scal
                                    constr.max /= container_scal
                        elif constr.type == 'LIMIT_LOCATION' and constr.owner_space != 'WORLD':
                            constr.min_x /= container_scal
                            constr.min_y /= container_scal
                            constr.min_z /= container_scal

                            constr.max_x /= container_scal
                            constr.max_y /= container_scal
                            constr.max_z /= container_scal

            # scale rigged meshes as well
            rigged = []
            for ob in arm_ob.children:
                if ob.name not in rigged:
                    rigged.append(ob)

            for ob in rigged:
                if ob.data.shape_keys:
                    # cannot transform objects with shape keys
                    ob.scale /= container_scal
                else:
                    ob.data.transform(inverted)
                # fix scale dependent attrs in modifiers
                for mod in ob.modifiers:
                    if mod.type == 'DISPLACE':
                        mod.strength /= container_scal
                    elif mod.type == 'SOLIDIFY':
                        mod.thickness /= container_scal

            #fix animation
            #set value
            if self.prev_fix_animations and self.fix_animations == False:
                self.fix_action_animations = self.fix_all_animations = False
                self.fix_action_name_animations = ""

            if self.prev_fix_action_animations and self.fix_action_animations == False:
                self.fix_all_animations = False
                self.fix_action_name_animations = ""

            if self.prev_fix_action_name_animations and self.fix_action_name_animations =="":
                self.fix_all_animations = False

            self.fix_animations = self.fix_animations or self.fix_action_animations or self.fix_action_name_animations != "" or self.fix_all_animations
            self.fix_action_animations = self.fix_action_animations or self.fix_action_name_animations != "" or self.fix_all_animations

            self.prev_fix_animations = self.fix_animations
            self.prev_fix_action_animations = self.fix_action_animations
            self.prev_fix_action_name_animations = self.fix_action_name_animations != ""


            if self.fix_animations:
                actions = []
                if self.fix_all_animations:
                    actions = [action for action in bpy.data.actions if validate_actions(action, arm_ob.path_resolve)]
                else:
                    if arm_ob.animation_data and arm_ob.animation_data.action:
                        actions.append(arm_ob.animation_data.action)
                    if self.fix_action_name_animations:
                        for action in bpy.data.actions:
                            if action.name.startswith(self.fix_action_name_animations) and action not in actions:
                                actions.append(action)

                for action in actions:

                    if not action:
                        continue

                    for slot in action.slots:

                        if slot.target_id_type != 'OBJECT':
                            continue

                        if  not self.fix_all_animations and not self.fix_action_animations and not self.fix_action_name_animations and not (arm_ob in slot.users() ):
                            continue

                        channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                       
                        for fc in channelbag.fcurves:
                            data_path = fc.data_path

                            if not data_path.endswith('location'):
                                continue

                            for kf in fc.keyframe_points:
                                kf.co[1] /= container_scal
        #delete the empty                        
        if not self.do_parent:
            current_m = context.mode
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.select_pattern( pattern=emp_ob.name, case_sensitive=True, extend=False)
            bpy.ops.object.delete(use_global=False)
            #reset the selection
            for armature in armatures:
                bpy.ops.object.select_pattern( pattern=armature.name, case_sensitive=True, extend=True)

            bpy.ops.object.mode_set(mode=current_m)

        return {'FINISHED'}
   

class ExtractMetarig(Operator):
    """Create Metarig from current object"""
    bl_idname = "object.retarget_extract_metarig"
    bl_label = "Extract Metarig"
    bl_description = "Create Metarig from current Armature , (place your character in the center of the scene)"
    bl_options = {'REGISTER', 'UNDO'}

    rig_preset: EnumProperty(items=preset_handler.iterate_presets_with_current,
                             name="Rig Type",
                             )

    offset_knee: FloatProperty(name='Offset Knee',
                               default=0.0)

    offset_elbow: FloatProperty(name='Offset Elbow',
                                default=0.0000001)

    offset_fingers: FloatVectorProperty(name='Offset Fingers')

    no_face: BoolProperty(name='No face bones',
                          default=True)
    
    no_breast: BoolProperty(name='No breast bones',
                          default=True)

    rigify_names: BoolProperty(name='Use rigify names',
                               default=True)
    
    other_bone: BoolProperty(name='Add Other Bone',
                             description='Include additional bones (such as clothing bone)',
                               default=True)

    assign_metarig: BoolProperty(name='Assign metarig',
                                 default=True,
                                 description='Rigify will generate to the active object')

    forward_spine_roll: BoolProperty(name='Align spine frontally', default=True,
                                     description='Spine Z will face the Y axis')

    apply_transforms: BoolProperty(name='Apply Transform', default=True,
                                   description='Apply current transforms before extraction')

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        # if not context.active_object.data.retarget_retarget.has_settings():
        row = column.row()
        row.prop(self, 'rig_preset', text="Rig Type")

        row = column.split(factor=0.5, align=True)
        row.label(text="Offset Knee")
        row.prop(self, 'offset_knee', text='')

        row = column.split(factor=0.5, align=True)
        row.label(text="Offset Elbow")
        row.prop(self, 'offset_elbow', text='')

        row = column.split(factor=0.5, align=True)
        row.label(text="Offset Fingers")
        row.prop(self, 'offset_fingers', text='')

        row = column.split(factor=0.5, align=True)
        row.label(text="No Face Bones")
        row.prop(self, 'no_face', text='')


        row = column.split(factor=0.5, align=True)
        row.label(text="No Breast Bones")
        row.prop(self, 'no_breast', text='')

        row = column.split(factor=0.5, align=True)
        row.label(text="Use Rigify Names")
        row.prop(self, 'rigify_names', text='')

        if self.rigify_names:
            row = column.split(factor=0.5, align=True)
            row.label(text="Add Other Bone")
            row.prop(self, 'other_bone', text='')

        row = column.split(factor=0.5, align=True)
        row.label(text="Assign Metarig")
        row.prop(self, 'assign_metarig', text='')

        row = column.split(factor=0.5, align=True)
        row.label(text="Align spine frontally")
        row.prop(self, 'forward_spine_roll', text='')

        row = column.split(factor=0.5, align=True)
        row.label(text="Apply Transform")
        row.prop(self, 'apply_transforms', text='')

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if 'rigify' not in context.preferences.addons:
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):

        current_m = context.mode

        armatures = context.selected_objects
        for src_object in armatures:

            if src_object.type != 'ARMATURE':
                continue
            context.view_layer.objects.active = src_object
            bpy.ops.object.mode_set(mode='POSE')

            src_armature = src_object.data

            current_settings = src_object.data.retarget_retarget

            if self.rig_preset == "--Current--":

                if current_settings.deform_preset and current_settings.deform_preset != '--':
                    deform_preset = current_settings.deform_preset

                    src_skeleton = preset_handler.set_preset_skel(deform_preset, context)
                    current_settings = src_skeleton
                else:
                    src_settings = preset_handler.PresetSkeleton()
                    src_settings.copy(current_settings)
                    src_skeleton = preset_handler.get_settings_skel(src_settings)
            else:
                src_skeleton = preset_handler.set_preset_skel(self.rig_preset, context)
                
            if not src_skeleton:
                continue



            # TODO: remove action, bring to rest pose
            if self.apply_transforms:
                rigged = (ob for ob in src_object.children)

                for ob in rigged:
                    if ob and ob.data:
                        ob.data.transform(src_object.matrix_local)

                src_armature.transform(src_object.matrix_local)
                src_object.matrix_local = Matrix()

            met_skeleton = bone_mapping.RigifyMeta()

            bone_names_map = dict()

            if self.rigify_names:
                # check if doesn't contain rigify deform bones already
                bones_needed = met_skeleton.spine.hips, met_skeleton.spine.spine
                if not [b for b in bones_needed if b in src_armature.bones]:
                    # Converted settings should not be validated yet, as bones have not been renamed
                    src_skeleton, trg_skeleton = ConvertBoneNaming.convert_settings(current_settings, 'Rigify_Deform.py', context, validate=False)
                    #resetname = len(armatures) > 1
                    #TODO check it
                    bone_names_map = src_skeleton.conversion_map(trg_skeleton)

                    ConvertBoneNaming.rename_bones(src_object, src_skeleton, trg_skeleton, skip_ik=True, reset=False)
                    src_skeleton = bone_mapping.RigifySkeleton()

                    for name_attr in ('left_eye', 'right_eye'):
                        bone_name = getattr(src_skeleton.face, name_attr)

                        if bone_name not in src_armature.bones and bone_name[4:] in src_armature.bones:
                            # fix eye bones lacking "DEF-" prefix on b3.2
                            setattr(src_skeleton.face, name_attr, bone_name[4:])

                        if src_skeleton.face.super_copy:
                            # supercopy def bones start with DEF-
                            bone_name = getattr(src_skeleton.face, name_attr)

                            if not bone_name.startswith('DEF-'):
                                new_name = f"DEF-{bone_name}"
                                try:
                                    src_object.data.bones[bone_name].name = new_name
                                except KeyError:
                                    pass
                                else:
                                    setattr(src_skeleton.face, name_attr, new_name)

            else:
                self.other_bone = False

            if self.other_bone:

                for bone in src_object.pose.bones:
                    if bone.name not in bone_names_map.values() and bone.name != "Root":
                        bone.rigify_type = "basic.super_copy"
                        

            # if self.other_bone:

            #     for bone in src_object.pose.bones:
            #         if bone.name not in bone_names_map.values() and bone.name != "Root":

            #             if bone.child and bone.parent and bone.parent in bone_names_map.values():
            #                 bone.rigify_type = "limbs.simple_tentacle"

            #             elif not bone.child and bone.parent and bone.parent in bone_names_map.values():
            #                 bone.rigify_type = "basic.super_copy"

            #             additional_bones.append((bone.name, bone.rigify_type))

             # bones that have rigify attr will be copied when the metarig is in edit mode
                additional_bones = [(b.name, b.rigify_type) for b in src_object.pose.bones if b.rigify_type]

           
            try:
                metarig = next(ob for ob in context.scene.objects if ob.type == 'ARMATURE' and ob.data.rigify_target_rig == src_object)
                #check visibility 
            except AttributeError:
                self.report({'WARNING'}, 'Rigify Add-On not enabled')
                return {'CANCELLED'}
            except StopIteration:
                create_metarig = True
                met_armature = bpy.data.armatures.new('metarig')
                metarig = bpy.data.objects.new("metarig", met_armature)
                try:
                    metarig.data.rigify_rig_basename = src_object.name
                except AttributeError:
                    # removed in rigify 0.6.4
                    pass

                context.collection.objects.link(metarig)
            else:
                met_armature = metarig.data
                create_metarig = False

            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            metarig.select_set(True)
            context.view_layer.objects.active = metarig
            bpy.ops.object.mode_set(mode='EDIT')

            if create_metarig:
                from rigify.metarigs import human
                human.create(metarig)

            def match_meta_bone(met_bone_group, src_bone_group, bone_attr, axis=None):
                try:
                    met_bone = met_armature.edit_bones[getattr(met_bone_group, bone_attr)]
                    src_bone_name = getattr(src_bone_group, bone_attr)
                    src_bone = src_armature.bones.get(src_bone_name, None)
                    
                except KeyError:
                    return

                if not src_bone:
                    self.report({'WARNING'}, f"{bone_attr}, {src_bone_name} not found in {src_armature}")
                    return

                met_bone.head = src_bone.head_local
                met_bone.tail = src_bone.tail_local

                if met_bone.parent and met_bone.use_connect:
                    bone_dir = met_bone.vector.normalized()
                    parent_dir = met_bone.parent.vector.normalized()

                    if bone_dir.dot(parent_dir) < -0.6:
                        self.report({'WARNING'}, f"{met_bone.name} is not aligned with its parent")
                        # TODO

                if axis:
                    met_bone.roll = bone_utils.ebone_roll_to_vector(met_bone, axis)
                else:
                    src_x_axis = Vector((0.0, 0.0, 1.0)) @ src_bone.matrix_local.inverted().to_3x3()
                    src_x_axis.normalize()
                    met_bone.roll = bone_utils.ebone_roll_to_vector(met_bone, src_x_axis)

                return met_bone

            for bone_attr in ['hips', 'spine', 'spine1', 'spine2', 'neck', 'head']:
                if self.forward_spine_roll:
                    align = Vector((0.0, -1.0, 0.0))
                else:
                    align = None
                match_meta_bone(met_skeleton.spine, src_skeleton.spine, bone_attr, axis=align)

            for bone_attr in ['shoulder', 'arm', 'forearm', 'hand']:
                match_meta_bone(met_skeleton.right_arm, src_skeleton.right_arm, bone_attr)
                match_meta_bone(met_skeleton.left_arm, src_skeleton.left_arm, bone_attr)

            for bone_attr in ['upleg', 'leg', 'foot', 'toe']:
                match_meta_bone(met_skeleton.right_leg, src_skeleton.right_leg, bone_attr)
                match_meta_bone(met_skeleton.left_leg, src_skeleton.left_leg, bone_attr)

            rigify_face_bones = bone_mapping.rigify_face_bones
            for bone_attr in ['left_eye', 'right_eye', 'jaw']:
                met_bone = match_meta_bone(met_skeleton.face, src_skeleton.face, bone_attr)
                if met_bone:
                    try:
                        rigify_face_bones.remove(met_skeleton.face[bone_attr])
                    except ValueError:
                        pass

                    if src_skeleton.face.super_copy:
                        metarig.pose.bones[met_bone.name].rigify_type = "basic.super_copy"
                        # FIXME: sometimes eye bone group is not renamed accordingly
                        # TODO: then maybe change jaw shape to box

            try:
                right_leg = met_armature.edit_bones[met_skeleton.right_leg.leg]
                left_leg = met_armature.edit_bones[met_skeleton.left_leg.leg]
            except KeyError:
                pass
            else:
                offset = Vector((0.0, self.offset_knee, 0.0))
                for bone in right_leg, left_leg:
                    bone.head += offset

                try:
                    right_knee = met_armature.edit_bones[met_skeleton.right_arm.forearm]
                    left_knee = met_armature.edit_bones[met_skeleton.left_arm.forearm]
                except KeyError:
                    pass
                else:
                    offset = Vector((0.0, self.offset_elbow, 0.0))

                    for bone in right_knee, left_knee:
                        bone.head += offset

            def match_meta_fingers(met_bone_group, src_bone_group, bone_attr):
                met_bone_names = getattr(met_bone_group, bone_attr)
                src_bone_names = getattr(src_bone_group, bone_attr)

                if not src_bone_names:
                    print(bone_attr, "not found in", src_armature)
                    return
                if not met_bone_names:
                    print(bone_attr, "not found in", src_armature)
                    return

                if 'thumb' not in bone_attr:
                    try:
                        met_bone = met_armature.edit_bones[met_bone_names[0]]
                        src_bone = src_armature.bones.get(src_bone_names[0], None)
                    except KeyError:
                        pass
                    else:
                        if src_bone:
                            palm_bone = met_bone.parent

                            palm_bone.tail = src_bone.head_local
                            hand_bone = palm_bone.parent
                            palm_bone.head = hand_bone.head * 0.75 + src_bone.head_local * 0.25
                            palm_bone.roll = 0

                for met_bone_name, src_bone_name in zip(met_bone_names, src_bone_names):
                    try:
                        met_bone = met_armature.edit_bones[met_bone_name]
                        src_bone = src_armature.bones[src_bone_name]
                    except KeyError:
                        print("source bone not found", src_bone_name)
                        continue

                    met_bone.head = src_bone.head_local
                    try:
                        met_bone.tail = src_bone.children[0].head_local
                    except IndexError:
                        bone_utils.align_to_closer_axis(src_bone, met_bone)

                    met_bone.roll = 0.0

                    src_z_axis = Vector((0.0, 0.0, 1.0)) @ src_bone.matrix_local.to_3x3()

                    inv_rot = met_bone.matrix.to_3x3().inverted()
                    trg_z_axis = src_z_axis @ inv_rot
                    dot_z = (met_bone.z_axis @ met_bone.matrix.inverted()).dot(trg_z_axis)
                    met_bone.roll = dot_z * pi

                    offset_fingers = Vector(self.offset_fingers) @ src_bone.matrix_local.to_3x3()
                    if met_bone.head.x < 0:  # Right side
                        offset_fingers /= -100
                    else:
                        offset_fingers /= 100

                    if met_bone.parent.name in met_bone_names and met_bone.children:
                        met_bone.head += offset_fingers
                        met_bone.tail += offset_fingers

            for bone_attr in ['thumb', 'index', 'middle', 'ring', 'pinky']:
                match_meta_fingers(met_skeleton.right_fingers, src_skeleton.right_fingers, bone_attr)
                match_meta_fingers(met_skeleton.left_fingers, src_skeleton.left_fingers, bone_attr)

            try:
                met_armature.edit_bones['spine.003'].tail = met_armature.edit_bones['spine.004'].head
                met_armature.edit_bones['spine.005'].head = (met_armature.edit_bones['spine.004'].head + met_armature.edit_bones['spine.006'].head) / 2
            except KeyError:
                pass

            # find foot vertices
            foot_verts = {}
            foot_ob = None
            # pick object with most foot verts
            for ob in bone_utils.iterate_rigged_obs(src_object, context):
                if src_skeleton.left_leg.foot not in ob.vertex_groups:
                    continue
                grouped_verts = bone_utils.get_group_verts(ob, src_skeleton.left_leg.foot, threshold=0.8)
                if len(grouped_verts) > len(foot_verts):
                    foot_verts = grouped_verts
                    foot_ob = ob

            if foot_verts:
                # find rear verts (heel)
                rearest_y = max([foot_ob.data.vertices[v].co[1] for v in foot_verts])
                leftmost_x = max([foot_ob.data.vertices[v].co[0] for v in foot_verts])  # FIXME: we should counter rotate verts for more accuracy
                rightmost_x = min([foot_ob.data.vertices[v].co[0] for v in foot_verts])

                for side in 'L', 'R':
                    # invert left/right vertices when we switch sides
                    leftmost_x, rightmost_x = rightmost_x, leftmost_x

                    heel_bone = met_armature.edit_bones['heel.02.' + side]

                    heel_bone.head.y = rearest_y
                    heel_bone.tail.y = rearest_y

                    if heel_bone.head.x > 0:
                        heel_head = leftmost_x
                        heel_tail = rightmost_x
                    else:
                        heel_head = rightmost_x * -1
                        heel_tail = leftmost_x * -1
                    heel_bone.head.x = heel_head
                    heel_bone.tail.x = heel_tail

                    try:
                        spine_bone = met_armature.edit_bones['spine']
                        pelvis_bone = met_armature.edit_bones['pelvis.' + side]
                    except KeyError:
                        pass
                    else:
                        pelvis_bone.head = spine_bone.head
                        pelvis_bone.tail.z = spine_bone.tail.z

                    try:
                        spine_bone = met_armature.edit_bones['spine.003']
                        breast_bone = met_armature.edit_bones['breast.' + side]
                    except KeyError:
                        pass
                    else:
                        breast_bone.head.z = spine_bone.head.z
                        breast_bone.tail.z = spine_bone.head.z

            if self.no_face:
                for bone_name in rigify_face_bones:
                    try:
                        face_bone = met_armature.edit_bones[bone_name]
                    except KeyError:
                        continue

                    met_armature.edit_bones.remove(face_bone)

            if self.no_breast:
                try:
                    breastl = met_armature.edit_bones["breast.L"]
                    breastr = met_armature.edit_bones["breast.R"]
                    met_armature.edit_bones.remove(breastl)
                    met_armature.edit_bones.remove(breastr)
                except KeyError:
                    pass

            name_collect = "Other Bone"
            try:
                ob_collection = met_armature.collections[name_collect]
            except KeyError:
                ob_collection = met_armature.collections.new(name_collect)
                ob_collection.is_visible = True
            other_bone_found = False

            if self.other_bone:

                for src_name, src_attr in additional_bones:

                    new_bone_name = bone_utils.copy_bone_to_arm(src_object, metarig, src_name, suffix="")
                    new_b = met_armature.edit_bones[new_bone_name]
                    for coll in new_b.collections:
                        coll.unassign(new_b)
                    other_bone_found = True
                    ob_collection.assign(new_b)

                    if 'chain' in src_attr:  # TODO: also fingers
                        # working around weird bug: sometimes src_armature.bones causes KeyError even if the bone is there
                        bone = next((b for b in src_armature.bones if b.name == src_name), None)

                        new_parent_name = new_bone_name
                        while bone:
                            # optional: use connect
                            try:
                                bone = bone.children[0]
                            except IndexError:
                                break

                            child_bone_name = bone_utils.copy_bone_to_arm(src_object, metarig, bone.name, suffix="")
                            child_bone = met_armature.edit_bones[child_bone_name]
                            child_bone.parent = met_armature.edit_bones[new_parent_name]
                            child_bone.use_connect = True

                            bone.name = f"DEF-{bone.name}"
                            new_parent_name = child_bone_name

                    try:
                        bone = next((b for b in src_armature.bones if b.name == src_name), None)
                        
                        if bone:
                            if bone.parent:
                                # FIXME: should use mapping to get parent bone name
                                parent_name = bone.parent.name.replace('DEF-', '')
                                met_armature.edit_bones[new_bone_name].parent = met_armature.edit_bones[parent_name]
                            if ".raw_" in src_attr:
                                met_armature.edit_bones[new_bone_name].use_deform = bone.use_deform
                            elif bone.name.startswith('DEF-'):
                                # already a DEF, need to strip that from metarig bone instead
                                met_armature.edit_bones[new_bone_name].name = new_bone_name.replace("DEF-", '')
                            else:
                                bone.name = f'DEF-{bone.name}'
                    except KeyError:
                        self.report({'WARNING'}, "bones not found in target, perhaps wrong preset?")
                        continue

            bpy.ops.object.mode_set(mode='POSE')

            if self.other_bone:
                #add other bone in interface
                if other_bone_found:
                    bpy.ops.armature.rigify_collection_add_ui_row(row=1, add=True)
                    bpy.ops.armature.rigify_collection_set_ui_row(index= ob_collection.index, row=1)
                # now we can copy the stored rigify attrs
                for src_name, src_attr in additional_bones:
                    src_meta = src_name[4:] if src_name.startswith('DEF-') else src_name
                    metarig.pose.bones[src_meta].rigify_type = src_attr
                    # TODO: should copy rigify options of specific types as well

            if current_settings.left_leg.upleg_twist_02 or current_settings.left_leg.leg_twist_02:
                metarig.pose.bones['thigh.L']['RigifyParameters.segments'] = 3

            if current_settings.right_leg.upleg_twist_02 or current_settings.right_leg.leg_twist_02:
                metarig.pose.bones['thigh.R']['RigifyParameters.segments'] = 3
            
            if current_settings.left_arm.arm_twist_02 or current_settings.left_arm.forearm_twist_02:
                metarig.pose.bones['upper_arm.L']['RigifyParameters.segments'] = 3
            
            if current_settings.right_arm.arm_twist_02 or current_settings.right_arm.forearm_twist_02:
                metarig.pose.bones['upper_arm.R']['RigifyParameters.segments'] = 3

            if self.assign_metarig:
                met_armature.rigify_target_rig = src_object

            metarig.parent = src_object.parent

        bpy.ops.object.mode_set(mode= current_m)
        return {'FINISHED'}


class ActionRangeToScene(Operator):
    """Set Playback range to current action Start/End"""
    bl_idname = "object.retarget_action_to_range"
    bl_label = "Action Range to Scene"
    bl_description = "Match scene range with current action range"
    bl_options = {'REGISTER', 'UNDO'}

    _allowed_modes_ = ['POSE', 'OBJECT']

    @classmethod
    def poll(cls, context):
        obj = context.object

        if not obj:
            return False
        if obj.mode not in cls._allowed_modes_:
            return False
        if not obj.animation_data:
            return False
        if not obj.animation_data.action:
            return False

        return True

    def execute(self, context):
        if not context.object:
            return {'FINISHED'}
        
        if not context.object.animation_data:
            return {'FINISHED'}
        
        if not context.object.animation_data.action:
            return {'FINISHED'}
        
        action_range = context.object.animation_data.action.frame_range

        scn = context.scene
        scn.frame_start = int(action_range[0])
        scn.frame_end = int(action_range[1])

        try:
            bpy.ops.action.view_all()
        except RuntimeError:
            # we are not in a timeline context, let's look for one in the screen
            for window in context.window_manager.windows:
                screen = window.screen
                for area in screen.areas:
                    if area.type == 'DOPESHEET_EDITOR':
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                with context.temp_override(window=window,
                                                           area=area,
                                                           region=region):
                                    bpy.ops.action.view_all()
                                break
                        break
        return {'FINISHED'}


class MergeHeadTails(Operator):
    
    bl_idname = "armature.retarget_merge_head_tails"
    bl_label = "Merge Head/Tails"
    bl_description = "Connect (small bone) head/tails when closer than given max distance"
    bl_options = {'REGISTER', 'UNDO'}

    at_child_head: BoolProperty(
        name="Match at child head",
        description="Bring parent's tail to match child head when possible",
        default=True
    )

    min_distance: FloatProperty(
        name="Distance",
        description="Max Distance for merging",
        default=0.0
    )

    selected_only: BoolProperty(name="Only Selected",
                                default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False
    
        if obj.type != 'ARMATURE':
            return False
    
        return True

    def execute(self, context):

        current_m = context.mode
        bpy.ops.object.mode_set(mode='EDIT')

        bones = []
        if self.selected_only:
            selected_names = [bone.name for bone in context.selected_bones]
           
            for obj in context.selected_objects:
                if obj.type != 'ARMATURE':
                    continue
                bones.extend([bone for bone in obj.data.edit_bones if bone.name in selected_names])
        else:
            for obj in context.selected_objects:
                if obj.type != 'ARMATURE':
                    continue
                bones.extend( obj.data.edit_bones)

        for bone in bones:
            if bone.use_connect:
                continue
            if not bone.parent:
                continue

            distance = (bone.parent.tail - bone.head).length
            if distance <= self.min_distance:
                if self.at_child_head and len(bone.parent.children) == 1:
                    bone.parent.tail = bone.head

                bone.use_connect = True

        for obj in context.selected_objects:
            if obj.type != 'ARMATURE':
                    continue
            obj.update_from_editmode()

        bpy.ops.object.mode_set(mode=current_m)
        return {'FINISHED'}

"""
def mute_fcurves(obj: bpy.types.Object, channel_name: str):
    action = obj.animation_data.action
    if not action:
        return
    for slot in action.slots:
        if slot.target_id_type != 'OBJECT':
            continue
        if not (obj in slot.users() ):
            continue
        channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
            
        for fc in channelbag.fcurves:
            if fc.data_path == channel_name:
                fc.mute = True

def limit_scale(obj):
    constr = obj.constraints.new('LIMIT_SCALE')
    
    constr.owner_space = 'LOCAL'
    constr.min_x = obj.scale[0]
    constr.min_y = obj.scale[1]
    constr.min_z = obj.scale[2]

    constr.max_x = obj.scale[0]
    constr.max_y = obj.scale[1]
    constr.max_z = obj.scale[2]

    constr.use_min_x = True
    constr.use_min_y = True
    constr.use_min_z = True

    constr.use_max_x = True
    constr.use_max_y = True
    constr.use_max_z = True
"""

class ConvertGameFriendly(Operator):
    """Convert Rigify rigs to a Game Friendly hierarchy"""
    bl_idname = "armature.retarget_convert_gamefriendly"
    bl_label = "Rigify Game Friendly"
    bl_description = "Make the rigify deformation bones a one root rig (Select a Rigify Armature)"
    bl_options = {'REGISTER', 'UNDO'}

    keep_backup: BoolProperty(
        name="Backup",
        description="Keep copy of datablock",
        default=True
    )
    rename: StringProperty(
        name="Rename",
        description="Rename rig to 'Armature'",
        default="Armature"
    )
    eye_bones: BoolProperty(
        name="Keep eye bones",
        description="Activate 'deform' for eye bones",
        default=True
    )
    limit_scale: BoolProperty(
        name="Limit Spine Scale",
        description="Limit scale on the spine deform bones",
        default=True
    )
    disable_bendy: BoolProperty(
        name="Disable B-Bones",
        description="Disable Bendy-Bones",
        default=True
    )
    fix_tail: BoolProperty(
        name="Invert Tail",
        description="Reverse the tail direction so that it spawns from hip",
        default=True
    )
    reparent_twist: BoolProperty(
        name="Dispossess Twist Bones",
        description="Rearrange Twist Hierarchy in limbs for in game IK",
        default=True
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False
        if obj.type != 'ARMATURE':
            return False
        return bool(context.active_object.data.get("rig_id"))

    def execute(self, context):

        current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')
        
        armatures = context.selected_objects
        for ob in armatures:

            if ob.type != 'ARMATURE':
                continue
            if not ob.data.get("rig_id"):
                continue

            context.view_layer.objects.active = ob

            if self.keep_backup:
                backup_data = ob.data.copy()
                backup_data.name = ob.name + "_GameUnfriendly_backup"
                backup_data.use_fake_user = True

            if self.rename:
                ob.name = self.rename
                ob.data.name = self.rename

                try:
                    metarig = next(
                        obj for obj in context.scene.objects if obj.type == 'ARMATURE' and obj.data.rigify_target_rig == ob)
                except (StopIteration, AttributeError):  # Attribute Error if Rigify is not loaded
                    pass
                else:
                    try:
                        metarig.data.rigify_rig_basename = self.rename
                    except AttributeError:
                        # Removed in rigify 0.6.4
                        pass

            if self.eye_bones and 'DEF-eye.L' not in ob.pose.bones:
                # Old rigify face: eyes deform is disabled
                # FIXME: the 'DEF-eye.L' condition should be checked on invoke
                try:
                    # Oddly, changes to use_deform are not kept
                    ob.pose.bones["MCH-eye.L"].bone.use_deform = True
                    ob.pose.bones["MCH-eye.R"].bone.use_deform = True
                except KeyError:
                    pass

            bpy.ops.object.mode_set(mode='EDIT')
            num_reparents = bone_utils.gamefriendly_hierarchy(ob, fix_tail=self.fix_tail, limit_scale=self.limit_scale)

            if self.reparent_twist:
                arm_bones = ["DEF-upper_arm", "DEF-forearm", "DEF-hand"]
                leg_bones = ["DEF-thigh", "DEF-shin", "DEF-foot"]
                for side in ".L", ".R":
                    for bone_names in arm_bones, leg_bones:
                        parent_bone = ob.data.edit_bones[bone_names.pop(0) + side] 
                        for bone in bone_names:
                            e_bone = ob.data.edit_bones[bone + side]
                            e_bone.use_connect = False

                            e_bone.parent = parent_bone
                            parent_bone = e_bone

                            num_reparents += 1

            bpy.ops.object.mode_set(mode='POSE')

            if self.disable_bendy:
                for bone in ob.data.bones:
                    bone.bbone_segments = 1
                    # TODO: disable bbone drivers

            self.report({'INFO'}, f'{num_reparents} bones were re-parented')

        bpy.ops.object.mode_set(mode= current_m)
        return {'FINISHED'}


class ConstrainToArmature(Operator):
    bl_idname = "armature.retarget_constrain_to_armature"
    bl_label = "Bind to Active Armature"
    bl_description = "Constrain bones of selected armatures to active armature (select at least 2 armatures)"
    bl_options = {'REGISTER', 'UNDO'}

    same_bone_names: BoolProperty(name="Same Bone Names", 
                                 description="When two armatures have the same bones names ",
                                 default=False)
    
    #ik bone
    detect_ik_bones:  BoolProperty(name="Detect All Ik Bone",  
                                   description="(Bone that the name contain 'ik')",
                                   default=False)
    
    ik_bones:  StringProperty(name = "IK Bones", 
                              description="IK Bones List",
                              default="", options = {'SKIP_SAVE'})
    
    clean_all:  BoolProperty(name="",  
                              description="Delete All",
                             default=False, options = {'SKIP_SAVE'})
    
    clean_last:  BoolProperty(name="",  
                              description="Delete the last one",
                              default=False, options = {'SKIP_SAVE'})
    
    ik_collection = []

    
    
    src_preset: EnumProperty(items=preset_handler.iterate_presets_with_current,
                             name="To Bind",
                             description="Other Armature",
                             )

    trg_preset: EnumProperty(items=preset_handler.iterate_presets_with_current,
                             name="Bind To",
                             description="Active Armature"
                             )
    
    only_animated_Bone: BoolProperty(name="Only Animated Bone", 
                               description="Bind only on Animated Bone (From Target Bones) (Recommended)",
                               default=False)

    only_selected: BoolProperty(name="Only Selected", default=False, description="Bind only selected bones (From Source Bones)")
    
    bind_by_name: BoolProperty(name="Bind bones by name", 
                               description= "Look for bones present in both",
                               default=False)
    name_prefix: StringProperty(name="Add prefix to name", 
                                description= "Add prefix to source bone name",
                                default="")
    name_replace: StringProperty(name="Replace in name", 
                                  description= "Replace in source bone name",
                                 default="")
    name_replace_with: StringProperty(name="Replace in name with", 
                                       description= "Replace with",
                                      default="")
    name_suffix: StringProperty(name="Add suffix to name", 
                                 description= "Add suffix to source bone name",
                                default="")

    ret_bones_collection: StringProperty(name="Layer",
                                             default="Retarget Bones",
                                             description="Armature collection to use for connection bones (Usefull to ADD modification to the Animation)")

    match_transform: EnumProperty(items=[
        ('None', "- None -", "Don't match any transform"),
        ('Bone', "Bones Offset", "Account for difference between control and deform rest pose (Requires similar proportions and Y bone-axis)"),
        ('Pose', "Current Pose is target Rest Pose", "Armature was posed manually to match rest pose of target"),
        ('World', "Follow target Pose in world space", "Just copy target world positions (Same bone orient, different rest pose)"),
    ],
        name="Match Transform",
        default='None')
    
    match_object_transform: BoolProperty(name="Match Object Transform", default=True)
    match_object_transform_s: BoolProperty(name="Match Object Transform", default=False)

    math_look_at: BoolProperty(name="Fix direction",
                               description="Correct chain direction based on mid limb (Useful for IK)",
                               default=False)
    
    copy_IK_roll_hands: BoolProperty(name="Hands IK Roll",
                            description="USe IK target roll from source armature (Useful for IK) (Not recommended)",
                            default=False)
    
    copy_IK_roll_feet: BoolProperty(name="Feet IK Roll",
                            description="USe IK target roll from source armature (Useful for IK) (Not recommended)",
                            default=False)
    
    fit_target_scale: EnumProperty(name="Fit height",
                                   items=(('--', '- None -', 'None'),
                                          ('head', 'head', 'head'),
                                          ('neck', 'neck', 'neck'),
                                          ('spine2', 'chest', 'spine2'),
                                          ('spine1', 'spine1', 'spine1'),
                                          ('spine', 'spine', 'spine'),
                                          ('hips', 'hips', 'hips'),
                                          ),
                                    default='--',
                                    description="Fit height of the target Armature at selected bone")
    
    fit_target_scale_s: StringProperty(name="Fit height",
                            description="Fit height of the target Armature at selected bone",
                            default="")
    
    adjust_location: BoolProperty(default=False, 
                                    description="scale location animation to avoid offset",
                                    name="Adjust location to new scale")

    constrain_root: EnumProperty(items=[
        ('None', "No Root", "Don't constrain root bone"),
        ('Bone', "Bone", "Constrain root to bone"),
        ('Object', "Object", "Constrain root to object")
    ],
        name="Constrain Root",
        default='None')
    

    loc_constraints: BoolProperty(name="Copy Location",
                                  description="Use Location Constraint when binding",
                                  default=False)
    
    rot_constraints: BoolProperty(name="Copy Rotation",
                                  description="Use Rotation Constraint when binding",
                                  default=True)
    
    scal_constraints:BoolProperty(name="Copy Scale",
                                  description="Use Rotation Constraint when binding (_to be used only when they have the same scale )",
                                  default=False)
    
    constraint_policy: EnumProperty(items=[
        ('skip', "Skip Existing Constraints", "Skip Bones that are constrained already"),
        ('disable', "Disable Existing Constraints", "Disable existing binding constraints and add new ones"),
        ('remove', "Delete Existing Constraints", "Delete existing binding constraints")
        ],
        name="Policy",
        description="Action to take with existing constraints",
        default='skip'
        )

    bind_floating: BoolProperty(name="Bind Floating",
                                description="Always bind unparented bones Location and Rotation",
                                default=True)

    root_motion_bone: StringProperty(name="Root Motion Target",
                                     description="Root Motion of the  Target",
                                     default="")

    root_motion_bone_sr: StringProperty(name="Root Motion Source",
                                     description="Root Motion of the Source",
                                     default="")

    root_cp_loc_x: BoolProperty(name="Root Copy Loc X", description="Copy Root X Location", default=True)
    root_cp_loc_y: BoolProperty(name="Root Copy Loc y", description="Copy Root Y Location", default=True)
    root_cp_loc_z: BoolProperty(name="Root Copy Loc Z", description="Copy Root Z Location", default=False)

    root_use_loc_min_x: BoolProperty(name="Use Root Min X", description="Use Minimum Root X Location", default=False)
    root_use_loc_min_y: BoolProperty(name="Use Root Min Y", description="Use Minimum Root Y Location", default=False)
    root_use_loc_min_z: BoolProperty(name="Use Root Min Z", description="Use Minimum Root Z Location", default=False)

    root_loc_min_x: FloatProperty(name="Root Min X", description="Minimum Root X Location", default=0.0)
    root_loc_min_y: FloatProperty(name="Root Min Y", description="Minimum Root Y Location", default=0.0)
    root_loc_min_z: FloatProperty(name="Root Min Z", description="Minimum Root Z Location", default=0.0)

    root_use_loc_max_x: BoolProperty(name="Use Root Max X", description="Use Maximum Root X Location", default=False)
    root_use_loc_max_y: BoolProperty(name="Use Root Max Y", description="Use Maximum Root Y Location", default=False)
    root_use_loc_max_z: BoolProperty(name="Use Root Max Z", description="Use Maximum Root Z Location", default=False)

    root_loc_max_x: FloatProperty(name="Root Max X", description="Maximum Root X Location", default=0.0)
    root_loc_max_y: FloatProperty(name="Root Max Y", description="Maximum Root Y Location", default=0.0)
    root_loc_max_z: FloatProperty(name="Root Max Z", description="Maximum Root Z Location", default=0.0)

    root_cp_rot_x: BoolProperty(name="Root Copy Rot X", description="Copy Root X Rotation", default=False)
    root_cp_rot_y: BoolProperty(name="Root Copy Rot y", description="Copy Root Y Rotation", default=False)
    root_cp_rot_z: BoolProperty(name="Root Copy Rot Z", description="Copy Root Z Rotation", default=False)

    root_cp_scal_x: BoolProperty(name="Root Copy Scal X", description="Copy Root X Scale", default=False)
    root_cp_scal_y: BoolProperty(name="Root Copy Scal y", description="Copy Root Y Scale", default=False)
    root_cp_scal_z: BoolProperty(name="Root Copy Scal Z", description="Copy Root Z Scale", default=False)

    
    no_finger_loc: BoolProperty(default=False, name="No Finger Location")
    
    """prefix_separator: StringProperty(
        name="Prefix Separator",
        description="Separator between prefix and name, i.e: MyCharacter:head",
        default=":"
    )"""
      
    force_dialog: BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})
    
    _constrained_root = None

    _prop_indent = 0.15

    action_range: BoolProperty(name= "Action Range to Scene", 
                               description="Set Playback range to current action Start/End",
                               default=True)
    transfer_pose: BoolProperty(name= "Save The Pose", 
                                description="Apply the Constrain To save the Pose",
                                options={'SKIP_SAVE'},
                                default=False)
    custom_Frame: IntProperty(name="Frame", description="Select the Frame for {Save The Pose}", default=1)
    
    @property
    def _bind_constraints(self):
        constrs = []
        if self.loc_constraints:
            constrs.append('COPY_LOCATION')
        if self.rot_constraints:
            constrs.append('COPY_ROTATION')
        if self.scal_constraints:
            constrs.append('COPY_SCALE')

        return constrs

    @classmethod
    def poll(cls, context):
        
        if not context.active_object:
            return False
        if context.object.type != 'ARMATURE':
            return False
        
        if len(context.selected_objects) < 2:
            return False
        #At least 2 Armatures
        i = 0
        for ob in context.selected_objects:
            if ob.type == 'ARMATURE':
                i = i + 1
            if i >= 2:
                return True
        return False
    
    current_m = None

    def invoke(self, context, event):            
            
        self.current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')

        #init the custom_Frame
        self.custom_Frame = context.scene.frame_current            
        
        # Set to use current Retarget settings if found
        to_bind = next(ob for ob in context.selected_objects if ob != context.active_object and ob.type == 'ARMATURE')

        if not self.src_preset and to_bind.data.retarget_retarget.has_settings():
            self.src_preset = '--Current--'
        if not self.trg_preset and context.active_object.data.retarget_retarget.has_settings():
            self.trg_preset = '--Current--'

        if self.root_motion_bone and not self.root_motion_bone in context.active_object.pose.bones:
            self.root_motion_bone = ""
        
        if self.root_motion_bone_sr and not self.root_motion_bone_sr in to_bind.pose.bones:
            self.root_motion_bone_sr = ""

        if self.fit_target_scale_s and not self.fit_target_scale_s in to_bind.pose.bones:
            self.fit_target_scale_s = ""

        if self.force_dialog:
            return context.window_manager.invoke_props_dialog(self)

        return self.execute(context)        

    def draw(self, context):

        layout = self.layout
        column = layout.column()

        row = column.row()
        row.prop(self, 'same_bone_names')

        if not self.same_bone_names:

            row = column.row()
            row.prop(self, 'src_preset', text="To Bind")
        
            row = column.row()
            row.prop(self, 'trg_preset', text="Bind To")
        

        if self.force_dialog:
            return
        
        sr_ob = None
        for ob in context.selected_objects:
            if ob.type == 'ARMATURE' and ob != context.active_object:
                sr_ob = ob
                break

         #ik bone
        if self.same_bone_names:

            row = column.row()
            row.label(text="")

            row = column.row()
            row.prop(self, 'detect_ik_bones')

            row = column.split(factor=0.80, align=True)

            
            if sr_ob:
                row.prop_search(self, 'ik_bones',
                            sr_ob.data,
                            "bones")
                row.prop(self, 'clean_all', toggle=True, icon='PANEL_CLOSE')
                row.prop(self, 'clean_last',toggle=True, icon='TRACKING_CLEAR_BACKWARDS')

            i = 0
            row = column.split(factor=0.25, align=True)

            for ik in self.ik_collection:
                if i == 3:
                    row = column.split(factor=0.25, align=True)
                    i = 0
                
                row.label(text= ik, icon='BONE_DATA')
                i += 1


        column.separator()
        row = column.row()
        row.label(text='Conversion')

        row = column.split(factor=self._prop_indent, align=True)
        row.separator()
        col = row.column()
        col.prop(self, 'match_transform', text='')

        if not self.same_bone_names:
            col.prop(self, 'match_object_transform')
        else:
            col.prop(self, 'match_object_transform_s')


        if self.same_bone_names and sr_ob != None:
            col.prop_search(self, 'fit_target_scale_s',
                        sr_ob.data,
                        "bones", text="Fit height")
            
        else:
            col.prop(self, 'fit_target_scale')

        if (self.fit_target_scale != "--" and not self.same_bone_names) or (self.same_bone_names and self.fit_target_scale_s):
            col.prop(self, 'adjust_location')

        if not self.loc_constraints and self.match_transform == 'Bone':
            col.label(text="'Copy Location' might be required", icon='ERROR')
        elif ((self.fit_target_scale == '--' and not self.same_bone_names) or (self.same_bone_names and not self.fit_target_scale_s)) and self.match_transform == 'Pose':
            col.label(text="'Fit height' might improve results", icon='ERROR')
        else:
            col.separator()

        column.separator()
        row = column.row()
        row.label(text='Constraints')

        row = column.row()
        row = column.split(factor=self._prop_indent, align=True)
        row.separator()

        constr_col = row.column()

        copy_loc_row = constr_col.row()
        copy_loc_row.prop(self, 'loc_constraints')
        if self.loc_constraints and  not self.same_bone_names:
            copy_loc_row.prop(self, 'no_finger_loc', text="Except Fingers")
        elif not self.same_bone_names:
            copy_loc_row.prop(self, 'bind_floating')
        
        if self.same_bone_names and not self.loc_constraints:
            copy_loc_row.prop(self, 'bind_floating')
        
        copy_rot_row = constr_col.row()
        copy_rot_row.prop(self, 'rot_constraints')

        copy_rot_row = constr_col.row()
        copy_rot_row.prop(self, 'scal_constraints')

        if not self.same_bone_names:
            copy_rot_row.prop(self, 'math_look_at')

        if not self.same_bone_names:
            ik_aim_row = constr_col.row()
            ik_aim_row.prop(self, 'copy_IK_roll_hands')
            ik_aim_row.prop(self, 'copy_IK_roll_feet')

        row = column.split(factor=self._prop_indent, align=True)
        constr_col.prop(self, 'constraint_policy', text='')
        
        column.separator()
        row = column.row()
        row.label(text="Affect Bones")
        
        row = column.row()
    
        col = row.column()
        col.prop(self, 'only_animated_Bone')
        col = row.column()
        col.prop(self, 'only_selected')

        row = column.row()
        row.prop(self, 'bind_by_name', text="Also by Name")
        if self.bind_by_name:
            row = column.row()
            col = row.column()
            col.label(text="Prefix")
            col.prop(self, 'name_prefix', text="")

            col = row.column()
            col.label(text="Replace:")
            col.prop(self, 'name_replace', text="")

            col = row.column()
            col.label(text="With:")
            col.prop(self, 'name_replace_with', text="")

            col = row.column()
            col.label(text="Suffix:")
            col.prop(self, 'name_suffix', text="")

        column.separator()
        row = column.row()
        row.label(text="Root Animation")
        row = column.split(factor=self._prop_indent, align=True)
        row.separator()
        row.prop(self, 'constrain_root', text="")


        if self.constrain_root != 'None' and self.constrain_root != 'Object' and sr_ob != None:
            row = column.split(factor=self._prop_indent, align=True)
            row.label(text="")
            row.prop_search(self, 'root_motion_bone_sr',
                            sr_ob.data,
                            "bones", text="")
            
        if self.constrain_root != 'None':
            row = column.split(factor=self._prop_indent, align=True)
            row.label(text="")
            row.prop_search(self, 'root_motion_bone',
                            context.active_object.data,
                            "bones", text="")

        if self.constrain_root != 'None':
            row = column.row(align=True)
            row.label(text="Location")
            row.prop(self, "root_cp_loc_x", text="X", toggle=True)
            row.prop(self, "root_cp_loc_y", text="Y", toggle=True)
            row.prop(self, "root_cp_loc_z", text="Z", toggle=True)

            if any((self.root_cp_loc_x, self.root_cp_loc_y, self.root_cp_loc_z)):
                column.separator()

                # Min/Max X
                if self.root_cp_loc_x:
                    row = column.row(align=True)
                    row.prop(self, "root_use_loc_min_x", text="Min X")

                    subcol = row.column()
                    subcol.prop(self, "root_loc_min_x", text="")
                    subcol.enabled = self.root_use_loc_min_x

                    row.separator()
                    row.prop(self, "root_use_loc_max_x", text="Max X")
                    subcol = row.column()
                    subcol.prop(self, "root_loc_max_x", text="")
                    subcol.enabled = self.root_use_loc_max_x
                    row.enabled = self.root_cp_loc_x

                # Min/Max Y
                if self.root_cp_loc_y:
                    row = column.row(align=True)
                    row.prop(self, "root_use_loc_min_y", text="Min Y")

                    subcol = row.column()
                    subcol.prop(self, "root_loc_min_y", text="")
                    subcol.enabled = self.root_use_loc_min_y

                    row.separator()
                    row.prop(self, "root_use_loc_max_y", text="Max Y")
                    subcol = row.column()
                    subcol.prop(self, "root_loc_max_y", text="")
                    subcol.enabled = self.root_use_loc_max_y
                    row.enabled = self.root_cp_loc_y

                # Min/Max Z
                if self.root_cp_loc_z:
                    row = column.row(align=True)
                    row.prop(self, "root_use_loc_min_z", text="Min Z")

                    subcol = row.column()
                    subcol.prop(self, "root_loc_min_z", text="")
                    subcol.enabled = self.root_use_loc_min_z

                    row.separator()
                    row.prop(self, "root_use_loc_max_z", text="Max Z")
                    subcol = row.column()
                    subcol.prop(self, "root_loc_max_z", text="")
                    subcol.enabled = self.root_use_loc_max_z
                    row.enabled = self.root_cp_loc_z

                column.separator()

            row = column.row(align=True)
            row.label(text="Rotation")
            row.prop(self, "root_cp_rot_x", text="X", toggle=True)
            row.prop(self, "root_cp_rot_y", text="Y", toggle=True)
            row.prop(self, "root_cp_rot_z", text="Z", toggle=True)

            row = column.row(align=True)
            row.label(text="Scale")
            row.prop(self, "root_cp_scal_x", text="X", toggle=True)
            row.prop(self, "root_cp_scal_y", text="Y", toggle=True)
            row.prop(self, "root_cp_scal_z", text="Z", toggle=True)

        column.separator()
        row = column.row()
        row.prop(self, 'ret_bones_collection', text="Layer")
        
        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "action_range", toggle=True, icon='PREVIEW_RANGE')
        
        row = column.split(factor=0.5, align=True)
        row.prop(self, "custom_Frame", text="Frame")
        row.prop(self, "transfer_pose", toggle=True, icon='ARMATURE_DATA')


    def _bone_bound_already(self, bone):
        for constr in bone.constraints:
            if constr.type in self._bind_constraints:
                return True

        return False

    def _add_limit_constraintss(self, ob, rot=True, loc=True, scale=False):
        limit_constraints = []
        if self.match_transform == 'Pose':
            return limit_constraints

        if rot:
            limit_rot = ob.constraints.new('LIMIT_ROTATION')
            limit_rot.use_limit_x = True
            limit_rot.use_limit_y = True
            limit_rot.use_limit_z = True

            limit_constraints.append(limit_rot)

        def limit_all(constr):
            constr.use_min_x = True
            constr.use_min_y = True
            constr.use_min_z = True
            constr.use_max_x = True
            constr.use_max_y = True
            constr.use_max_z = True

        if loc:
            limit_loc = ob.constraints.new('LIMIT_LOCATION')
            limit_all(limit_loc)
            limit_constraints.append(limit_loc)

        if scale:
            limit_scale = ob.constraints.new('LIMIT_SCALE')
            limit_scale.min_x = 1.0
            limit_scale.min_y = 1.0
            limit_scale.min_z = 1.0
            
            limit_scale.max_x = 1.0
            limit_scale.max_y = 1.0
            limit_scale.max_z = 1.0

            limit_all(limit_scale)
            limit_constraints.append(limit_scale)

        return limit_constraints

    def execute(self, context):

        bpy.ops.object.mode_set(mode='POSE')

        if self.action_range and context.active_object.animation_data and context.active_object.animation_data.action:
            bpy.ops.object.retarget_action_to_range()

        context.scene.frame_current = self.custom_Frame
        # force_dialog limits drawn properties and is no longer required
        self.force_dialog = False

         #// update value ik bones
        if self.same_bone_names:

            if self.clean_all:
                if len(self.ik_collection) > 0 :
                    self.ik_collection.clear()
                self.clean_all = False
                
            if self.clean_last:
                if len(self.ik_collection) > 0 :
                    self.ik_collection.pop()
                self.clean_last = False

            if self.ik_bones:
                if not self.ik_bones in self.ik_collection:
                    self.ik_collection.append(self.ik_bones)
                self.ik_bones = ""

        trg_ob = context.active_object

        if not self.same_bone_names:

            if self.trg_preset == '--':
                bpy.ops.object.mode_set(mode=self.current_m)
                return {'FINISHED'}
            
            if self.src_preset == '--':
                bpy.ops.object.mode_set(mode=self.current_m)
                return {'FINISHED'}
            


            if self.trg_preset == '--Current--' and trg_ob.data.retarget_retarget.has_settings():
                trg_settings = trg_ob.data.retarget_retarget
                trg_skeleton = preset_handler.get_settings_skel(trg_settings)
            else:
                trg_skeleton = preset_handler.set_preset_skel(self.trg_preset, context)

                if not trg_skeleton:
                    bpy.ops.object.mode_set(mode=self.current_m)
                    return {'FINISHED'}

        cp_suffix = 'RET'
        prefix = ""

        fit_scale = False

        if self.same_bone_names:

            if self.fit_target_scale_s:
                try:
                    trg_bone = trg_ob.pose.bones[self.fit_target_scale_s]
                except KeyError:
                    pass
                else:
                    fit_scale = True
                    trg_height = (trg_ob.matrix_world @ trg_bone.bone.head_local)
        else:

            if self.fit_target_scale != '--':
                    
                try:
                    trg_bone = trg_ob.pose.bones[getattr(trg_skeleton.spine, self.fit_target_scale)]
                except KeyError:
                    pass
                else:
                    fit_scale = True
                    trg_height = (trg_ob.matrix_world @ trg_bone.bone.head_local)
        
        armatures = context.selected_objects

        for ob in armatures:
            if ob == trg_ob:
                continue
            
            if ob.type != 'ARMATURE':
                continue
            
           
            if not self.same_bone_names:
                src_settings = ob.data.retarget_retarget
                if self.src_preset == '--Current--' and ob.data.retarget_retarget.has_settings():    
                    if not src_settings.has_settings():
                        continue
                    src_skeleton = preset_handler.get_settings_skel(src_settings)
                else:
                    src_skeleton = preset_handler.get_preset_skel(self.src_preset, src_settings)
                    
                if not src_skeleton:
                    continue
                
                if  src_skeleton.root:
                    root_prefix = ""
                     # root prefix
                    for bone in ob.pose.bones:
                        if ":" in bone.name and ":" not in src_skeleton.root:
                            root_prefix = bone.name.split(":")[0] + ":"
                        break
                    src_skeleton.root = root_prefix + src_skeleton.root
                    root = src_skeleton.root
            
                else:
                    root = ""
                   
            else:
                root = ""
            
                #find root bone 
                root_bone = None
                for bone in ob.pose.bones:
                    root_bone = bone
                    break
            

            if fit_scale:

                try:
                    if self.same_bone_names:
                        ob_height = (ob.matrix_world @ ob.pose.bones[self.fit_target_scale_s].bone.head_local)
                    else:
                        ob_height = (ob.matrix_world @ ob.pose.bones[getattr(src_skeleton.spine, self.fit_target_scale)].bone.head_local)
                    height_ratio = ob_height[2] / trg_height[2]
                    
                    #mute_fcurves(trg_ob, 'scale')
                    trg_ob.scale *= height_ratio
                    #limit_scale(trg_ob)

                    if self.adjust_location:
                        # scale location animation to avoid offset
                        trg_action = trg_ob.animation_data.action
                        if trg_action:
                            for slot in trg_action.slots:

                                if slot.target_id_type != 'OBJECT':
                                    continue
                                if not  (trg_ob in slot.users() ):
                                    continue

                                channelbag = anim_utils.action_get_channelbag_for_slot(trg_action, slot)
                                #TODO: i need to check this 
                                if not (trg_ob in slot.users() ):
                                    continue
                                for fc in channelbag.fcurves:
                                    data_path = fc.data_path

                                    if not data_path.endswith('location'):
                                        continue

                                    for kf in fc.keyframe_points:
                                        kf.co[1] /= height_ratio
                except KeyError:
                    pass

            bone_names_map = dict()

           
            if self.same_bone_names:
                
                for bone in ob.pose.bones:

                    try:
                        pb = trg_ob.pose.bones[bone.name]
                    except KeyError:
                        continue
                        
                    if not bone_utils.is_pose_bone_all_locked(bone):
                        bone_names_map[bone.name] = bone.name
            else:
                bone_names_map = src_skeleton.conversion_map(trg_skeleton)


            if not self.same_bone_names:
                def_skeleton = preset_handler.get_preset_skel(src_settings.deform_preset)
                if def_skeleton:
                    deformation_map = src_skeleton.conversion_map(def_skeleton)
                else:
                    deformation_map = None
            else:
                deformation_map = None

            if self.bind_by_name:
                # Look for bones present in both
                for bone in ob.pose.bones:
                    bone_name = bone.name
                    bone_look_up = self.name_prefix + bone_name.replace(self.name_replace, self.name_replace_with) + self.name_suffix
                    
                    if bone_look_up in bone_names_map:
                        continue
                    if bone_utils.is_pose_bone_all_locked(bone):
                        continue
                    if bone_look_up in trg_ob.pose.bones:
                        bone_names_map[bone_name] = bone_look_up

            look_ats = {}
            self._constrained_root = None
            
            if self.constrain_root == 'None':

                if not self.same_bone_names:
                    try:
                        del bone_names_map[root]
                    except KeyError:
                        pass
                

            elif self.constrain_root == 'Bone':

                if self.root_motion_bone_sr:
                    if root in bone_names_map.keys():
                        bone_names_map.pop(root)
                    root = self.root_motion_bone_sr
                    
                bone_names_map[root] = self.root_motion_bone 


            # only_animated_Bone -------------------------------
            trg_action = trg_ob.animation_data.action if trg_ob.animation_data and trg_ob.animation_data.action else None
            channelbag = None
            if trg_action:
                for slot in trg_action.slots:

                    if slot.target_id_type != 'OBJECT':
                        continue
                    if not  (trg_ob in slot.users() ):
                        continue
                    channelbag = anim_utils.action_get_channelbag_for_slot(trg_action, slot)
                    break

            if self.only_animated_Bone:
                if channelbag:

                    to_del = [] 
                    for key_b_name, b_name in bone_names_map.items():
                        if not key_b_name:
                            continue

                        if not b_name in channelbag.groups:
                            to_del.append(key_b_name)
                            

                    for name in to_del:
                        del bone_names_map[name]

                else:
                    bone_names_map.clear()
            #--------------
        
            if self.only_selected:
                b_names = list(bone_names_map.keys())
                for b_name in b_names:
                    if not b_name:
                        continue
                    try:
                        bone = ob.pose.bones[b_name]
                    except KeyError:
                        continue

                    if not bone.select:
                        del bone_names_map[b_name]

            # hacky, but will do it: keep target armature in place during binding
            limit_constraints = self._add_limit_constraintss(trg_ob)
            
            try:
                ret_collection = trg_ob.data.collections[self.ret_bones_collection]
            except KeyError:
                ret_collection = trg_ob.data.collections.new(self.ret_bones_collection)
                ret_collection.is_visible = False

            # create Retarget bones
            bpy.ops.object.mode_set(mode='EDIT')
            for src_name, trg_name in bone_names_map.items():
                if not src_name:
                    continue

                if self.constraint_policy == 'skip':
                    try:
                        pb = ob.pose.bones[src_name]
                    except KeyError:
                        pass
                    else:
                        if self._bone_bound_already(pb):
                            continue

                is_object_root = src_name == root and self.constrain_root == 'Object'
                if not trg_name and not is_object_root:
                    continue

                trg_name = str(prefix) + str(trg_name)

                new_bone_name = bone_utils.copy_bone_to_arm(ob, trg_ob, src_name, suffix=cp_suffix)
                if not new_bone_name:
                    continue
                try:
                    new_parent = trg_ob.data.edit_bones[trg_name]
                except KeyError:
                    if is_object_root:
                        new_parent = None
                    else:
                        self.report({'WARNING'}, f"{trg_name} not found in target")
                        continue

                new_bone = trg_ob.data.edit_bones[new_bone_name]
                new_bone.parent = new_parent

                if self.match_transform == 'Bone':
                    # counter deformation bone transform

                    if deformation_map:
                        try:
                            def_bone = ob.data.edit_bones[deformation_map[src_name]]
                        except KeyError:
                            def_bone = ob.data.edit_bones[src_name]
                    else:
                        def_bone = ob.data.edit_bones[src_name]

                    try:
                        trg_ed_bone = trg_ob.data.edit_bones[trg_name]
                    except KeyError:
                        continue

                    new_bone.transform(def_bone.matrix.inverted())

                    # even transform
                    if not self.same_bone_names:
                        if self.match_object_transform:
                            new_bone.transform(ob.matrix_world)
                    elif self.match_object_transform_s:
                        new_bone.transform(ob.matrix_world)
                    # counter target transform
                    new_bone.transform(trg_ob.matrix_world.inverted())
                    
                    # align target temporarily
                    trg_roll = trg_ed_bone.roll
                    trg_ed_bone.roll = bone_utils.ebone_roll_to_vector(trg_ed_bone, def_bone.z_axis)

                    # bring under trg_bone
                    new_bone.transform(trg_ed_bone.matrix)

                    # restore target orient
                    trg_ed_bone.roll = trg_roll

                    new_bone.roll = bone_utils.ebone_roll_to_vector(trg_ed_bone, def_bone.z_axis)
                elif self.match_transform == 'Pose':
                    new_bone.matrix = ob.pose.bones[src_name].matrix
                    if not self.same_bone_names:
                        if self.match_object_transform:
                            new_bone.transform(ob.matrix_world)
                    elif self.match_object_transform_s:
                        new_bone.transform(ob.matrix_world)
                    new_bone.transform(trg_ob.matrix_world.inverted_safe())
                elif self.match_transform == 'World':
                    new_bone.head = new_bone.parent.head
                    new_bone.tail = new_bone.parent.tail
                    new_bone.roll = new_bone.parent.roll
                    if not self.same_bone_names:
                        if self.match_object_transform:
                            new_bone.transform(ob.matrix_world)
                    elif self.match_object_transform_s:
                        new_bone.transform(ob.matrix_world)
                else:
                    src_bone = ob.data.bones[src_name]
                    src_z_axis_neg = Vector((0.0, 0.0, 1.0)) @ src_bone.matrix_local.inverted().to_3x3()
                    src_z_axis_neg.normalize()

                    new_bone.roll = bone_utils.ebone_roll_to_vector(new_bone, src_z_axis_neg)

                    if not self.same_bone_names:
                        if self.match_object_transform:
                            new_bone.transform(ob.matrix_world)
                            new_bone.transform(trg_ob.matrix_world.inverted())
                    elif self.match_object_transform_s:
                        new_bone.transform(ob.matrix_world)
                        new_bone.transform(trg_ob.matrix_world.inverted())

                if not self.same_bone_names:
                    if self.copy_IK_roll_hands:
                        if src_name in (src_skeleton.right_arm_ik.hand,
                                        src_skeleton.left_arm_ik.hand):

                            src_ik = ob.data.bones[src_name]
                            new_bone.roll = bone_utils.ebone_roll_to_vector(new_bone, src_ik.z_axis)
                    if self.copy_IK_roll_feet:
                        if src_name in (src_skeleton.left_leg_ik.foot,
                                        src_skeleton.right_leg_ik.foot):

                            src_ik = ob.data.bones[src_name]
                            new_bone.roll = bone_utils.ebone_roll_to_vector(new_bone, src_ik.z_axis)

            
                for coll in new_bone.collections:
                    coll.unassign(new_bone)
                ret_collection.assign(new_bone)

                if not self.same_bone_names:
                    if self.math_look_at:
                        if src_name == src_skeleton.right_arm_ik.arm:
                            start_bone_name = trg_skeleton.right_arm_ik.forearm
                        elif src_name == src_skeleton.left_arm_ik.arm:
                            start_bone_name = trg_skeleton.left_arm_ik.forearm
                        elif src_name == src_skeleton.right_leg_ik.upleg:
                            start_bone_name = trg_skeleton.right_leg_ik.leg
                        elif src_name == src_skeleton.left_leg_ik.upleg:
                            start_bone_name = trg_skeleton.left_leg_ik.leg
                        else:
                            start_bone_name = ""

                        if start_bone_name:
                            start_bone = trg_ob.data.edit_bones[prefix + start_bone_name]

                            look_bone = trg_ob.data.edit_bones.new(start_bone_name + '_LOOK')
                            look_bone.head = start_bone.head
                            look_bone.tail = 2 * start_bone.head - start_bone.tail
                            look_bone.parent = start_bone

                            look_ats[src_name] = look_bone.name

                            for coll in look_bone.collections:
                                coll.unissign(look_bone)
                            ret_collection.assign(look_bone)
                        
            for constr in limit_constraints:
                trg_ob.constraints.remove(constr)

            bpy.ops.object.mode_set(mode='POSE')

            for src_name, trg_name in look_ats.items():
                ret_bone = trg_ob.pose.bones[f'{src_name}_{cp_suffix}']
                constr = ret_bone.constraints.new(type='LOCKED_TRACK')

                constr.head_tail = 1.0
                constr.target = trg_ob
                constr.subtarget = trg_name
                constr.lock_axis = 'LOCK_Y'
                constr.track_axis = 'TRACK_NEGATIVE_Z'

            if not self.same_bone_names:
                left_finger_bones = list(chain(*src_skeleton.left_fingers.values()))
                right_finger_bones = list(chain(*src_skeleton.right_fingers.values()))

            for src_name in bone_names_map.keys():
                if not src_name:
                    continue
                if src_name == root:
                    if self.constrain_root == "None":
                        continue
                    if self.constrain_root == "Bone" and (not self.root_motion_bone or not self.root_motion_bone_sr):
                        continue
                try:
                    src_pbone = ob.pose.bones[src_name]

                except KeyError:
                    continue

                if self._bone_bound_already(src_pbone):
                    if self.constraint_policy == 'skip':
                       continue
                    
                    if self.constraint_policy == 'disable':
                        for constr in src_pbone.constraints:
                            if constr.type in self._bind_constraints:
                                constr.mute = True
                    elif self.constraint_policy == 'remove':
                        for constr in reversed(src_pbone.constraints):
                            if constr.type in self._bind_constraints:
                                src_pbone.constraints.remove(constr)
                    # TODO: should unconstrain mid bones to!

                if not self.same_bone_names and not self.loc_constraints and self.bind_floating and is_bone_floating(src_pbone, src_skeleton.spine.hips):
                    if self.scal_constraints:
                        constr_types = ['COPY_LOCATION', 'COPY_ROTATION', 'COPY_SCALE']
                    else:
                        constr_types = ['COPY_LOCATION', 'COPY_ROTATION']
                
                elif not self.same_bone_names and self.no_finger_loc and (src_name in left_finger_bones or src_name in right_finger_bones):
                    if self.scal_constraints:
                        constr_types = ['COPY_ROTATION', 'COPY_SCALE']
                    else:
                        constr_types = ['COPY_ROTATION']
                else:
                    if self.same_bone_names and (src_name in self.ik_collection or self.detect_ik_bones and "ik" in src_name):
                        if self.scal_constraints:
                            constr_types = ['COPY_LOCATION', 'COPY_ROTATION','COPY_SCALE']
                        else:
                            constr_types = ['COPY_LOCATION', 'COPY_ROTATION']
                    elif self.same_bone_names and not self.loc_constraints and self.bind_floating and is_bone_floating(src_pbone, root_bone.name):
                        if self.scal_constraints:
                            constr_types = ['COPY_LOCATION', 'COPY_ROTATION','COPY_SCALE']
                        else:
                            constr_types = ['COPY_LOCATION', 'COPY_ROTATION']
                    else:
                        constr_types = self._bind_constraints

                subtarget_name = f'{src_name}_{cp_suffix}'

                if subtarget_name in trg_ob.data.bones:

                    for constr_type in constr_types:
                        constr = src_pbone.constraints.new(type=constr_type)
                        constr.target = trg_ob
                        constr.subtarget = subtarget_name

                    #//shape
                    new_ob_bone = trg_ob.pose.bones[subtarget_name]
                    new_ob_bone.custom_shape = src_pbone.custom_shape
                    new_ob_bone.custom_shape_transform = src_pbone.custom_shape_transform
                    new_ob_bone.custom_shape_rotation_euler = src_pbone.custom_shape_rotation_euler
                    new_ob_bone.custom_shape_scale_xyz = src_pbone.custom_shape_scale_xyz
                    new_ob_bone.custom_shape_translation = src_pbone.custom_shape_translation
                    new_ob_bone.custom_shape_wire_width = src_pbone.custom_shape_wire_width
                    new_ob_bone.color.palette = src_pbone.color.palette
                    new_ob_bone.color.custom.normal = src_pbone.color.custom.normal
                    new_ob_bone.color.custom.select = src_pbone.color.custom.select 
                    new_ob_bone.color.custom.active = src_pbone.color.custom.active

                if self.constrain_root == 'Bone' and src_name == root:
                    self._constrained_root = src_pbone

            if self.constrain_root == 'Object' and self.root_motion_bone:
                constr_types = ['COPY_LOCATION']
                if any([self.root_cp_rot_x, self.root_cp_rot_y, self.root_cp_rot_z]):
                    constr_types.append('COPY_ROTATION')
                if any([self.root_cp_scal_x, self.root_cp_scal_y, self.root_cp_scal_z]):
                    constr_types.append('COPY_SCALE')
                for constr_type in constr_types:
                    constr = ob.constraints.new(type=constr_type)
                    constr.target = trg_ob

                    constr.subtarget = self.root_motion_bone

                self._constrained_root = ob

            if self._constrained_root and self.root_motion_bone:
                
                constr = None
                loc_constr = None
                for cons in reversed(self._constrained_root.constraints):
                    if cons.type == 'LIMIT_LOCATION':
                        constr = cons
                    if cons.type == 'COPY_LOCATION':
                        loc_constr = cons

                #create a contraint if not found
                if not loc_constr:
                    loc_constr = self._constrained_root.constraints.new('COPY_LOCATION')
                    loc_constr.target = trg_ob

                    loc_constr.subtarget = self.root_motion_bone

                if not constr:
                    constr = self._constrained_root.constraints.new('LIMIT_LOCATION')
                
                constr.use_min_x = self.root_use_loc_min_x or not self.root_cp_loc_x
                constr.use_min_y = self.root_use_loc_min_y or not self.root_cp_loc_y
                constr.use_min_z = self.root_use_loc_min_z or not self.root_cp_loc_z

                constr.use_max_x = self.root_use_loc_max_x or not self.root_cp_loc_x
                constr.use_max_y = self.root_use_loc_max_y or not self.root_cp_loc_y
                constr.use_max_z = self.root_use_loc_max_z or not self.root_cp_loc_z

                constr.min_x = self.root_loc_min_x if self.root_cp_loc_x and self.root_use_loc_min_x else 0.0
                constr.min_y = self.root_loc_min_y if self.root_cp_loc_y and self.root_use_loc_min_y else 0.0
                constr.min_z = self.root_loc_min_z if self.root_cp_loc_z and self.root_use_loc_min_z else 0.0

                constr.max_x = self.root_loc_max_x if self.root_cp_loc_x and self.root_use_loc_max_x else 0.0
                constr.max_y = self.root_loc_max_y if self.root_cp_loc_y and self.root_use_loc_max_y else 0.0
                constr.max_z = self.root_loc_max_z if self.root_cp_loc_z and self.root_use_loc_max_z else 0.0

            if self._constrained_root and self.root_motion_bone:
                constr = None
                for cons in reversed(self._constrained_root.constraints):
                    if cons.type == 'COPY_ROTATION':
                        constr = cons
                        break
                if not constr:
                    constr = self._constrained_root.constraints.new('COPY_ROTATION')
                    constr.target = trg_ob

                    constr.subtarget = self.root_motion_bone

                constr.use_x = self.root_cp_rot_x
                constr.use_y = self.root_cp_rot_y
                constr.use_z = self.root_cp_rot_z
            
            if self._constrained_root and self.root_motion_bone:
                constr = None
                for cons in reversed(self._constrained_root.constraints):
                    if cons.type == 'COPY_SCALE':
                        constr = cons
                        break
                if constr or any((self.root_cp_scal_x, self.root_cp_scal_y, self.root_cp_scal_z)):
                    
                    if not constr:

                        constr = self._constrained_root.constraints.new('COPY_SCALE')
                        constr.target = trg_ob

                        constr.subtarget = self.root_motion_bone
                
                    constr.use_x = self.root_cp_scal_x
                    constr.use_y = self.root_cp_scal_y
                    constr.use_z = self.root_cp_scal_z
            
            if self.transfer_pose:
                constr_bone_names = []

                for pb in bone_utils.get_constrained_controls(ob, unselect=True, use_deform= True):
                
                    if pb.name + "_RET" in trg_ob.data.bones:
                        pb.select = True
                        constr_bone_names.append(pb.name)
                
                bpy.ops.object.mode_set(mode= 'OBJECT')
                context.view_layer.objects.active = ob
                bpy.ops.object.mode_set(mode= 'POSE')

                # apply Constraints
                for bone_name in constr_bone_names:
                    try:
                        pbone = ob.pose.bones[bone_name]
                    except KeyError:
                        continue
                    ob.data.bones.active = pbone.bone
                    pbone.select = True

                    for constr in reversed(pbone.constraints):  
                        bpy.ops.constraint.apply(constraint = constr.name, owner = 'BONE')
                
                # delete bone collection
    
                bones_to_delete = [bone.name for bone in trg_ob.pose.bones if bone.name in ret_collection.bones]

                context.view_layer.objects.active = trg_ob
                bpy.ops.object.mode_set(mode='EDIT')
                
                for bone_name in bones_to_delete:
                    
                    if bone_name in trg_ob.data.edit_bones:
                        trg_ob.data.edit_bones.remove(trg_ob.data.edit_bones[bone_name])

                trg_ob.data.collections.remove(ret_collection)

        bpy.ops.object.mode_set(mode= self.current_m)
        return {'FINISHED'}


def validate_actions(action: bpy.types.Action, path_resolve: callable):

    valid = 0
    for slot in action.slots:

        if slot.target_id_type != 'OBJECT':
            continue

        channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)

        for fc in channelbag.fcurves:
            data_path = fc.data_path
            if fc.array_index:
                data_path = data_path + "[%d]" % fc.array_index
            try:
                path_resolve(data_path)
                valid = valid + 1
            except ValueError:
                continue  # Invalid.
    return valid > 0  # Valid.


class BakeConstrainedActions(Operator):
    bl_idname = "armature.retarget_bake_constrained_actions"
    bl_label = "Bake Constrained Actions"
    bl_description = "Bake Actions constrained from another Armature. No need to select two armatures"
    bl_options = {'REGISTER', 'UNDO'}

    clear_users_old: BoolProperty(name="Clear original Action Users",
                                  default=False)

    fake_user_new: BoolProperty(name="Save New Action User",
                                default=True)
    
    bake_similar:BoolProperty(name="Include Similar Action",
                              description="i.e: if you have 5 Mixamo animations(actions) and you bind your armature to one of them, this feature will bake these 5 actions in one go",
                                default=False)
    
    exclude_deform:BoolProperty(name="Exclude deform bones", default=False)

    del_const:BoolProperty(name="Delete Constraint", default=True)

    del_col:BoolProperty(name="Delete Retarget Collection", 
                         description="Delete Retarget Collection (AND ALL THE BONES INSIDE) ",
                         default=True)

    col_name:StringProperty(name = "Name", description="Name of the Collection", default="Retarget Bones")

    do_bake: BoolProperty(name="  BAKE  ", description="Bake driven motion and exit",
                          default=False, options={'SKIP_SAVE'})

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        test = True
        for to_bake in context.selected_objects:
            if to_bake.type != 'ARMATURE':
                continue
            trg_ob = self.get_trg_ob(to_bake)
            if not trg_ob:
                continue
            if not trg_ob.animation_data and not trg_ob.animation_data.action:
                continue
            test = False
            column.label(text=f"Baking from {trg_ob.name} to {to_bake.name}")

        if test:
            row = column.split(factor=0.30, align=True)
            row.label(text="")
            row.label(text="NO CONSTRAIN FOUND", icon='ERROR')
        #if len(context.selected_objects) > 1:
            #column.label(text="No need to select two Armatures anymore", icon='ERROR')

        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "clear_users_old")

        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "fake_user_new")
        
        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "bake_similar")

        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "exclude_deform")

        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "del_const")

        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "del_col")

        if self.del_col:
            row = column.split(factor=0.30, align=True)
            row.label(text="")
            row.prop(self, "col_name")

        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "do_bake", toggle=True)

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.object.type != 'ARMATURE':
            return False
        return True

    def get_trg_ob(self, ob: bpy.types.Object) -> bpy.types.Object:
        for pb in bone_utils.get_constrained_controls(armature_object=ob, use_deform=not self.exclude_deform):
            for constr in pb.constraints:
                try:
                    subtarget = constr.subtarget
                except AttributeError:
                    continue

                if subtarget.endswith("_RET"):
                    return(constr.target)
        return None

    def execute(self, context):

        current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')

        if not self.do_bake:
            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}
        sel_obs = list(context.selected_objects)

        target_list = []
        constr_bone_names = []

        for ob in sel_obs:
            if ob.type != 'ARMATURE':
                continue

            trg_ob = self.get_trg_ob(ob)
            
            if not trg_ob:
                continue

            context.view_layer.objects.active = ob
            
            for pb in bone_utils.get_constrained_controls(ob, unselect=True, use_deform=not self.exclude_deform):
                
                if pb.name + "_RET" in trg_ob.data.bones:
                    pb.select = True
                    if pb.name not in constr_bone_names:
                        constr_bone_names.append(pb.name)

            actions = []

            if self.bake_similar:
                actions = list(bpy.data.actions)
            else:
                if trg_ob.animation_data and trg_ob.animation_data.action:
                    actions.append(trg_ob.animation_data.action)


            for action in actions:  # convert to list beforehand to avoid picking new actions
                if not action:
                    continue
                if not validate_actions(action, trg_ob.path_resolve):
                    continue

                trg_ob.animation_data.action = action
                fr_start, fr_end = action.frame_range
                bpy.ops.nla.bake(frame_start=int(fr_start), frame_end=int(fr_end),
                                 bake_types={'POSE'}, only_selected=True,
                                 visual_keying=True, clear_constraints=False)

                if not ob.animation_data or  not ob.animation_data.action:
                    self.report({'WARNING'}, f"failed to bake {action.name}")
                    continue
                
                ob.animation_data.action.use_fake_user = self.fake_user_new
                
                new_name = f"{ob.name}|{action.name}"

                ob.animation_data.action.name = new_name

                # find if there's constraint on object
                if len(ob.constraints) > 0:

                    ob.select_set(True)

                    bpy.ops.nla.bake(frame_start=int(fr_start), frame_end=int(fr_end),
                                 bake_types={'OBJECT'},
                                 visual_keying=True, clear_constraints=False, use_current_action=True)
                    
                    for slot in ob.animation_data.action.slots:
                        
                        if slot.target_id_type != 'OBJECT' and not (ob in slot.users() ):
                            continue

                        channelbag = anim_utils.action_get_channelbag_for_slot(ob.animation_data.action, slot)
                        new_group = channelbag.groups.new(f"{ob.name}|OBJECT")

                        for fc in channelbag.fcurves:
                            if not fc.group:
                               fc.group = new_group

                if not trg_ob.name in target_list:
                    target_list.append(trg_ob)

                if self.clear_users_old:
                    action.user_clear()

        # delete Constraints
        if self.del_const:
            for ob in sel_obs:
                if ob.type != 'ARMATURE':
                    continue
                ob.select_set(False)

                trg_ob = self.get_trg_ob(ob)
                
                if not trg_ob:
                    continue

                for constr in reversed(ob.constraints):
                        ob.constraints.remove(constr)

                for bone_name in constr_bone_names:
                    try:
                        pbone = ob.pose.bones[bone_name]
                    except KeyError:
                        continue
                    for constr in reversed(pbone.constraints):
                        pbone.constraints.remove(constr)

        else:
            self.del_col = False

        # delete collection
        if self.del_col:             
            
           
            active = context.active_object

            for ob in target_list:
                
                if ob.type != 'ARMATURE':
                    continue
                
                #check visibility
                view = False
                if ob.hide_viewport:
                    view = ob.hide_viewport
                    ob.hide_viewport = False

                if self.col_name in ob.data.collections:
                    ret_collection = ob.data.collections[self.col_name]
                    
                    bones_to_delete = [bone.name for bone in ob.pose.bones if bone.name in ret_collection.bones]

                    context.view_layer.objects.active = ob
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                    for bone_name in bones_to_delete:
                        if bone_name in ob.data.edit_bones:
                            ob.data.edit_bones.remove(ob.data.edit_bones[bone_name])

                    ob.data.collections.remove(ret_collection)

                   
                else:
                    self.report({'WARNING'}, f"bone collection {self.col_name} not found in {ob.name}")
            
                if view:
                    ob.hide_viewport = view

            context.view_layer.objects.active = active

        bpy.ops.object.mode_set(mode= current_m)

        return {'FINISHED'}

def is_bone_floating(bone, hips_bone_name):
    binding_constrs = ['COPY_LOCATION', 'COPY_ROTATION', 'COPY_TRANSFORMS']
    while bone.parent:
        if bone.parent.name == hips_bone_name:
            return False
        for constr in bone.constraints:
            if constr.type in binding_constrs:
                return False
        bone = bone.parent

    return True


def add_loc_key(bone, frame, options):
    bone.keyframe_insert('location', index=0, frame=frame, options=options)
    bone.keyframe_insert('location', index=1, frame=frame, options=options)
    bone.keyframe_insert('location', index=2, frame=frame, options=options)


def get_rot_ani_path(to_animate):
    if to_animate.rotation_mode == 'QUATERNION':
        return 'rotation_quaternion', 4
    if to_animate.rotation_mode == 'AXIS_ANGLE':
        return 'rotation_axis_angle', 4
    
    return 'rotation_euler', 3


def add_loc_rot_key(bone, frame, options):
    add_loc_key(bone, frame, options)

    mode, channels = get_rot_ani_path(bone)
    for i in range(channels):
        bone.keyframe_insert(mode, index=i, frame=frame, options=options)

def add_scal_key(bone, frame, options):
    bone.keyframe_insert('scale', index=0, frame=frame, options=options)
    bone.keyframe_insert('scale', index=1, frame=frame, options=options)
    bone.keyframe_insert('scale', index=2, frame=frame, options=options)

class AddRoot(Operator):

    bl_idname = "armature.retarget_add_root"
    bl_label = "Add Root Bone"
    bl_description = "Add Root Bone, (Apply the Rotation)"
    bl_options = {'REGISTER', 'UNDO'}

    rig_preset: EnumProperty(items=preset_handler.iterate_presets,
                             name="Target Preset")
    rig_preset_prev = None
    hips_bone: StringProperty(name="Hips_Bone",
                               default="",
                               options={'SKIP_SAVE'})
    
    root_name: StringProperty(name="Root Name",
                              description="'Root' is the recommended name, it will make it compatible with other features (it will automatically add the prefix if it's not specified)",
                                default="Root")
    
    addroot: BoolProperty(name="Add Root", default=True)

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.object.type != 'ARMATURE':
            return False
        return True
        
    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.row()
        row.prop(self, 'rig_preset', text="Rig Type:")

        if len(context.selected_objects) > 1 and not self.rig_preset.endswith(".py"):
            row = column.row()
            row.label(text="--Rig Type its sometimes Required--", icon='ERROR')

        row = column.split(factor=0.2, align=True)
        row.label(text="Hips Bone")
        row.prop_search(self, 'hips_bone',
                        context.active_object.data,
                        "bones", text="")
        
        row = column.row()
        row.prop(self, "root_name")
        
        row = column.split(factor=0.30, align=True)
        row.label(text="")
        row.prop(self, "addroot", toggle=True)

    def _set_defaults(self, context, rig_settings):
        if not rig_settings:
            return False
        
        if rig_settings.spine.hips in context.active_object.pose.bones:
            self.hips_bone = rig_settings.spine.hips
        
    def invoke(self, context, event):

        rig_settings = preset_handler.set_preset_skel(self.rig_preset, context)
        self._set_defaults(context, rig_settings)
        self.rig_preset_prev = self.rig_preset

        return self.execute(context)

    def execute(self, context):

        #update 
        if(self.rig_preset_prev != self.rig_preset):
            rig_settings = preset_handler.set_preset_skel(self.rig_preset, context)
            self._set_defaults(context, rig_settings)
            self.rig_preset_prev = self.rig_preset

        current_m = context.mode

        if not self.hips_bone:
            bpy.ops.object.mode_set(mode=current_m)
            return {'FINISHED'}
        
        if not self.addroot:
            bpy.ops.object.mode_set(mode=current_m)
            return {'FINISHED'}
        
        armatures = context.selected_objects
        current_m = context.mode
        bpy.ops.object.mode_set(mode='EDIT')

        for armature in armatures:

            if armature.type != 'ARMATURE':
                continue

            root_name = "Root" if self.root_name == "" else self.root_name 

            prefix_ = ""
            #find the prefix
            for bone in armature.data.edit_bones:
                if ":" in bone.name:
                    prefix_ = bone.name.split(":")[0]
                    if ":" not in root_name:
                        root_name = prefix_ +":"+ root_name
                    #if there's many armatures find the hips bone name for each armature
                    if(len(armatures) > 1) and self.rig_preset.endswith(".py"):
                        self.hips_bone = prefix_ +":"+ preset_handler.get_preset_skel(self.rig_preset).spine.hips
                    break
                else:
                    break
            
            try:
                if armature.data.edit_bones[self.hips_bone]:
                    root_bone = armature.data.edit_bones.new(root_name)
                    root_bone.length = armature.data.edit_bones[self.hips_bone].length * 3
                    armature.data.edit_bones[self.hips_bone].parent = root_bone
        
            except KeyError:
                print(self.hips_bone + " not found in " + armature.name)

        bpy.ops.object.mode_set(mode= current_m)
        return {'FINISHED'}



class AddRootMotion(Operator):
    bl_idname = "armature.retarget_add_rootmotion"
    bl_label = "Transfer Root Motion"
    bl_description = "Bring Motion to Root Bone, ( apply the scale if there's problem )"
    bl_options = {'REGISTER', 'UNDO'}

    rig_preset: EnumProperty(items=preset_handler.iterate_presets,
                             description="the rig preset it needed",
                             name="Target Preset")
    rig_preset_prev = None

    bone_or_channel: EnumProperty(items=[
        ('bone', "Bone", "Use Bone"),
        ('channel', "Channel", "Use Channel")],
                              name="Bone/Channel", default='bone')
    
    channel: StringProperty(name="Channel",
                                description="select Channel",
                                default="")
    #channel
    channelbag = None

    motion_bone: StringProperty(name="Motion",
                                description="select motion bone ( most of the time it's the hips bone )",
                                default="")
    
    del_keyframe: BoolProperty(name="Delete KeyFrame", default=False)

    position_x: BoolProperty(name="X", 
                               description="Delete the Position X",
                               default=True)
    
    position_y: BoolProperty(name="Y", 
                               description="Delete the Position Y",
                               default=True)
    
    position_z: BoolProperty(name="Z", 
                               description="Delete the Position Z",
                               default=True)
    
    rotation_x: BoolProperty(name="X", 
                               description="Delete the Rotation X",
                               default=False)
    
    rotation_y: BoolProperty(name="Y", 
                               description="Delete the Rotation Y",
                               default=False)
    
    rotation_z: BoolProperty(name="Z", 
                               description="Delete the Rotation Z",
                               default=False)
    
    scale_freeze: BoolProperty(name="Delete the scale", 
                               description="Delete the Scale",
                               default=False)


    root_motion_bone: StringProperty(name="Root Motion",
                                     description="select the new motion bone ( root bone )",
                                     default="") 

    new_anim_suffix: StringProperty(name="Suffix",
                                    default="_RM",
                                    description="Suffix of the duplicate animation, leave empty to overwrite")

    obj_or_bone: EnumProperty(items=[
        ('object', "Object", "Transfer Root Motion To Object (Apply the Scale of the Armature)"),
        ('bone', "Bone", "Transfer Root Motion To Bone")],
                              name="Object/Bone", default='bone')

    keep_offset: BoolProperty(name="Keep Offset", default=False)
    offset_type: EnumProperty(items=[
        ('start', "Action Start", "Offset to Start Pose"),
        ('end', "Action End", "Offset to Match End Pose"),
        ('rest', "Rest Pose", "Offset to Match Rest Pose")],
                              name="Offset",
                              default='rest')

    root_cp_loc_x: BoolProperty(name="Root Copy Loc X", description="Copy Root X Location", default=True)
    root_cp_loc_y: BoolProperty(name="Root Copy Loc y", description="Copy Root Y Location", default=True)
    root_cp_loc_z: BoolProperty(name="Root Copy Loc Z", description="Copy Root Z Location", default=False)

    root_use_loc_min_x: BoolProperty(name="Use Root Min X", description="Use Minimum Root X Location", default=False)
    root_use_loc_min_y: BoolProperty(name="Use Root Min Y", description="Use Minimum Root Y Location", default=False)
    root_use_loc_min_z: BoolProperty(name="Use Root Min Z", description="Use Minimum Root Z Location", default=False)

    root_loc_min_x: FloatProperty(name="Root Min X", description="Minimum Root X Location", default=0.0)
    root_loc_min_y: FloatProperty(name="Root Min Y", description="Minimum Root Y Location", default=0.0)
    root_loc_min_z: FloatProperty(name="Root Min Z", description="Minimum Root Z Location", default=0.0)

    root_use_loc_max_x: BoolProperty(name="Use Root Max X", description="Use Maximum Root X Location", default=False)
    root_use_loc_max_y: BoolProperty(name="Use Root Max Y", description="Use Maximum Root Y Location", default=False)
    root_use_loc_max_z: BoolProperty(name="Use Root Max Z", description="Use Maximum Root Z Location", default=False)

    root_loc_max_x: FloatProperty(name="Root Max X", description="Maximum Root X Location", default=0.0)
    root_loc_max_y: FloatProperty(name="Root Max Y", description="Maximum Root Y Location", default=0.0)
    root_loc_max_z: FloatProperty(name="Root Max Z", description="Maximum Root Z Location", default=0.0)

    root_cp_rot_x: BoolProperty(name="Root Copy Rot X", description="Copy Root X Rotation", default=False)
    root_cp_rot_y: BoolProperty(name="Root Copy Rot y", description="Copy Root Y Rotation", default=False)
    root_cp_rot_z: BoolProperty(name="Root Copy Rot Z", description="Copy Root Z Rotation", default=False)

    root_cp_scal_x: BoolProperty(name="Root Copy Scal X", description="Copy Root X Scale", default=False)
    root_cp_scal_y: BoolProperty(name="Root Copy Scal y", description="Copy Root Y Scale", default=False)
    root_cp_scal_z: BoolProperty(name="Root Copy Scal Z", description="Copy Root Z Scale", default=False)

    _armature = None
    _prop_indent = 0.15

    custom_Frame: IntProperty(name="Frame", 
                               description=" To test the animation ",
                              default=1)
    prev_Frame = 0
    action_range: BoolProperty(name= "Action Range to Scene", 
                               description="Set Playback range to current action Start/End",
                               default=True)
    
    transfert_root: BoolProperty(name= "Transfer Root Motion", 
                               description="Clic here to transfer",
                               default=False, options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        if not context.active_object:
            return False
        if context.active_object.type != 'ARMATURE':
            return False 
        if not context.active_object.animation_data:
            return False 
        if not context.active_object.animation_data.action:
            return False 
        return True

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        row = column.row()
        row.prop(self, 'rig_preset', text="Rig Type:")

        split = column.split(factor=self._prop_indent, align=True)
        split.label(text="From")
        col = split.column()
        col.prop(self, 'bone_or_channel', expand=True)

        if self.bone_or_channel == "bone":
    
            col.prop_search(self, 'motion_bone',
                            context.active_object.data,
                            "bones", text="")
        else:
            action = context.active_object.animation_data.action
            channelbag = None
            for slot in action.slots:

                if slot.target_id_type != 'OBJECT':
                    continue

                if not context.active_object in slot.users(): 
                        continue

                channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                break

            if channelbag:

                col.prop_search(self, 'channel',
                                channelbag,
                                "groups", text="")
                
        row = column.row(align=False)
        row.prop(self, "del_keyframe")

        if self.del_keyframe:

            row = column.row(align=True)
            row.label(text="Location")
            row.prop(self, "position_x", text="X", toggle=True)
            row.prop(self, "position_y", text="Y", toggle=True)
            row.prop(self, "position_z", text="Z", toggle=True)

            row = column.row(align=True)
            row.label(text="Rotation")
            row.prop(self, "rotation_x", text="X", toggle=True)
            row.prop(self, "rotation_y", text="Y", toggle=True)
            row.prop(self, "rotation_z", text="Z", toggle=True)

            row = column.split(factor=0.20, align=True)
            row.label(text="Scale")
            row.prop(self, "scale_freeze", text="Delete the Scale", toggle=True)

        #separator
        row = column.row()
        row.label(text="")

        split = column.split(factor=self._prop_indent, align=True)
        split.label(text="To")

        col = split.column()
        col.prop(self, 'obj_or_bone', expand=True)

        if self.obj_or_bone == "bone":
        
            col.prop_search(self, 'root_motion_bone',
                                context.active_object.data,
                                "bones", text="")

        row = column.split(factor=self._prop_indent, align=True)
        row.label(text="Suffix:")
        row.prop(self, 'new_anim_suffix', text="")

        column.separator()

        row = column.row(align=False)
        row.prop(self, "keep_offset")
        subcol = row.column()
        subcol.prop(self, "offset_type", text="Match ")
        subcol.enabled = self.keep_offset

        row = column.row(align=True)
        row.label(text="Location")
        row.prop(self, "root_cp_loc_x", text="X", toggle=True)
        row.prop(self, "root_cp_loc_y", text="Y", toggle=True)
        row.prop(self, "root_cp_loc_z", text="Z", toggle=True)

        row = column.row(align=True)
        row.label(text="Rotation Plane")
        row.prop(self, "root_cp_rot_x", text="X", toggle=True)
        row.prop(self, "root_cp_rot_y", text="Y", toggle=True)
        row.prop(self, "root_cp_rot_z", text="Z", toggle=True)

        row = column.row(align=True)
        row.label(text="Scale")
        row.prop(self, "root_cp_scal_x", text="X", toggle=True)
        row.prop(self, "root_cp_scal_y", text="Y", toggle=True)
        row.prop(self, "root_cp_scal_z", text="Z", toggle=True)

        column.separator()

        # Min/Max X
        row = column.row(align=True)
        row.prop(self, "root_use_loc_min_x", text="Min X")

        subcol = row.column()
        subcol.prop(self, "root_loc_min_x", text="")
        subcol.enabled = self.root_use_loc_min_x

        row.separator()
        row.prop(self, "root_use_loc_max_x", text="Max X")
        subcol = row.column()
        subcol.prop(self, "root_loc_max_x", text="")
        subcol.enabled = self.root_use_loc_max_x
        row.enabled = self.root_cp_loc_x

        # Min/Max Y
        row = column.row(align=True)
        row.prop(self, "root_use_loc_min_y", text="Min Y")

        subcol = row.column()
        subcol.prop(self, "root_loc_min_y", text="")
        subcol.enabled = self.root_use_loc_min_y

        row.separator()
        row.prop(self, "root_use_loc_max_y", text="Max Y")
        subcol = row.column()
        subcol.prop(self, "root_loc_max_y", text="")
        subcol.enabled = self.root_use_loc_max_y
        row.enabled = self.root_cp_loc_y

        # Min/Max Z
        row = column.row(align=True)
        row.prop(self, "root_use_loc_min_z", text="Min Z")

        subcol = row.column()
        subcol.prop(self, "root_loc_min_z", text="")
        subcol.enabled = self.root_use_loc_min_z

        row.separator()
        row.prop(self, "root_use_loc_max_z", text="Max Z")
        subcol = row.column()
        subcol.prop(self, "root_loc_max_z", text="")
        subcol.enabled = self.root_use_loc_max_z
        row.enabled = self.root_cp_loc_z

        row = column.split(factor=0.5, align=True)
        row.prop(self, "custom_Frame", text="Frame")
        row.prop(self, "action_range", toggle=True, icon='PREVIEW_RANGE')

        row = column.row(align=True)
        row.prop(self, "transfert_root", toggle=True, icon='ARMATURE_DATA')


    def _set_defaults(self, context, rig_settings):

        if not rig_settings:
            return 

        if not self.root_motion_bone and rig_settings.root in context.active_object.pose.bones:
            self.root_motion_bone = rig_settings.root
    
        if not self.motion_bone and rig_settings.spine.hips in context.active_object.pose.bones:
            self.motion_bone = rig_settings.spine.hips
        
    def invoke(self, context, event):

        """Fill root and hips field according to character settings"""
        self._rootbo_transfs = []

        self._rootbo_transfs_local = []

        self._hip_bone_transfs = []
        self._all_floating_mats = []

        self._stored_motion_bone = ""
        self._stored_channel = ""
        self._stored_motion_type = self.obj_or_bone
        self._transforms_stored = False

        #reset variable

        if self.root_motion_bone and self.root_motion_bone not in context.active_object.pose.bones:
            self.root_motion_bone = ""
        
        if self.motion_bone and self.motion_bone not in context.active_object.pose.bones:
            self.motion_bone = ""

        if self.channel:
            action = context.active_object.animation_data.action
            channelbag = None
            for slot in action.slots:

                if slot.target_id_type != 'OBJECT':
                    continue

                if not context.active_object in slot.users(): 
                    continue

                channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                break
            if not channelbag or (channelbag and self.channel not in channelbag.groups):
                self.channel = ""
    
        #init the custom_Frame
        self.custom_Frame = context.scene.frame_current
        self.prev_Frame = self.custom_Frame

        rig_settings = context.object.data.retarget_retarget
        if not rig_settings.has_settings():
            rig_settings = preset_handler.set_preset_skel(self.rig_preset, context)
        
        if rig_settings:

            #root prefix
            root_prefix = ""
            for bone in context.active_object.pose.bones:
                if ":" in bone.name and ":" not in rig_settings.root:
                    root_prefix = bone.name.split(":")[0] + ":"
                break

       
            rig_settings.root = root_prefix + rig_settings.root

        self._set_defaults(context, rig_settings)
        self.rig_preset_prev = self.rig_preset

        return self.execute(context)
    
    def init(self, context):
        self._stored_motion_bone = ""
        self._stored_channel = ""
        self._stored_motion_type = self.obj_or_bone
        self._transforms_stored = False

        self._store_transforms(context)

        
    def _get_floating_bones(self, context):
        arm_ob = context.active_object
        
        # TODO: check controls with animation curves instead
        def consider_bone(b_name):
            if b_name == self.root_motion_bone:
                return False
            return b_name in arm_ob.pose.bones

        rig_bones = [bone for bone in arm_ob.pose.bones if bone and consider_bone(bone.name)]
        motion_bone = self.motion_bone
        if not self.motion_bone:
            for bone in arm_ob.pose.bones:
                motion_bone = bone
                break
        
        return list([bone for bone in rig_bones if is_bone_floating(bone, motion_bone)])
        
    def _clear_cache(self):
        self._all_floating_mats.clear()
        self._hip_bone_transfs.clear()
        self._rootbo_transfs_local.clear()

        self._rootbo_transfs.clear()

    def _store_transforms(self, context):
        self._clear_cache()
        arm_ob = context.active_object
        
        try:    
            if self.bone_or_channel == "channel":
                if self.channel in arm_ob.pose.bones:
                    hip_bone = arm_ob.pose.bones[self.channel]
                else:
                    hip_bone = arm_ob
            else:
                hip_bone = arm_ob.pose.bones[self.motion_bone]
        except KeyError:
            return
        if self.obj_or_bone == 'bone' and self.root_motion_bone:
            root_bone = arm_ob.pose.bones[self.root_motion_bone]
        else:
            root_bone = arm_ob

        floating_bones = self._get_floating_bones(context)

        start, end = self._get_start_end(context)

        current_position = arm_ob.data.pose_position

        if self.offset_type == 'start':
            context.scene.frame_set(start)
        elif self.offset_type == 'end':
            context.scene.frame_set(end)
        else:
            arm_ob.data.pose_position = 'REST'
        
        context.scene.frame_set(start)
        arm_ob.data.pose_position = current_position

        for frame_num in range(start, end + 1):

            context.scene.frame_set(frame_num)

            if self.bone_or_channel == "channel" and not self.channel in arm_ob.pose.bones:
                self._hip_bone_transfs.append( hip_bone.matrix_world.copy())
                #TODO fix this
                self._all_floating_mats.append(list([ arm_ob.matrix_world.copy() @ b.matrix.copy() for b in floating_bones]))
            else:
                self._hip_bone_transfs.append(hip_bone.matrix.copy())
                
                self._all_floating_mats.append(list([b.matrix.copy() for b in floating_bones]))


            if self.obj_or_bone == 'object':
                self._rootbo_transfs.append(root_bone.matrix_world.copy())
                self._rootbo_transfs_local.append( root_bone.matrix_world.copy() )
            
            else:
                self._rootbo_transfs.append(root_bone.matrix.copy())                
                self._rootbo_transfs_local.append( arm_ob.matrix_world.copy() @ root_bone.matrix.copy().inverted() )

        self._stored_motion_bone = self.motion_bone
        self._stored_channel = self.channel
        self._stored_motion_type = self.obj_or_bone
        self._transforms_stored = True

    def _cache_dirty(self):
        if self._stored_motion_bone != self.motion_bone:
            return True
        if self._stored_channel != self.channel:
            return True
        if self._stored_motion_type != self.obj_or_bone:
            return True

        return False
    
    def execute(self, context):

        current_m = context.mode

        bpy.ops.object.mode_set(mode='POSE')

        if self.custom_Frame != self.prev_Frame:
            context.scene.frame_current = self.custom_Frame
            self.prev_Frame = self.custom_Frame
        
        if self.action_range and context.active_object.animation_data and context.active_object.animation_data.action:
            bpy.ops.object.retarget_action_to_range()

        if(self.rig_preset_prev != self.rig_preset):
            rig_settings = context.object.data.retarget_retarget
            if not rig_settings.has_settings():
                rig_settings = preset_handler.set_preset_skel(self.rig_preset, context)
            if rig_settings:
                #root prefix
                root_prefix = ""
                for bone in context.object.pose.bones:
                    if ":" in bone.name and ":" not in rig_settings.root:
                        root_prefix = bone.name.split(":")[0] + ":"
                    break
                if rig_settings:
                    rig_settings.root = root_prefix + rig_settings.root

            self._set_defaults(context, rig_settings)
            self.rig_preset_prev = self.rig_preset

        # the armuse need a rig_preset
        #rig_settings = preset_handler.set_preset_skel(self.rig_preset, context)
        #self._set_defaults(rig_settings)
        #self.precision = not self.rig_preset.endswith(".py")

        
        if not self.transfert_root:
            bpy.ops.object.mode_set(mode=current_m)
            return {'FINISHED'}

        if not self.root_motion_bone and self.obj_or_bone == "bone":
            bpy.ops.object.mode_set(mode=current_m)
            return {'FINISHED'}
        
        if (not self.motion_bone and self.bone_or_channel == "bone") or (not self.channel and self.bone_or_channel == "channel"):
            bpy.ops.object.mode_set(mode=current_m)
            return {'FINISHED'}
        
        armatures = context.selected_objects
        for ob in armatures:

            if ob.type != 'ARMATURE':
                continue
            
            if not ob.animation_data:
                continue

            if not ob.animation_data.action:
                continue
            
            context.view_layer.objects.active = ob
           

            if not self.root_motion_bone in ob.pose.bones and self.obj_or_bone == "bone":
                continue
            
            if not self.motion_bone in ob.pose.bones and self.bone_or_channel == "bone":
                continue

            action = ob.animation_data.action
            for slot in action.slots:

                if slot.target_id_type != 'OBJECT':
                    continue

                #only the current slot
                if not ob in slot.users():
                    continue

                self.channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                break 
            
            if not self.channelbag and not self.channel in self.channelbag.groups and self.bone_or_channel == "channel":
                continue
            
            if self.new_anim_suffix:
                action_dupli = ob.animation_data.action.copy()

                action_name = ob.animation_data.action.name
                action_dupli.name = f'{action_name}{self.new_anim_suffix}'
                action_dupli.use_fake_user = ob.animation_data.action.use_fake_user
                ob.animation_data.action = action_dupli

                for slot in action_dupli.slots:

                    if slot.target_id_type != 'OBJECT':
                        continue

                    #only the current slot
                    if not ob in slot.users():
                        continue

                    self.channelbag = anim_utils.action_get_channelbag_for_slot(action_dupli, slot)
                    break 
            
            self.init(context)

            if self._cache_dirty():
                self._store_transforms(context)
                
            if not self._transforms_stored:
                self.report({'WARNING'}, "No transforms stored")

            self.action_offs(context, current_m)

            if self.del_keyframe :
                self.del_Keyframe_f(context)

        bpy.ops.object.mode_set(mode= current_m)
        return {'FINISHED'}
    
    def del_Keyframe_f(self, context):

        if self.bone_or_channel == "channel":
            bone_name = self.channel
            bone = context.active_object
        else:
            bone_name = self.motion_bone
            bone = context.active_object.pose.bones[bone_name]
        
        # if self.obj_or_bone == "bone" and bone_name == self.root_motion_bone:
        #     return
        
        if bone_name in self.channelbag.groups:

            group = self.channelbag.groups[bone_name]
            del_fc = []
            pl = -1
            pr = -1
            
            for fcurve in group.channels:
                data_path = fcurve.data_path
                
                if self.bone_or_channel == "bone" and not bone_name in data_path:
                    continue

                if data_path.endswith('location'):
                    pl += 1

                    if pl == 0 and not self.position_x:
                        continue
                    
                    if pl == 1 and not self.position_y:
                        continue

                    if pl == 2 and not self.position_z:
                        continue

                if 'rotation' in data_path:
                    pr += 1

                    if data_path.endswith('rotation_quaternion'):

                        if pr == 0 and (not self.rotation_x or not self.rotation_y or not self.rotation_z):
                            continue

                        if pr == 1 and not self.rotation_x:
                            continue
                        
                        if pr == 2 and not self.rotation_y:
                            continue

                        if pr == 3 and not self.rotation_z:
                            continue
                    else:
                        if pr == 0 and not self.rotation_x:
                            continue
                        
                        if pr == 1 and not self.rotation_y:
                            continue

                        if pr == 2 and not self.rotation_z:
                            continue

                if data_path.endswith('scale') and not self.scale_freeze:
                    continue
                
                del_fc.append(fcurve)

            for fc in del_fc:
                self.channelbag.fcurves.remove(fc)
            
            bone.location[0] = 0
            bone.location[1] = 0
            bone.location[2] = 0

            
    @staticmethod
    def _get_start_end(context):
        action = context.active_object.animation_data.action
        start, end = action.frame_range
        
        return int(start), int(end)

    def action_offs(self, context, current_m):
        start, end = self._get_start_end(context)
        current = context.scene.frame_current

        if self.bone_or_channel == "channel":
            if self.channel in context.active_object.pose.bones:
                hip_bone = context.active_object.pose.bones[self.channel]
            else:
                hip_bone = context.active_object
        else:
            hip_bone = context.active_object.pose.bones[self.motion_bone]

        if self.keep_offset and self.offset_type == 'end':
            context.scene.frame_set(end)
            if self.bone_or_channel == "channel" and not self.channel in context.active_object.pose.bones:
                end_mat = hip_bone.matrix_world.copy()
            else:
                end_mat = hip_bone.matrix.copy()
        else:
            end_mat = Matrix()

        context.scene.frame_set(start)

        if self.bone_or_channel == "channel" and not self.channel in context.active_object.pose.bones:
            start_mat = hip_bone.matrix_world.copy()
        else:
            start_mat = hip_bone.matrix.copy()

        start_mat_inverse = start_mat.inverted()

        if self.keep_offset:
            if self.offset_type == 'rest':
                if self.bone_or_channel == "channel" and not self.channel in context.active_object.pose.bones:
                    offset_mat = context.active_object.data.matrix_local.inverted()
                else:
                    offset_mat = context.active_object.data.bones[hip_bone.name].matrix_local.inverted()
            elif self.offset_type == 'start':
                offset_mat = start_mat_inverse
            elif self.offset_type == 'end':
                offset_mat = end_mat.inverted()
        else:
            offset_mat = Matrix()


        if self.obj_or_bone == 'object':
            root_bone = context.active_object
        else:
            root_bone_name = self.root_motion_bone
            try:
                root_bone = context.active_object.pose.bones[root_bone_name]
            except (TypeError, KeyError):
                self.report({'WARNING'}, f"{root_bone_name} not found in target")
                bpy.ops.object.mode_set(mode=current_m)
                return {'FINISHED'}
        
        context.scene.frame_set(start)
        keyframe_options = {'INSERTKEY_VISUAL', 'INSERTKEY_CYCLE_AWARE'}
        add_loc_rot_key(root_bone, start, keyframe_options)

        root_matrix = root_bone.matrix if self.obj_or_bone == 'bone' else context.active_object.matrix_world
        for i, frame_num in enumerate(range(start, end + 1)):
            context.scene.frame_set(frame_num)

            rootmo_transf = self._hip_bone_transfs[i] @ offset_mat
            
            #oject to borne or object
            if self.bone_or_channel == "channel" and not self.channel in context.active_object.pose.bones and self.obj_or_bone == 'bone':
                root_matrix = self._rootbo_transfs_local[i]
                
                if self.root_cp_loc_x:
                    rootmo_transf[0][3] = root_matrix[0][3]
                    if self.root_use_loc_min_x:
                        rootmo_transf[0][3] = max(root_matrix[0][3], self.root_loc_min_x)
                    if self.root_use_loc_max_x:
                        rootmo_transf[0][3] = min(root_matrix[0][3], self.root_loc_max_x)


                if self.root_cp_loc_y:
                    rootmo_transf[1][3] = root_matrix[1][3]
                    if self.root_use_loc_min_y:
                        rootmo_transf[1][3] = max(root_matrix[1][3], self.root_loc_min_y)
                    if self.root_use_loc_max_y:
                        rootmo_transf[1][3] = min(root_matrix[1][3], self.root_loc_max_y)

                if self.root_cp_loc_z:
                    rootmo_transf[2][3] = root_matrix[2][3]
                    if self.root_use_loc_min_z:
                        rootmo_transf[2][3] = max(root_matrix[2][3], self.root_loc_min_z)
                    if self.root_use_loc_max_z:
                        rootmo_transf[2][3] = min(root_matrix[2][3], self.root_loc_max_z)

            else:
                if self.root_cp_loc_x:
                    if self.root_use_loc_min_x:
                        rootmo_transf[0][3] = max(rootmo_transf[0][3], self.root_loc_min_x)
                    if self.root_use_loc_max_x:
                        rootmo_transf[0][3] = min(rootmo_transf[0][3], self.root_loc_max_x)
                else:
                    rootmo_transf[0][3] = root_matrix[0][3]
                if self.root_cp_loc_y:
                    if self.root_use_loc_min_y:
                        rootmo_transf[1][3] = max(rootmo_transf[1][3], self.root_loc_min_y)
                    if self.root_use_loc_max_y:
                        rootmo_transf[1][3] = min(rootmo_transf[1][3], self.root_loc_max_y)
                else:
                    rootmo_transf[1][3] = root_matrix[1][3]
                if self.root_cp_loc_z:
                    if self.root_use_loc_min_z:
                        rootmo_transf[2][3] = max(rootmo_transf[2][3], self.root_loc_min_z)
                    if self.root_use_loc_max_z:
                        rootmo_transf[2][3] = min(rootmo_transf[2][3], self.root_loc_max_z)
                else:
                    rootmo_transf[2][3] = root_matrix[2][3]

            if self.root_cp_rot_x + self.root_cp_rot_y + self.root_cp_rot_z < 2:
                # need at least two axis to make this work, don't use rotation

                #set the offset
                if offset_mat == Matrix():
                    no_rot = self._rootbo_transfs[i]
                else:
                    tmp = self._rootbo_transfs[i]
                    no_rot = tmp  @ offset_mat
                    no_rot[0][2] = tmp[0][2]
                    no_rot[1][2] = tmp[1][2]
                    no_rot[2][2] = tmp[2][2]

                no_rot[0][3] = rootmo_transf[0][3]
                no_rot[1][3] = rootmo_transf[1][3]
                no_rot[2][3] = rootmo_transf[2][3]

                rootmo_transf = no_rot
            else:
                rootmo_transf.transpose()
                root_transp = root_matrix.transposed()

                if not self.root_cp_rot_z:
                    # XY plane
                    rootmo_transf[1][2] = root_transp[1][2]
                    rootmo_transf[0][2] = root_transp[0][2]

                    y_axis = rootmo_transf[1].to_3d()
                    y_axis.normalize()

                    x_axis = y_axis.cross(root_transp[2].to_3d())
                    x_axis.normalize()

                    z_axis = x_axis.cross(y_axis)
                    z_axis.normalize()
                elif not self.root_cp_rot_x:
                    # ZY plane
                    rootmo_transf[1][0] = root_transp[1][0]
                    rootmo_transf[2][0] = root_transp[2][0]

                    z_axis = rootmo_transf[2].to_3d().normalized()
                    up = root_transp[1].to_3d()
                    x_axis = up.cross(z_axis).normalized()
                    y_axis = z_axis.cross(x_axis)
                    y_axis.normalize()
                else:
                    # XZ plane
                    rootmo_transf[2][1] = root_transp[2][1]
                    rootmo_transf[0][1] = root_transp[0][1]

                    z_axis = rootmo_transf[2].to_3d().normalized()
                    up = root_transp[1].to_3d()
                    x_axis = up.cross(z_axis).normalized()
                    y_axis = z_axis.cross(x_axis)

                rootmo_transf[0] = x_axis.to_4d()
                rootmo_transf[1] = y_axis.to_4d()
                rootmo_transf[2] = z_axis.to_4d()

                rootmo_transf.transpose()

            if any ((self.root_cp_scal_x, self.root_cp_scal_y, self.root_cp_scal_z)):

                rot_tmp = self._rootbo_transfs[i]

                if self.root_cp_scal_x:
                    rootmo_transf[1][1] = rot_tmp[1][1]
                    rootmo_transf[2][1] = rot_tmp[2][1]
                    
                if self.root_cp_scal_y:
                    rootmo_transf[0][1] = rot_tmp[0][1]
                    rootmo_transf[2][1] = rot_tmp[2][1]
                
                if self.root_cp_scal_z:
                    rootmo_transf[0][1] = rot_tmp[0][1]
                    rootmo_transf[1][1] = rot_tmp[1][1]

            
            if self.obj_or_bone == 'object':
                root_bone.matrix_world = rootmo_transf
            else:
                root_bone.matrix = rootmo_transf
            
            add_loc_rot_key(root_bone, frame_num, keyframe_options)

            if any((self.root_cp_scal_x, self.root_cp_scal_y, self.root_cp_scal_z)):
                add_scal_key(root_bone, frame_num, keyframe_options)

        #TODO fix this object vers bone/object
        if not (self.bone_or_channel == "channel" and not self.channel in context.active_object.pose.bones):
            floating_bones = self._get_floating_bones(context)
            for i, frame_num in enumerate(range(start, end + 1)):
                context.scene.frame_set(frame_num)

                if self.obj_or_bone == 'object' and self.root_motion_bone:
                    context.active_object.pose.bones[self.root_motion_bone].matrix = root_bone.matrix_world.inverted() @ context.active_object.pose.bones[self.root_motion_bone].matrix

                floating_mats = self._all_floating_mats[i]
                for bone, mat in zip(floating_bones, floating_mats):
                    if self.obj_or_bone == 'object':
                        # TODO: should get matrix at frame 0
                        mat = root_bone.matrix_world.inverted() @ mat

                    bone.matrix = mat
                    add_loc_rot_key(bone, frame_num, set())

        context.scene.frame_set(current)


class ActionNameCandidates(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name Candidate", default="")


classes = (
	 ActionRangeToScene,
     AdjustAnimation,
	 ConstraintStatus,
	 SelectConstrainedControls,
	 AlignBone,
	 ConvertBoneNaming,
	 ConvertGameFriendly,
	 ExtractMetarig,
	 MergeHeadTails,
	 ConstrainToArmature,
	 BakeConstrainedActions,
     ApplyAsRestPose,
	 CreateTransformOffset,
	 AddRoot,
	 AddRootMotion,
	 ActionNameCandidates,

)


def register_classes():
    for cls in classes:
        bpy.utils.register_class(cls)
    

    bpy.types.Action.retarget_name_candidates = bpy.props.CollectionProperty(type=ActionNameCandidates)


def unregister_classes():
    del bpy.types.Action.retarget_name_candidates

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)