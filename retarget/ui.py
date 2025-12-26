import bpy
from bpy.props import StringProperty
from bpy.props import BoolProperty
from bpy.props import FloatProperty
from bpy.props import PointerProperty
from bpy.types import Context, Operator, Menu, Panel
from bl_operators.presets import AddPresetBase

from bpy.app.translations import (
    pgettext_rpt as rpt_,
    pgettext_data as data_,
)

from . import operators
from . import preset_handler
from . import properties


def menu_header(layout):
    row = layout.row()
    row.separator()

    row = layout.row()
    row.label(text="Retarget", icon='ARMATURE_DATA')


def object_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    row = layout.row()
    row.operator(operators.CreateTransformOffset.bl_idname)


class BindingsMenu(Menu):
    bl_label = "Binding"
    bl_idname = "OBJECT_MT_retarget_binding_menu"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator(operators.ConstrainToArmature.bl_idname)

        row = layout.row()
        row.operator(operators.ConstraintStatus.bl_idname)

        row = layout.row()
        row.operator(operators.SelectConstrainedControls.bl_idname)

        row = layout.row()
        row.operator(operators.AlignBone.bl_idname)


class ConvertMenu(Menu):
    bl_label = "Conversion"
    bl_idname = "OBJECT_MT_retarget_convert_menu"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator(operators.ConvertGameFriendly.bl_idname)

        row = layout.row()
        row.operator(operators.ConvertBoneNaming.bl_idname)

        row = layout.row()
        row.operator(operators.ExtractMetarig.bl_idname)

        row = layout.row()
        row.operator(operators.ApplyAsRestPose.bl_idname)

        row = layout.row()
        row.operator(operators.CreateTransformOffset.bl_idname)

        row = layout.row()
        row.operator(operators.MergeHeadTails.bl_idname)


class AnimMenu(Menu):
    bl_label = "Animation"
    bl_idname = "OBJECT_MT_retarget_anim_menu"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator(operators.ActionRangeToScene.bl_idname)

        row = layout.row()
        row.operator(operators.AdjustAnimation.bl_idname)

        row = layout.row()
        row.operator(operators.BakeConstrainedActions.bl_idname)

        row = layout.row()
        row.operator(operators.AddRoot.bl_idname)

        row = layout.row()
        row.operator(operators.AddRootMotion.bl_idname)

def pose_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    # use an operator enum property to populate a sub-menu
    layout.menu(BindingsMenu.bl_idname)
    layout.menu(ConvertMenu.bl_idname)
    layout.menu(AnimMenu.bl_idname)

    layout.separator()


def armature_context_options(self, context):
    layout = self.layout
    menu_header(layout)

    row = layout.row()
    row.operator(operators.MergeHeadTails.bl_idname)


def action_header_buttons(self, context):
    layout = self.layout
    row = layout.row()
    row.operator(operators.ActionRangeToScene.bl_idname, icon='PREVIEW_RANGE', text='To Scene Range')

#pie menu short cut
class Retarget_pie_menu(Operator):
    bl_idname = "object.retarget_pie_menu"
    bl_label = "Retarget Pie Menu"

    @classmethod
    def poll(cls, context):
        if context.mode not in ['POSE', 'OBJECT']:
            return False
        return True
   
    def invoke(self, context, event):
        
        bpy.ops.wm.call_menu_pie(name = VIEW3D_MT_PIE_Retarget.bl_idanme)
        return {'FINISHED'}
    
