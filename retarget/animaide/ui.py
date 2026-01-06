 

from bpy.types import Panel, Menu
from .curve_tools.ui import blend_button


# class ANIMAIDERT_PT_help:
#     bl_label = "Help"
#     bl_region_type = 'UI'
#     bl_category = 'AnimAideRT'
#     bl_options = {'DEFAULT_CLOSED'}
#
#     def draw(self, context):
#
#         layout = self.layout
#
#         row = layout.row(align=True)
#
#         row.operator('anim.retarget_aide_manual', text='', icon='HELP', emboss=False)
#         row.operator('anim.retarget_aide_demo', text='', icon='FILE_MOVIE', emboss=False)


# class ANIMAIDERT_PT_info:
#     bl_label = "Info"
#     bl_region_type = 'UI'
#     bl_category = 'AnimAideRT'
#
#     def draw(self, context):
#
#         layout = self.layout
#
#         layout.label(text='-Anim-offset and Key-manager')
#         layout.label(text='can now be put on the headers')
#         layout.label(text='instead of the panels.')
#         layout.label(text='-that and other preferences are')
#         layout.label(text='now located in the addon tab')
#         layout.label(text='in Blender Preferences.')
#         layout.label(text='Because of that Blender')
#         layout.label(text='will remember them after')
#         layout.label(text='you quit.')
#         layout.label(text='-This info panel can also')
#         layout.label(text='be removed in the addon')
#         layout.label(text='preferences.')
#         layout.label(text='Find more information at:')
#         layout.label(text='https://github.com/aresdevo/animaide')


# class ANIMAIDERT_PT_info_3d(Panel, ANIMAIDERT_PT_info):
#     bl_idname = 'ANIMAIDERT_PT_info_3d'
#     bl_space_type = 'VIEW_3D'
#
#
# class ANIMAIDERT_PT_info_ge(Panel, ANIMAIDERT_PT_info):
#     bl_idname = 'ANIMAIDERT_PT_info_ge'
#     bl_space_type = 'GRAPH_EDITOR'
#
#
# class ANIMAIDERT_PT_info_de(Panel, ANIMAIDERT_PT_info):
#     bl_idname = 'ANIMAIDERT_PT_info_de'
#     bl_space_type = 'DOPESHEET_EDITOR'


class ANIMAIDERT_MT_operators(Menu):
    bl_idname = 'ANIMAIDERT_MT_menu_operators'
    bl_label = "AnimAideRT"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout

        if context.area.type == 'VIEW_3D':
            layout.menu('ANIMAIDERT_MT_curve_tools', text='On Frame Curve Tools')
            layout.separator()
            layout.menu('ANIMAIDERT_MT_anim_offset')

        elif context.area.type == 'DOPESHEET_EDITOR':
            layout.operator('wm.call_menu_pie', text="Pie Anim Aide").name = 'ANIMAIDERT_MT_PIE_Retarget_anim_aide'
            layout.menu('ANIMAIDERT_MT_anim_offset')
            layout.menu('ANIMAIDERT_MT_anim_offset_mask')

        elif context.area.type == 'GRAPH_EDITOR':
            layout.operator('wm.call_menu_pie', text="Pie Anim Aide").name = 'ANIMAIDERT_MT_PIE_Retarget_anim_aide'
            layout.menu('ANIMAIDERT_MT_curve_tools')
            layout.menu('ANIMAIDERT_MT_tweak')
            layout.separator()
            layout.menu('ANIMAIDERT_MT_anim_offset')
            layout.menu('ANIMAIDERT_MT_anim_offset_mask')


def draw_menu(self, context):
    if context.mode == 'OBJECT' or context.mode == 'POSE':
        layout = self.layout
        layout.menu('ANIMAIDERT_MT_menu_operators')


menu_classes = (
    ANIMAIDERT_MT_operators,
)

# info_classes = (
#     ANIMAIDERT_PT_info_3d,
#     ANIMAIDERT_PT_info_ge,
#     ANIMAIDERT_PT_info_de,
# )
