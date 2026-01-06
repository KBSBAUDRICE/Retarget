 

import bpy
from . import support
from bpy.types import Panel, Menu, Operator


class ANIMAIDERT_PT:
    bl_label = "Anim Offset"
    bl_region_type = 'UI'
    bl_category = 'AnimAideRT'

    def draw(self, context):

        anim_offset = context.scene.animaidert.anim_offset
        mask_in_use = context.scene.animaidert.anim_offset.mask_in_use

        layout = self.layout

        # layout.label(text='Now Anim Offset buttons')
        # layout.label(text='are in the timeline')
        # layout.label(text='header next to Animaide')
        # layout.label(text='menu')

        if support.magnet_handlers in bpy.app.handlers.depsgraph_update_post:
            layout.operator("anim.retarget_aide_deactivate_anim_offset", text='Deactivate', depress=True, icon='TEMP')
        else:
            layout.operator("anim.retarget_aide_activate_anim_offset", text='Activate', icon='TEMP')

        row = layout.row(align=True)

        if context.area.type != 'VIEW_3D' or context.area.type != 'NLA_EDITOR':

            if mask_in_use:
                row.operator("anim.retarget_aide_delete_anim_offset_mask", text='Deactivate Mask', depress=True, icon='SELECT_SUBTRACT')
                sub = row.row(align=True)
                sub.active = True
                op = sub.operator("anim.retarget_aide_add_anim_offset_mask", text='', icon='GREASEPENCIL')
                op.sticky = True

            else:
                op = row.operator("anim.retarget_aide_add_anim_offset_mask", text='Mask', icon='SELECT_SUBTRACT')
                op.sticky = False
                sub = row.row(align=True)
                sub.active = False

            sub.operator('anim.retarget_aide_anim_offset_settings', text='', icon='PREFERENCES', emboss=True)

        # row = layout.row(align=False)
        # row.active = status
        # sub.operator('anim.retarget_aide_anim_offset_settings', text='', icon='PREFERENCES', emboss=True)
        # sub.popover(panel="ANIMAIDERT_PT_preferences", text="")

        # if support.magnet_handlers in bpy.app.handlers.depsgraph_update_post:
        #     row.operator("anim.retarget_aide_deactivate_anim_offset", text='Deactivate', depress=True, icon='OVERLAY')
        # else:
        #     row.operator("anim.retarget_aide_activate_anim_offset", text='Activate', icon='OVERLAY')

        # row.operator('anim.retarget_aide_anim_offset_settings', text='', icon='PREFERENCES', emboss=True)
        #
        # row = layout.row(align=True)
        #
        # if context.area.type != 'VIEW_3D':
        #     mask_in_use = context.scene.animaidert.anim_offset.mask_in_use
        #     if mask_in_use:
        #         name = 'Modify Mask'
        #         depress = True
        #
        #     else:
        #         name = 'Mask'
        #         depress = False
        #
        #     row.operator("anim.retarget_aide_add_anim_offset_mask", text=name, depress=depress, icon='SELECT_SUBTRACT')
        #     row.operator("anim.retarget_aide_delete_anim_offset_mask", text='', icon='TRASH')
        # if mask_in_use:
        #     layout.label(text='Mask blend interpolation:')
        #     row = layout.row(align=True)
        #     row.prop(anim_offset, 'easing', text='', icon_only=False)
        #     row.prop(anim_offset, 'interp', text='', expand=True)


class ANIMAIDERT_PT_anim_offset_3d(Panel, ANIMAIDERT_PT):
    bl_idname = 'ANIMAIDERT_PT_anim_offset_3d'
    bl_space_type = 'VIEW_3D'


class ANIMAIDERT_PT_anim_offset_ge(Panel, ANIMAIDERT_PT):
    bl_idname = 'ANIMAIDERT_PT_anim_offset_ge'
    bl_space_type = 'GRAPH_EDITOR'


class ANIMAIDERT_PT_anim_offset_de(Panel, ANIMAIDERT_PT):
    bl_idname = 'ANIMAIDERT_PT_anim_offset_de'
    bl_space_type = 'DOPESHEET_EDITOR'


class ANIMAIDERT_MT_anim_offset(Menu):
    bl_idname = 'ANIMAIDERT_MT_anim_offset'
    bl_label = "Anim Offset"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

        layout.operator('anim.retarget_aide_activate_anim_offset', text='On')
        layout.operator('anim.retarget_aide_deactivate_anim_offset', text='Off')


class ANIMAIDERT_MT_anim_offset_mask(Menu):
    bl_idname = 'ANIMAIDERT_MT_anim_offset_mask'
    bl_label = "Anim Offset Mask"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

        if context.area.type != 'VIEW_3D':
            layout.operator('anim.retarget_aide_add_anim_offset_mask', text='Add/Modify')
            layout.operator('anim.retarget_aide_delete_anim_offset_mask', text='Delete')

#pie menu


