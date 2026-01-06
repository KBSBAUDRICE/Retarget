
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty
import rna_keymap_ui
from . import preset_handler
from bpy.types import Operator, AddonPreferences
from .animaide import anim_offset, key_manager, utils, ui

#-------------- animaide
addon_name = __package__

key_manager_pref = ''
anim_offset_pref = ''


def add_key_manager_header():
    global key_manager_pref
    for cls in key_manager.ui.header_classes:
        bpy.utils.register_class(cls)
    
    bpy.types.DOPESHEET_MT_editor_menus.append(key_manager.ui.draw_key_manager)
    bpy.types.GRAPH_MT_editor_menus.append(key_manager.ui.draw_key_manager)
    key_manager_pref = 'HEADERS'


def remove_key_manager_header():
    global key_manager_pref
    for cls in key_manager.ui.header_classes:
        bpy.utils.unregister_class(cls)

    bpy.types.DOPESHEET_MT_editor_menus.remove(key_manager.ui.draw_key_manager)
    bpy.types.GRAPH_MT_editor_menus.remove(key_manager.ui.draw_key_manager)
    key_manager_pref = ''


def add_key_manager_panel():
    global key_manager_pref
    for cls in key_manager.ui.panel_classes:
        bpy.utils.register_class(cls)
    key_manager_pref = 'PANEL'


def remove_key_manager_panel():
    global key_manager_pref
    for cls in key_manager.ui.panel_classes:
        bpy.utils.unregister_class(cls)
    key_manager_pref = ''

def  add_key_manager_both():
    global key_manager_pref
    if key_manager_pref == 'HEADERS':
        add_key_manager_panel()
    else:
        add_key_manager_header()
    key_manager_pref = 'BOTH'

def add_anim_offset_panel():
    global anim_offset_pref
    for cls in anim_offset.ui.panel_classes:
        bpy.utils.register_class(cls)
    anim_offset_pref = 'PANEL'


def remove_anim_offset_panel():
    global anim_offset_pref
    for cls in anim_offset.ui.panel_classes:
        bpy.utils.unregister_class(cls)
    anim_offset_pref = ''


def add_anim_offset_header():
    global anim_offset_pref
    
    bpy.types.DOPESHEET_MT_editor_menus.append(anim_offset.ui.draw_anim_offset_mask)
    bpy.types.GRAPH_MT_editor_menus.append(anim_offset.ui.draw_anim_offset_mask)
    anim_offset_pref = 'HEADERS'


def remove_anim_offset_header():
    global anim_offset_pref
    
    bpy.types.GRAPH_MT_editor_menus.remove(anim_offset.ui.draw_anim_offset_mask)
    bpy.types.DOPESHEET_MT_editor_menus.remove(anim_offset.ui.draw_anim_offset_mask)
    anim_offset_pref = ''

def add_anim_offset_both():
    global anim_offset_pref
    if anim_offset_pref == 'HEADERS':
        add_anim_offset_panel()
    else:
        add_anim_offset_header()
    anim_offset_pref = 'BOTH'

#--------------------------

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
    bl_idname = addon_name

    #-------------------------------------------animaide
    def key_manager_update(self, context):
        global key_manager_pref

        if self.key_manager_ui == key_manager_pref:
            return
        
        tmp = key_manager_pref

        if self.key_manager_ui == 'HEADERS':
            remove_key_manager_panel()
            if tmp != 'BOTH':
                if self.anim_offset_ui == 'HEADERS':
                    remove_anim_offset_header()
                add_key_manager_header()
                if self.anim_offset_ui == 'HEADERS':
                    add_anim_offset_header()

        elif self.key_manager_ui == 'PANEL':
            remove_key_manager_header()
            if tmp != 'BOTH':
                add_key_manager_panel()

        elif self.key_manager_ui == 'BOTH':
            add_key_manager_both()


    def anim_offset_update(self, context):
        global anim_offset_pref

        if self.anim_offset_ui == anim_offset_pref:
            return
        
        tmp = anim_offset_pref

        if self.anim_offset_ui == 'HEADERS':
            remove_anim_offset_panel()
            if tmp != 'BOTH':
                add_anim_offset_header()

        elif self.anim_offset_ui == 'PANEL':
            remove_anim_offset_header()
            if tmp != 'BOTH':
                add_anim_offset_panel()

        elif self.anim_offset_ui == 'BOTH':
            add_anim_offset_both()


    def toggle_tool_markers(self, context):
        tool = context.scene.animaidert.tool

        if self.ct_use_markers:
            if tool.left_ref_frame > 0:
                utils.add_marker(name='', side='L', frame=tool.left_ref_frame)

            if tool.right_ref_frame > 0:
                utils.add_marker(name='', side='R', frame=tool.right_ref_frame)
        else:
            for name in ['L', 'R']:
                utils.remove_marker(
                    name=name)
        return

    # def info_panel_update(self, context):
    #     if self.info_panel:
    #         for cls in ui.info_classes:
    #             bpy.utils.register_class(cls)
    #     else:
    #         for cls in reversed(ui.info_classes):
    #             bpy.utils.unregister_class(cls)

    key_manager_ui: EnumProperty(
        items=[('PANEL', 'Panel', 'Choose if you want "Key Manager" on a panel', '', 1),
               ('HEADERS', 'Headers', 'Choose if you want "Key Manager" tools on headers', '', 2),
               ('BOTH', 'Both', '', '', 3)],
        name="Key Manager",
        default='PANEL',
        update=key_manager_update
    )

    anim_offset_ui: EnumProperty(
        items=[('PANEL', 'Panel', 'Choose if you want "Anim Offset" on a panel', '', 1),
               ('HEADERS', 'Headers', 'Choose if you want "Anim Offset" tools on headers', '', 2),
               ('BOTH', 'Both', '', '', 3)],
        name="Anim Offset",
        default='HEADERS',
        update=anim_offset_update
    )

    tool_on_release: BoolProperty(default=True,
                                  description='Changes how the tools modal work')

    ct_use_markers: BoolProperty(default=True,
                                 description='use markers for the reference frames',
                                 update=toggle_tool_markers)

    ao_fast_offset: BoolProperty(default=False)

    # info_panel: BoolProperty(default=True,
    #                          update=info_panel_update)

    #------------------------------------------

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
        col.label(text="", icon="KEYINGSET")

        wm = context.window_manager
        kc = wm.keyconfigs.user
        if not kc:
            col.label(text="No user keyconfig available", icon='ERROR')
            return

        km = kc.keymaps.get('3D View')
        add_key = True
        if km:
            for kmi in km.keymap_items:
                if kmi.idname == "object.retarget_pie_menu":
                    col.context_pointer_set("keymap", km)
                    rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
                    add_key = False
                    
        if add_key:
            # No keymap found, show add button
            row = col.row()
            row.operator(add_keymap.bl_idname, 
                        text="Add Keyboard Shortcut", 
                        icon='ADD')
        
        #-------------------------animaide

        col = box.column()  
        col.label(text="Anim Aide Parameter:")
        layout.use_property_split = True
        layout.use_property_decorate = True

        layout.prop(self, "anim_offset_ui", text="Anim Offset on")
        layout.prop(self, "key_manager_ui", text="Key Manager on")
        col = layout.column(heading='Curve Tools')
        col.prop(self, 'tool_on_release', text='Activate on mouse release', toggle=False)
        col.prop(self, 'ct_use_markers', text='Use markers', toggle=False)
        col = layout.column(heading='Anim Offset')
        col.prop(self, 'ao_fast_offset', text='Fast calculation', toggle=False)

        #---------------------
        
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
                "object.retarget_pie_menu",
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