class VIEW3D_MT_PIE_Retarget(Menu):
    bl_idanme = 'VIEW3D_MT_PIE_Retarget'
    bl_label = "RETARGET"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        
        gap = pie.column()

        menu = gap.box()
        my_text = "BINDING".center(40)
        menu.label(text= my_text, icon='LINKED')
        menu.operator(operators.ConstrainToArmature.bl_idname)
        menu.operator(operators.ConstraintStatus.bl_idname)
        menu.operator(operators.SelectConstrainedControls.bl_idname)
        menu.operator(operators.AlignBone.bl_idname)

        
        gap = pie.column()
        gap.separator()
        gap.separator()
        gap.separator()
        gap.separator()
        gap.separator()
        gap.separator()

        menu = gap.box()
        my_text = "CONVERSION".center(40)
        menu.label(text= my_text, icon='BONE_DATA')
        menu.operator(operators.ConvertGameFriendly.bl_idname)
        menu.operator(operators.ConvertBoneNaming.bl_idname)
        menu.operator(operators.ExtractMetarig.bl_idname)
        menu.operator(operators.ApplyAsRestPose.bl_idname)
        menu.operator(operators.CreateTransformOffset.bl_idname)
        menu.operator(operators.MergeHeadTails.bl_idname)

        gap = pie.column()

        menu = gap.box()
        my_text = "ANIMATION".center(40)
        menu.label(text= my_text, icon='OUTLINER_DATA_ARMATURE')
        menu.operator(operators.ActionRangeToScene.bl_idname)
        menu.operator(operators.AdjustAnimation.bl_idname)
        menu.operator(operators.BakeConstrainedActions.bl_idname)
        menu.operator(operators.AddRoot.bl_idname)
        menu.operator(operators.AddRootMotion.bl_idname)

#---------

class ActionRemoveRenameData(Operator):
    """Remove action rename data"""
    bl_idname = "object.retarget_remove_action_rename_data"
    bl_label = "Retarget remove rename data"

    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode  != 'EDIT_ARMATURE'
    
    def execute(self, context):
        for action in bpy.data.actions:
            action.retarget_name_candidates.clear()

        return {'FINISHED'}


class ActionMakeActive(Operator):
    """Apply next action and adjust timeline"""
    bl_idname = "object.retarget_make_action_active"
    bl_label = "Retarget apply action"

    @classmethod
    def poll(cls, context):
        return context.mode  != 'EDIT_ARMATURE'
    
    def execute(self, context: Context):
        ob = context.object
        to_rename = [a for a in bpy.data.actions if len(a.retarget_name_candidates) > 1 and operators.validate_actions(a, ob.path_resolve)]

        if len(to_rename) == 0:
            return {'CANCELLED'}
        
        if not ob.animation_data.action:
            action = to_rename.pop()
        else:
            try:
                idx = to_rename.index(ob.animation_data.action)
            except ValueError:
                action = to_rename.pop()
            else:
                action = to_rename[idx - 1]

        context.object.animation_data.action = action
        bpy.ops.object.retarget_action_to_range()

        return {'FINISHED'}


class ActionRenameSimple(Operator):
    """Rename Current Action"""
    bl_idname = "object.retarget_rename_action_simple"
    bl_label = "Retarget Action Rename"
    bl_options = {'REGISTER', 'UNDO'}

    new_name: StringProperty(default="", name="Renamed to")

    @classmethod
    def poll(cls, context):
        if not context.object:
            return None
        if context.object.type != 'ARMATURE':
            return False
        if not context.object.animation_data:
            return False
        if not context.object.animation_data.action:
            return False

        return True

    def execute(self, context):
        action = context.object.animation_data.action
        if self.new_name and action:
            action.name = self.new_name

        # remove candidate from other actions
        for other_action in bpy.data.actions:
            if other_action == action:
                continue
            idx = other_action.retarget_name_candidates.find(self.new_name)
            if idx > -1:
                other_action.retarget_name_candidates.remove(idx)
            if len(other_action.retarget_name_candidates) == 1:
                other_action.name = other_action.retarget_name_candidates[0].name

        action.retarget_name_candidates.clear()
        return {'FINISHED'}


class VIEW3D_PT_retarget_rename_candidates(Panel):
    bl_label = "Action Name Candidates"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Retarget"
    bl_idname = "VIEW3D_PT_retarget_rename_candidates"

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_ARMATURE':
            return False

        try:
            next(a for a in bpy.data.actions if len(a.retarget_name_candidates) > 1)
        except StopIteration:
            return False
        
        return True

    def draw(self, context):
        layout = self.layout

        to_rename = [a for a in bpy.data.actions if len(a.retarget_name_candidates) > 1 and operators.validate_actions(a, context.object.path_resolve)]

        row = layout.row()
        row.operator(ActionMakeActive.bl_idname, text=f"Next of {len(to_rename)} actions to rename")

        action = context.object.animation_data.action
        if not action:
            return
        
        row = layout.row()
        row.label(text=action.name)
        
        for candidate in action.retarget_name_candidates:
            if candidate.name in bpy.data.actions:
                # that name has been taken
                continue

            row = layout.row()
            op = row.operator(ActionRenameSimple.bl_idname, text=candidate.name)
            op.new_name = candidate.name