class ANIMAIDERT_MT_PIE_Retarget_anim_aide(Menu):
    bl_idanme = 'ANIMAIDERT_MT_PIE_Retarget_anim_aide'
    bl_label = "ANIM AIDE"

    def draw(self, context):
        layout = self.layout

        pie = layout.menu_pie()
        
        
        gap = pie.column()

        menu = gap.box()
        my_text = "Curve Tools A".center(40)
        menu.label(text= my_text, icon='IPO_SINE')
        menu.operator("anim.retarget_aide_ease_to_ease")
        menu.operator("anim.retarget_aide_tween")
        menu.operator("anim.retarget_aide_blend_ease")
        menu.operator("anim.retarget_aide_ease")
        menu.operator("anim.retarget_aide_blend_neighbor")
        menu.operator("anim.retarget_aide_scale_average")
        menu.operator("anim.retarget_aide_push_pull")
        menu.operator("anim.retarget_aide_blend_frame")

        gap = pie.column()

        menu = gap.box()
        my_text = "Curve Tools B".center(40)
        menu.label(text= my_text, icon='IPO_QUAD')
        menu.operator("anim.retarget_aide_scale_left")
        menu.operator("anim.retarget_aide_scale_right")
        menu.operator("anim.retarget_aide_wave_noise")
        menu.operator("anim.retarget_aide_smooth")
        menu.operator("anim.retarget_aide_blend_offset")
        menu.operator("anim.retarget_aide_time_offset")
        menu.operator("anim.retarget_aide_blend_default")
        menu.operator('anim.retarget_aide_blend_infinite')

        gap = pie.column()

        menu = gap.box()
        my_text = "ANIM OFFSET".center(40)
        menu.label(text= my_text, icon='COLOR')
        menu.operator('anim.retarget_aide_activate_anim_offset', text='AnimOffset Without Mask')
        menu.operator('anim.retarget_aide_add_anim_offset_mask', text='Add AnimOffset Mask')
        menu.operator('anim.retarget_aide_delete_anim_offset_mask', text='Delete AnimOffset Mask')
        menu.operator('anim.retarget_aide_deactivate_anim_offset', text='Deactivate AnimOffset')

        gap = pie.column()
       
        menu = gap.box()
        my_text = "AREA".center(40)
        menu.label(text= my_text, icon='WORKSPACE')

        menu.operator("object.retarget_action_to_range", icon = "PREVIEW_RANGE")

        props = menu.operator("wm.context_set_enum", icon = "ACTION" ,text="Dope Sheet Editor")
        props.data_path = "area.ui_type"
        props.value = "DOPESHEET"

        props = menu.operator("wm.context_set_enum", icon = "GRAPH", text="Graph Editor")
        props.data_path = "area.ui_type"
        props.value = "FCURVES"
#---------

class ANIMAIDERT_PT_preferences(Panel):
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'HEADER'
    bl_label = "Anim Offset Settings"
    bl_options = {'HIDE_HEADER'}

    # @classmethod
    # def poll(cls, context):
    #     return support.magnet_handlers in bpy.app.handlers.depsgraph_update_post

    def draw(self, context):
        anim_offset = context.scene.animaidert.anim_offset

        layout = self.layout

        # if support.magnet_handlers not in bpy.app.handlers.depsgraph_update_post:
        #     layout.active = False

        mask_in_use = context.scene.animaidert.anim_offset.mask_in_use
        if not mask_in_use:
            layout.active = False

        # layout.label(text='Settings')
        # layout.separator()
        # layout.prop(anim_offset, 'end_on_release', text='masking ends on mouse release')
        # layout.prop(anim_offset, 'fast_mask', text='Fast offset calculation')
        # if context.area.type != 'VIEW_3D':

        layout.prop(anim_offset, 'insert_outside_keys', text='Auto Key outside margins')
        layout.separator()
        layout.label(text='Mask blend interpolation:')
        row = layout.row(align=True)
        if not mask_in_use:
            row.active = False
        row.prop(anim_offset, 'easing', text='', icon_only=False)
        row.prop(anim_offset, 'interp', text='', expand=True)


def draw_anim_offset(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.separator()

    if support.magnet_handlers in bpy.app.handlers.depsgraph_update_post:
        row.operator("anim.retarget_aide_deactivate_anim_offset", text='', depress=True, icon='TEMP')
    else:
        row.operator("anim.retarget_aide_activate_anim_offset", text='', icon='TEMP')


def draw_anim_offset_mask(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.separator()

    if support.magnet_handlers in bpy.app.handlers.depsgraph_update_post:
        row.operator("anim.retarget_aide_deactivate_anim_offset", text='', depress=True, icon='TEMP')
    else:
        row.operator("anim.retarget_aide_activate_anim_offset", text='', icon='TEMP')

    mask_in_use = context.scene.animaidert.anim_offset.mask_in_use
    if mask_in_use:
        row.operator("anim.retarget_aide_delete_anim_offset_mask", text='', depress=True, icon='SELECT_SUBTRACT')
        op = row.operator("anim.retarget_aide_add_anim_offset_mask", text='', icon='GREASEPENCIL')
        op.sticky = True
        sub = row.row(align=True)
        sub.active = True
    else:
        op = row.operator("anim.retarget_aide_add_anim_offset_mask", text='', icon='SELECT_SUBTRACT')
        op.sticky = False
        sub = row.row(align=True)
        sub.active = False

    sub.popover(panel="ANIMAIDERT_PT_preferences", text="")


menu_classes = (
    ANIMAIDERT_MT_anim_offset,
    ANIMAIDERT_MT_anim_offset_mask,
    ANIMAIDERT_MT_PIE_Retarget_anim_aide,
    ANIMAIDERT_PT_preferences,
)

panel_classes = (
    ANIMAIDERT_PT_anim_offset_3d,
    ANIMAIDERT_PT_anim_offset_ge,
    ANIMAIDERT_PT_anim_offset_de,
)
