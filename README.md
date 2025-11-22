# Retarget
Retarget it's a Fork of Expy Kit (https://github.com/pKrime/Expy-Kit) with many new feature.
It is a retargeting tool, with many presets (Mixamo, Unreal, Vroid, etc.) to make the task easier. You can add your own preset in the N-panel

# New

- Support of Blender 5, (compatibility, action, slot)
- Work in object mode 
- Multi selection support
- Apply scale without breaking the animation
- Vroid preset
- Add Root Bone
- Align bone

Lots of bug fixes and more

----------------------
here's all the feature
----------------------

# Binding

 - Bind to Active Armature
 - Apply/disable/Remove constraints
 - Select Constrained Controls
 - Align Bones
  
# Conversion

 - Rigify Game Friendly
 - Revert dots in Names
 - Renames Bones
 - Extract Metarig
 - Apply Scale / Create Scale Offset
 - Merge Head/Tail
  
# Animation

 - Action Range to Scene
 - Bake Constrained Actions
 - Add Root Bone
 - Transfer Root Motion


# FAQ

- Read each tooltip carefully; some actions only affect the current slot, while others affect other animations.

- This addon does not support Expy kit preset, you must make changes of the second line  (preset file) from 
   "skeleton = bpy.context.object.data.expykit_retarget " to "skeleton = bpy.context.object.data.retarget_retarget"

- "Transfer Root Motion" does not work as expected when there is a lot of selection (this is a known issue)