class VIEW3D_PT_retarget_rename_advanced(Panel):
    bl_label = "Advanced Options"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Retarget"

    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = VIEW3D_PT_retarget_rename_candidates.bl_idname

    @classmethod
    def poll(cls, context):
        if context.mode  == 'EDIT_ARMATURE':
            return False

        to_rename = [a for a in bpy.data.actions if len(a.retarget_name_candidates) > 1]
        return len(to_rename) > 0

    def draw(self, context):
        row = self.layout.row()
        row.operator(ActionRemoveRenameData.bl_idname, text="Remove Rename Data")


class AddPresetArmatureRetarget(AddPresetBase, Operator):
    """Add a Bone Retarget Preset"""
    bl_idname = "object.retarget_armature_preset_add"
    bl_label = "Retarget Preset (select a armature)"
    preset_menu = "VIEW3D_MT_retarget_presets"

    # variable used for all preset values
    preset_defines = [
        "skeleton = bpy.context.object.data.retarget_retarget"
    ]

    # properties to store in the preset
    preset_values = [
        "skeleton.face",

        "skeleton.spine",
        "skeleton.right_arm",
        "skeleton.left_arm",
        "skeleton.right_leg",
        "skeleton.left_leg",

        "skeleton.left_fingers",
        "skeleton.right_fingers",

        "skeleton.right_arm_ik",
        "skeleton.left_arm_ik",

        "skeleton.right_leg_ik",
        "skeleton.left_leg_ik",

        "skeleton.deform_preset",
        "skeleton.root",
    ]

    preset_subdir = preset_handler.PRESETS_SUBDIR

class ClearArmatureRetarget(Operator):
    bl_idname = "object.retarget_armature_clear"
    bl_label = "Clear Retarget Settings"

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.object.type != 'ARMATURE':
            return False

        return True

    def execute(self, context):
        skeleton = context.object.data.retarget_retarget
        for setting in (skeleton.right_arm, skeleton.left_arm, skeleton.spine, skeleton.right_leg,
                        skeleton.left_leg, skeleton.right_arm_ik, skeleton.left_arm_ik,
                        skeleton.right_leg_ik, skeleton.left_leg_ik,
                        skeleton.face,
                        ):
            for k in setting.keys():
                if k == 'name':
                    continue
                try:
                    setattr(setting, k, '')
                except TypeError:
                    continue

        for settings in (skeleton.right_fingers, skeleton.left_fingers):
            for setting in [getattr(settings, k) for k in settings.keys()]:
                if k == 'name':
                    continue
                try:
                    for k in setting.keys():
                        setattr(setting, k, '')
                except AttributeError:
                    continue

        skeleton.root = ''
        skeleton.deform_preset = '--'

        return {'FINISHED'}


class SetToActiveBone(Operator):
    """Set adjacent UI entry to active bone"""
    bl_idname = "object.retarget_set_to_active_bone"
    bl_label = "Set Retarget value to active bone"

    attr_name: StringProperty(default="", options={'SKIP_SAVE'})
    sub_attr_name: StringProperty(default="", options={'SKIP_SAVE'})
    slot_name: StringProperty(default="", options={'SKIP_SAVE'})
    attr_ptr = PointerProperty(type=properties.RetargetBase)

    @classmethod
    def poll(cls, context):
        if context.mode  == 'EDIT_ARMATURE':
            return False
        return True

    def execute(self, context):
        current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')
        if not self.attr_name or not  context.active_pose_bone:
            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}

        skeleton = context.object.data.retarget_retarget

        if not self.slot_name:
            if self.attr_name == 'root':
                setattr(skeleton, 'root', context.active_pose_bone.name)

            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}

        try:
            rig_grp = getattr(skeleton, self.attr_name)
        except AttributeError:
            # TODO: warning
            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}
        else:
            if self.sub_attr_name:
                rig_grp = getattr(rig_grp, self.sub_attr_name)
                
            setattr(rig_grp, self.slot_name, context.active_pose_bone.name)

        
        bpy.ops.object.mode_set(mode= current_m)
        return {'FINISHED'}


