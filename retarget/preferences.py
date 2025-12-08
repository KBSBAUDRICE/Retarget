import os

import bpy
from bpy.props import StringProperty
import rna_keymap_ui
from . import preset_handler
from bpy.types import Operator, AddonPreferences



class RetargetToClipboard(Operator):
    """Copy Retarget Preferences to the clipboard"""
    bl_idname = "wm.retarget_to_clipboard"
    bl_label = "Copy Stuff to the clipboard"

    clip_text: StringProperty(description="Text to Copy", default="")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        context.window_manager.clipboard = self.clip_text
        return {'FINISHED'}

class RetargetPrefs(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        box = column.box()
        col = box.column()

        row = col.row()
        row.label(text="Useful Paths:")

        row = col.row()
        split = row.split(factor=0.15, align=False)
        sp_col = split.column()
        sp_col = split.column()

        row = col.row()
        split = row.split(factor=0.15, align=False)
        sp_col = split.column()
        sp_col = split.column()

        script_path = os.path.dirname(__file__)
        script_path = os.path.join(script_path, 'rig_mapping', 'unreal_mapping.py')
        op = sp_col.operator(RetargetToClipboard.bl_idname, text='Path of "Unreal Mapping" to Clipboard')
        op.clip_text = script_path

        col.separator()
        row = col.row()
        split = row.split(factor=0.15, align=False)
        sp_col = split.column()
        sp_col = split.column()
        op = sp_col.operator(RetargetToClipboard.bl_idname, text='Path of stored rig presets')
        op.clip_text = preset_handler.get_retarget_dir()

def register_classes():
    bpy.utils.register_class(RetargetPrefs)
    bpy.utils.register_class(RetargetToClipboard)

def unregister_classes():
    bpy.utils.unregister_class(RetargetPrefs)
    bpy.utils.unregister_class(RetargetToClipboard)
