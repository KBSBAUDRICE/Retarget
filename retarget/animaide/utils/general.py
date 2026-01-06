 

import bpy
import blf

# from curve_tools.support import get_items


def set_animaide_action():
    """Creates an "action" called 'animaide'"""

    action = bpy.data.actions.get('animaide')

    if not action:
        action = bpy.data.actions.new('animaide')
        action.slots.new('OBJECT', "test")
        return action
    
    else:
        return action


def get_all_actions(obj):

    trans_action = getattr(obj.animation_data, 'action', None)

    transform = {'type': 'transform_action',
                 'action': trans_action}

    sk = getattr(obj.data, 'shape_keys', None)
    sk_animation_data = getattr(sk, 'animation_data', None)
    sk_action = getattr(sk_animation_data, 'action', None)

    shape_keys = {'type': 'shape_keys',
                  'action': sk_action}

    if transform or shape_keys:
        return [transform, shape_keys]
    else:
        return


def gradual(key_y, target_y, delta=1.0, factor=0.15):
    """Gradualy transition the value of key_y to target_y"""
    step = abs(key_y - target_y) * (delta * factor)

    if target_y > key_y:
        return key_y + step

    else:
        return key_y - step


def clamp(value, minimum, maximum, to_none=False):
    """Take a value and if it goes beyond the minimum and maximum it would replace it with those."""

    if value <= minimum:
        if to_none is True:
            return None
        else:
            return minimum

    if value >= maximum:
        if to_none is True:
            return None
        else:
            return maximum

    return value


def floor(value, minimum, to_none=False):
    """Take the value and if it goes lower than the minimum it would replace it with it"""
    if value < minimum:
        if to_none is True:
            return None
        else:
            return minimum

    return value


def ceiling(value, maximum, to_none=False):
    """Take the value and if it goes over the maximum it would replace it with it"""
    if value > maximum:
        if to_none is True:
            return None
        else:
            return maximum

    return value


def toggle(to_toggle, value_a, value_b):
    """Change 'to_toggle' to one of the tow values it doesn't have at the moment"""
    if to_toggle == value_a:
        return value_b
    elif to_toggle == value_b:
        return value_a


def add_marker(name, side, frame=0, overwrite=True, del_in_same_frame = False):
    """add reference frames marker"""

    animaide = bpy.context.scene.animaidert
    use_markers = animaide.tool.use_markers

    if not use_markers:
        return

    name = f'{side}{name}'

    markers = bpy.context.scene.timeline_markers
    
    if del_in_same_frame and check_Mark(frame, name):
        return
    
    if overwrite:
        remove_marker(name)
    
    marker = markers.new(name=name, frame=frame)
    return marker


def modify_marker(marker, name='SAME', frame='SAME'):
    if name != 'SAME':
        marker.name = name

    if frame != 'SAME':
        marker.frame = frame

def check_Mark(frame, name):
    markers = bpy.context.scene.timeline_markers

    list_mark = list(markers)
    for marker in list_mark:
        if marker.frame == frame and marker.name == name:
            markers.remove(marker)
            return True
    return False
        
def remove_marker(name):
    """Removes reference frame markers"""

    markers = bpy.context.scene.timeline_markers

    list_mark = list(markers)
    for marker in list_mark:
        if marker.name == name:
            markers.remove(marker)
    return


def switch_aim(aim, factor):
    if factor < 0.5:
        aim = aim * -1
    return aim


def poll(context):
    """Poll used on all the slider operators"""

    selected = get_items(context, any_mode=True)

    area = context.area.type
    return bool((area == 'GRAPH_EDITOR' or
                area == 'DOPESHEET_EDITOR' or
                area == 'VIEW_3D') and
                selected)


def get_items(context, any_mode=False):
    """returns objects"""
    if any_mode:
        if context.mode == 'OBJECT':
            selected = context.selected_objects
            if context.active_object and not selected:
                selected = [context.active_object]
        elif context.mode == 'POSE':
            selected = context.selected_pose_bones
        else:
            selected = None
    else:
        selected = context.selected_objects
        if context.active_object and not selected:
            selected = [context.active_object]

    if context.area.type == 'VIEW_3D':
        return selected
    elif context.space_data.dopesheet.show_only_selected:
        return selected
    else:
        return bpy.data.objects


text_handle = None
bar_color = None
pref_autosave = None
dopesheet_color = None
graph_color = None
nla_color = None


def set_bar_color():
    global bar_color, dopesheet_color, graph_color, nla_color, pref_autosave
    if bar_color is None:
        bar_color = True
        pref_autosave = bpy.context.preferences.use_preferences_save
        dopesheet_color = bpy.context.preferences.themes[0].dopesheet_editor.space.header[:]
        graph_color = bpy.context.preferences.themes[0].graph_editor.space.header[:]
        nla_color = bpy.context.preferences.themes[0].nla_editor.space.header[:]

    h = bpy.context.preferences.themes[0].graph_editor.space.header
    highlight = (h[0]*.9, h[1]*.9, h[2]*.9, 1)
    bpy.context.preferences.use_preferences_save = False
    bpy.context.preferences.themes[0].dopesheet_editor.space.header = highlight
    bpy.context.preferences.themes[0].nla_editor.space.header = highlight
    bpy.context.preferences.themes[0].graph_editor.space.header = highlight


def reset_bar_color():
    if pref_autosave is not None:
        bpy.context.preferences.use_preferences_save = pref_autosave
    if dopesheet_color is not None:
        bpy.context.preferences.themes[0].dopesheet_editor.space.header = dopesheet_color
    if graph_color is not None:
        bpy.context.preferences.themes[0].nla_editor.space.header = graph_color
    if nla_color is not None:
        bpy.context.preferences.themes[0].graph_editor.space.header = nla_color


def add_message(message):

    global text_handle

    def draw_text_callback(info):
        font_id = 0
        blf.position(font_id, 5, 80, 0)
        blf.size(font_id, 30)
        blf.color(font_id, 1, 1, 1, .5)
        blf.draw(font_id, info)

    if text_handle is None:
        # set_bar_color(0.5, 0.3, 0.2, 1)
        text_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_text_callback, (message,),
            'WINDOW', 'POST_PIXEL')


def remove_message():
    global text_handle

    reset_bar_color()
    if text_handle:
        bpy.types.SpaceView3D.draw_handler_remove(text_handle, 'WINDOW')
    text_handle = None