class MirrorSettings(Operator):
    """Mirror Settings to the other side"""
    bl_idname = "object.retarget_settings_mirror"
    bl_label = "Mirror Skeleton Mapping"
    bl_options = {'REGISTER', 'UNDO'}

    src_setting: StringProperty(default="", options={'SKIP_SAVE'})
    trg_setting: StringProperty(default="", options={'SKIP_SAVE'})

    tolerance: FloatProperty(default=0.001)

    @classmethod
    def poll(cls, context):
        if not context.object:
            return False
        if context.object.type != 'ARMATURE':
            return False
        if not context.object.data.retarget_retarget:
            return False

        return True

    def _is_mirrored_vec(self, trg_head, src_head):
        epsilon = self.tolerance
        if abs(trg_head.x + src_head.x) > epsilon:
            return False
        if abs(trg_head.y - src_head.y) > epsilon:
            return False
        return abs(trg_head.z - src_head.z) < epsilon
    
    def _is_mirrored(self, src_bone, trg_bone):
        if not self._is_mirrored_vec(src_bone.head_local, trg_bone.head_local):
            return False
        if not self._is_mirrored_vec(src_bone.tail_local, trg_bone.tail_local):
            return False
        
        return True

    def find_mirrored(self, arm_data, bone):
        # TODO: should be in bone_utils
        # TODO: should select best among mirror candidates
        return next((b for b in arm_data.bones if self._is_mirrored(bone, b)), None)

    def execute(self, context):
        current_m = context.mode
        bpy.ops.object.mode_set(mode='POSE')

        if not self.src_setting:
            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}
        if not self.trg_setting:
            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}

        skeleton = context.object.data.retarget_retarget

        try:
            src_grp = getattr(skeleton, self.src_setting)
        except AttributeError:
            # TODO: warning
            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}
        
        try:
            trg_grp = getattr(skeleton, self.trg_setting)
        except AttributeError:
            # TODO: warning
            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}

        arm_data = context.object.data
        if 'fingers' in self.trg_setting:
            for finger_name in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                for attr_name in ('a', 'b', 'c'):
                    bone_name = getattr(getattr(src_grp, finger_name), attr_name)
                    if not bone_name:
                        continue
                    m_bone = self.find_mirrored(arm_data,
                                                arm_data.bones[bone_name])
                    if not m_bone:
                        continue

                    setattr(getattr(trg_grp, finger_name), attr_name, m_bone.name)

            bpy.ops.object.mode_set(mode= current_m)
            return {'FINISHED'}

        for k, v in src_grp.items():
            if not v:
                continue

            try:
                bone = arm_data.bones[v]
            except KeyError:
                continue

            m_bone = self.find_mirrored(arm_data, bone)
            if m_bone:
                setattr(trg_grp, k, m_bone.name)

        bpy.ops.object.mode_set(mode= current_m)
        return {'FINISHED'}


class VIEW3D_MT_retarget_presets(Menu):
    bl_label = "Retarget Presets"
    preset_subdir = AddPresetArmatureRetarget.preset_subdir
    preset_operator = "script.execute_preset"

    draw = Menu.draw_preset


class BindFromPanelSelection(Operator):
    """Constrain to armature selected in panel"""
    bl_idname = "object.retarget_bind_from_panel"
    bl_label = "Bind Armatures"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode != 'EDIT_ARMATURE' and context.scene.retarget_bind_to and context.object != context.scene.retarget_bind_to and context.object.type == 'ARMATURE'
    
    def execute(self, context: Context):

        for ob in context.selected_objects:
            if not ob.hide_viewport:
                ob.select_set(ob == context.object)
       
        if not context.scene.retarget_bind_to.hide_viewport and context.scene.retarget_bind_to.name in context.view_layer.objects:
            context.scene.retarget_bind_to.select_set(True)

        if len(context.selected_objects) < 2:
            self.report({'WARNING'}, "A object is hidden")
            return {'FINISHED'}
        
        context.view_layer.objects.active = context.scene.retarget_bind_to

        if context.scene.retarget_bind_to.animation_data and context.scene.retarget_bind_to.animation_data.action:
            # TODO: this should be in the constrain operator
            bpy.ops.object.retarget_action_to_range()
        
        bpy.ops.armature.retarget_constrain_to_armature('INVOKE_DEFAULT', force_dialog=True)

        return {'FINISHED'}


