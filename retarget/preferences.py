
import bpy
from bpy.props import StringProperty
import rna_keymap_ui
from . import preset_handler, ui
from bpy.types import Operator, AddonPreferences



class RetargetToClipboard(Operator):
    """Open the Path of stored rig presets"""
    bl_idname = "wm.retarget_to_clipboard"
    bl_label = "Open Path"

    clip_text: StringProperty(description="Text to Copy", default="")

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        #context.window_manager.clipboard = self.clip_text
        bpy.ops.wm.path_open(filepath=self.clip_text)
        return {'FINISHED'}

class RetargetPrefs(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        column = layout.column()

        box = column.box()
        col = box.column()
        
        row = col.row()
        split = row.split(factor=0.15, align=False)
        sp_col = split.column()
        sp_col = split.column()

        col.separator()
        row = col.row()
        split = row.split(factor=0.15, align=False)
        sp_col = split.column()
        sp_col = split.column()
        op = sp_col.operator(RetargetToClipboard.bl_idname, text='Open the Path of stored rig presets')
        op.clip_text = preset_handler.get_retarget_dir()

        #shortcut
        col = box.column()  
        col.label(text="Keymap List:", icon="KEYINGSET")
        wm = context.window_manager
        kc = wm.keyconfigs.user
        if not kc:
            col.label(text="No user keyconfig available", icon='ERROR')
            return

        km = kc.keymaps.get('3D View')
        if km:
            for kmi in km.keymap_items:
                if kmi.idname == ui.Retarget_pie_menu.bl_idname:
                    col.context_pointer_set("keymap", km)
                    rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
                    return

        # No keymap found, show add button
        row = col.row()
        row.operator(add_keymap.bl_idname, 
                    text="Add Keyboard Shortcut", 
                    icon='ADD')
        
class add_keymap(Operator):
    bl_idname = "screen.retarget_add_keymap"
    bl_label = "Add Keymap"
    bl_description = "Add keyboard shortcut for Retarget"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    def execute(self, context):
        wm = context.window_manager
        kc = wm.keyconfigs.user
        if kc:
            km = kc.keymaps.get('3D View')
            if not km:
                km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
            kmi = km.keymap_items.new(
                ui.Retarget_pie_menu.bl_idname,
                type='NONE',
                value='PRESS'
            )
        return {'FINISHED'}

def register_classes():
    bpy.utils.register_class(RetargetPrefs)
    bpy.utils.register_class(RetargetToClipboard)
    bpy.utils.register_class(add_keymap)

def unregister_classes():
    bpy.utils.unregister_class(add_keymap)
    bpy.utils.unregister_class(RetargetPrefs)
    bpy.utils.unregister_class(RetargetToClipboard)
