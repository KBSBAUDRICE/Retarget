# Retarget
Retarget it's a Fork of Expy Kit (https://github.com/pKrime/Expy-Kit) with many new feature.
It is a retargeting tool, with many presets (Mixamo, Unreal, Vroid, etc.) to make the task easier. You can add your own preset in the N-panel

[![IMAGE ALT TEXT HERE](https://img.youtube.com/vi/iXRW5t6eEjE&t/0.jpg)](https://www.youtube.com/watch?v=iXRW5t6eEjE&t)
https://youtu.be/iXRW5t6eEjE

----------------------
# FEATURES
----------------------

# Binding

 - Bind to Active Armature
 - Apply/disable/Remove constraints
 - Select Constrained Controls
 - Align Bones
  
# Conversion

 - Rigify Game Friendly
 - Renames Bones
 - Extract Metarig
 - Apply Scale / Create Scale Offset
 - Merge Head/Tail
  
# Animation

 - Action Range to Scene
 - Adjust Animation
 - Bake Constrained Actions
 - Add Root Bone
 - Transfer Root Motion


# FAQ

- Read each tooltip carefully; some actions only affect the current slot, while others affect other animations.

- This addon does not support Expy kit preset, you must make changes of the second line  (preset file) from 
   "skeleton = bpy.context.object.data.expykit_retarget " to "skeleton = bpy.context.object.data.retarget_retarget"