class VIEW3D_PT_BindPanel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Retarget"
    bl_label = "Bind To"

    @classmethod
    def poll(cls, context):
        return context.mode  != 'EDIT_ARMATURE'

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, 'retarget_bind_to', text="")

        layout.operator(BindFromPanelSelection.bl_idname)


class RetargetBasePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Retarget"

    @classmethod
    def poll(cls, context):
        return context.mode != 'EDIT_ARMATURE'

    def sided_rows(self, ob, limbs, bone_names, suffix=""):
        split = self.layout.split()

        labels = None
        side = 'right'
        for group in limbs:
            attr_tokens = [side, group.name]
            attr_suffix = suffix.strip(' ').lower()
            if attr_suffix:
                attr_tokens.append(attr_suffix)

            attr_name = '_'.join(attr_tokens)
            
            col = split.column()
            row = col.row()
            if not labels:
                row.label(text=side.title())
                labels = split.column()
                row = labels.row()

                mirror_props = row.operator(MirrorSettings.bl_idname, text="<--")
                mirror_props.trg_setting = attr_name

                mirror_props_2 = row.operator(MirrorSettings.bl_idname, text="-->")
                mirror_props_2.src_setting = attr_name
                side = 'left'
            else:
                mirror_props.src_setting = attr_name
                mirror_props_2.trg_setting = attr_name
                row.label(text=side.title())

            for k in bone_names:
                bsplit = col.split(factor=0.85)
                bsplit.prop_search(group, k, ob.data, "bones", text="")

                props = bsplit.operator(SetToActiveBone.bl_idname, text="<-")
                props.attr_name = attr_name
                props.slot_name = k

        for k in bone_names:
            row = labels.row()
            row.label(text=(k + suffix).title())


class VIEW3D_PT_retarget_retarget(RetargetBasePanel, Panel):
    bl_label = "Retarget Mapping"

    def draw(self, context):
        layout = self.layout

        split = layout.split(factor=0.75)
        split.menu(VIEW3D_MT_retarget_presets.__name__, text=VIEW3D_MT_retarget_presets.bl_label)
        row = split.row(align=True)
        row.operator(AddPresetArmatureRetarget.bl_idname, text="+")
        row.operator(AddPresetArmatureRetarget.bl_idname, text="-").remove_active = True

class VIEW3D_PT_retarget_retarget_face(RetargetBasePanel, Panel):
    bl_label = "Face"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        ob = context.object
        layout = self.layout

        if not context.active_object or ob.type != 'ARMATURE':
            return
        
        skeleton = ob.data.retarget_retarget

        bsplit = layout.split(factor=0.85)
        bsplit.prop_search(skeleton.face, "jaw", ob.data, "bones", text="Jaw")
        props = bsplit.operator(SetToActiveBone.bl_idname, text="<-")
        props.attr_name = 'face'
        props.slot_name = 'jaw'

        split = layout.split()
        col = split.column()
        col.label(text="Right")

        bsplit = col.split(factor=0.85)
        col = bsplit.column()
        col.prop_search(skeleton.face, "right_eye", ob.data, "bones", text="")
        col.prop_search(skeleton.face, "right_upLid", ob.data, "bones", text="")

        col = bsplit.column()
        eye_props = col.operator(SetToActiveBone.bl_idname, text="<-")
        eye_props.attr_name = 'face'
        eye_props.slot_name = 'right_eye'

        eye_props = col.operator(SetToActiveBone.bl_idname, text="<-")
        eye_props.attr_name = 'face'
        eye_props.slot_name = 'right_upLid'

        col = split.column()
        col.label(text="")
        col.label(text="Eye")
        col.label(text="Up Lid")

        col = split.column()
        col.label(text="Left")

        bsplit = col.split(factor=0.85)
        col = bsplit.column()
        col.prop_search(skeleton.face, "left_eye", ob.data, "bones", text="")
        col.prop_search(skeleton.face, "left_upLid", ob.data, "bones", text="")

        col = bsplit.column()
        eye_props = col.operator(SetToActiveBone.bl_idname, text="<-")
        eye_props.attr_name = 'face'
        eye_props.slot_name = 'left_eye'

        eye_props = col.operator(SetToActiveBone.bl_idname, text="<-")
        eye_props.attr_name = 'face'
        eye_props.slot_name = 'left_upLid'

        row = layout.row()
        row.prop(skeleton.face, "super_copy", text="As Rigify Super Copy")


