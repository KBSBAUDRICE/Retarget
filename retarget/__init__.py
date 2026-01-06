# ====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation, version 3.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ======================= END GPL LICENSE BLOCK ========================


bl_info = {
    "name": "Retarget",
    "version": (1, 0, 0),
    "author": "KBS DEV",
    "blender": (5, 0, 0),
    "description": "Tools for Character Rig Conversion",
    "category": "Rigging",
}


from . import operators
from . import ui
from . import preferences
from . import preset_handler
from . import properties
from .animaide import animaide_init

import bpy

def register():
    properties.register_classes()
    preferences.register_classes()
    operators.register_classes()
    ui.register_classes()

    preset_handler.install_presets()

    animaide_init.register_classes()

    pref = bpy.context.preferences.addons[ preferences.addon_name].preferences

    if pref.key_manager_ui == 'PANEL':
        preferences.add_key_manager_panel()

    if pref.anim_offset_ui == 'PANEL':
        preferences.add_anim_offset_panel()

    if pref.key_manager_ui == 'HEADERS':
        preferences.add_key_manager_header()

    if pref.anim_offset_ui == 'HEADERS':
        preferences.add_anim_offset_header()

    if pref.key_manager_ui == 'BOTH':
        preferences.add_key_manager_panel()
        preferences.add_key_manager_header()
        preferences.key_manager_pref = 'BOTH'

    if pref.anim_offset_ui == 'BOTH':
        preferences.add_anim_offset_panel()
        preferences.add_anim_offset_header()
        preferences.anim_offset_pref = 'BOTH'


def unregister():
    animaide_init.unregister_classes()

    pref = bpy.context.preferences.addons[preferences.addon_name].preferences

    if pref.key_manager_ui == 'PANEL':
        preferences.remove_key_manager_panel()

    if pref.anim_offset_ui == 'PANEL':
        preferences.remove_anim_offset_panel()

    if pref.key_manager_ui == 'HEADERS':
        preferences.remove_key_manager_header()

    if pref.anim_offset_ui == 'HEADERS':
        preferences.remove_anim_offset_header()

    if pref.key_manager_ui == 'BOTH':
        preferences.remove_key_manager_panel()
        preferences.remove_key_manager_header()

    if pref.anim_offset_ui == 'BOTH':
        preferences.remove_anim_offset_panel()
        preferences.remove_anim_offset_header()

    ui.unregister_classes()
    operators.unregister_classes()
    preferences.unregister_classes()
    properties.unregister_classes()