class VIEW3D_PT_retarget_retarget_fingers(RetargetBasePanel, Panel):
    bl_label = "Fingers"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        ob = context.object
        layout = self.layout

        if not context.active_object or ob.type != 'ARMATURE':
            return
        
        skeleton = ob.data.retarget_retarget
        
        sides = "right", "left"
        split = layout.split()
        finger_bones = ('a', 'b', 'c')
        fingers = ('thumb', 'index', 'middle', 'ring', 'pinky')
        m_props = []
        for side, group in zip(sides, [skeleton.right_fingers, skeleton.left_fingers]):
            col = split.column()
            m_props.append(col.operator(MirrorSettings.bl_idname, text="<--" if side == 'right' else "-->"))

            for k in fingers:
                if k == 'name':  # skip Property Group name
                    continue
                row = col.row()
                row.label(text=" ".join((side, k)).title())
                finger = getattr(group, k)
                for slot in finger_bones:
                    bsplit = col.split(factor=0.85)
                    bsplit.prop_search(finger, slot, ob.data, "bones", text="")
                    
                    f_props = bsplit.operator(SetToActiveBone.bl_idname, text="<-")
                    f_props.attr_name = '_'.join([side, group.name])
                    f_props.sub_attr_name = k
                    f_props.slot_name = slot

        m_props[0].trg_setting = "right_fingers"
        m_props[0].src_setting = "left_fingers"

        m_props[1].trg_setting = "left_fingers"
        m_props[1].src_setting = "right_fingers"


class VIEW3D_PT_retarget_retarget_arms_IK(RetargetBasePanel, Panel):
    bl_label = "Arms IK"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        ob = context.object
        layout = self.layout

        try:

            skeleton = ob.data.retarget_retarget
            arm_bones = ('shoulder', 'arm', 'forearm', 'hand')

            self.sided_rows(ob, (skeleton.right_arm_ik, skeleton.left_arm_ik), arm_bones, suffix=" IK")
        except AttributeError:
            pass

class VIEW3D_PT_retarget_retarget_arms(RetargetBasePanel, Panel):
    bl_label = "Arms"

    def draw(self, context):
        ob = context.object
        layout = self.layout

        try:

            skeleton = ob.data.retarget_retarget

            row = layout.row()
            row.prop(ob.data, "retarget_twist_on", text="Display Twist Bones")
            
            if ob.data.retarget_twist_on:
                arm_bones = ('shoulder', 'arm', 'arm_twist', 'arm_twist_02', 'forearm', 'forearm_twist', 'forearm_twist_02', 'hand')
            else:
                arm_bones = ('shoulder', 'arm', 'forearm', 'hand')

            self.sided_rows(ob, (skeleton.right_arm, skeleton.left_arm), arm_bones)
        except AttributeError:
            pass

class VIEW3D_PT_retarget_retarget_spine(RetargetBasePanel, Panel):
    bl_label = "Spine"

    def draw(self, context):
        ob = context.object
        layout = self.layout

        try:

            skeleton = ob.data.retarget_retarget

            for slot in ('head', 'neck', 'spine2', 'spine1', 'spine', 'hips'):
                split = layout.split(factor=0.85)
                split.prop_search(skeleton.spine, slot, ob.data, "bones", text="Chest" if slot == 'spine2' else slot.title())
                props = split.operator(SetToActiveBone.bl_idname, text="<-")
                props.attr_name = 'spine'
                props.slot_name = slot
        except AttributeError:
            pass

class VIEW3D_PT_retarget_retarget_leg_IK(RetargetBasePanel, Panel):
    bl_label = "Legs IK"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        ob = context.object
        
        try:

            skeleton = ob.data.retarget_retarget
            
            leg_bones = ('upleg', 'leg', 'foot', 'toe')
            self.sided_rows(ob, (skeleton.right_leg_ik, skeleton.left_leg_ik), leg_bones, suffix=" IK")
        except AttributeError:
            pass

class VIEW3D_PT_retarget_retarget_leg(RetargetBasePanel, Panel):
    bl_label = "Legs"

    def draw(self, context):
        ob = context.object

        try:

            skeleton = ob.data.retarget_retarget

            row = self.layout.row(align=True)
            row.prop(ob.data, "retarget_twist_on", text="Display Twist Bones")

            if ob.data.retarget_twist_on:
                leg_bones = ('upleg', 'upleg_twist', 'upleg_twist_02', 'leg', 'leg_twist', 'leg_twist_02', 'foot', 'toe')
            else:
                leg_bones = ('upleg', 'leg', 'foot', 'toe')

            self.sided_rows(ob, (skeleton.right_leg, skeleton.left_leg), leg_bones)
        except AttributeError:
            pass

class VIEW3D_PT_retarget_retarget_root(RetargetBasePanel, Panel):
    bl_label = "Root"

    def draw(self, context):
        ob = context.object
        layout = self.layout

        try:

            skeleton = ob.data.retarget_retarget

            split = layout.split(factor=0.85)
            split.prop_search(skeleton, 'root', ob.data, "bones", text="Root")
            s_props = split.operator(SetToActiveBone.bl_idname, text="<-")
            s_props.attr_name = 'root'
            s_props.sub_attr_name = ''

            layout.separator()
            row = layout.row()
            row.prop(skeleton, 'deform_preset')

            row = layout.row()
            row.operator(ClearArmatureRetarget.bl_idname, text="Clear All")
        except AttributeError:
            pass

def poll_armature_bind_to(self, object):
    return object != bpy.context.object and object.type == 'ARMATURE' 


classes = (
	 ClearArmatureRetarget,
	 VIEW3D_MT_retarget_presets,
	 AddPresetArmatureRetarget,
	 SetToActiveBone,
	 MirrorSettings,
	 BindingsMenu,
	 ConvertMenu,
	 AnimMenu,
	 ActionRenameSimple,
	 ActionMakeActive,
	 ActionRemoveRenameData,
	 VIEW3D_PT_retarget_rename_candidates,
	 VIEW3D_PT_retarget_rename_advanced,
	 BindFromPanelSelection,
	 VIEW3D_PT_BindPanel,
	 VIEW3D_PT_retarget_retarget,
	 VIEW3D_PT_retarget_retarget_face,
	 VIEW3D_PT_retarget_retarget_fingers,
	 VIEW3D_PT_retarget_retarget_arms_IK,
	 VIEW3D_PT_retarget_retarget_arms,
	 VIEW3D_PT_retarget_retarget_spine,
	 VIEW3D_PT_retarget_retarget_leg_IK,
	 VIEW3D_PT_retarget_retarget_leg,
	 VIEW3D_PT_retarget_retarget_root,

     Retarget_pie_menu,
     VIEW3D_MT_PIE_Retarget,
)


def register_classes():
    bpy.types.Scene.retarget_bind_to = bpy.props.PointerProperty(type=bpy.types.Object,
                                                                name="Bind To",
                                                                poll=poll_armature_bind_to,
                                                                description="This armature will drive another one.")
                                                         
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.VIEW3D_MT_pose_context_menu.append(pose_context_options)
    bpy.types.VIEW3D_MT_object_context_menu.append(pose_context_options)
    bpy.types.VIEW3D_MT_armature_context_menu.append(armature_context_options)
    bpy.types.DOPESHEET_HT_header.append(action_header_buttons)


def unregister_classes():
    
    bpy.types.VIEW3D_MT_pose_context_menu.remove(pose_context_options)
    bpy.types.VIEW3D_MT_object_context_menu.remove(pose_context_options)
    bpy.types.VIEW3D_MT_armature_context_menu.remove(armature_context_options)
    bpy.types.DOPESHEET_HT_header.remove(action_header_buttons)
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.retarget_bind_to

