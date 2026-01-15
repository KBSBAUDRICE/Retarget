# Retarget 
Retarget it's a Fork of Expy Kit (https://github.com/pKrime/Expy-Kit) and Animaide (https://github.com/aresdevo/animaide) since v2.0.0 with many new feature (COMPATIBLE ONLY WITH BLENDER 5 AND HIGHER VERSIONS).
It is a retargeting tool, with many presets (Mixamo, Unreal, Vroid, etc.) to make the task easier. You can add your own preset in the N-panel

# TUTO

https://youtu.be/iXRW5t6eEjE

# Blender Extensions

https://extensions.blender.org/add-ons/retarget/

# Preview

![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/%7B8D46FC20-1F50-4D72-BA75-776F51371996%7D.png))

![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/%7B8124276C-2028-4A0F-902F-50174347561E%7D.png))

![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/AnimAide.png))

![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/animaide_f.png))

----------------------
# FEATURES
----------------------
# Animaide
- CurveTools
- AnimOffset
- KeyManager

# Binding

 - Bind to Active Armature
 - Apply/disable/Remove constraints
 - Select Constrained Controls
 - Align Bones
  
# Conversion

 - Rigify Game Friendly
 - Renames Bones
 - Extract Metarig
 - Apply As Rest Pose and align the mesh to this new rest pose
 - Apply Scale / Create Scale Offset
 - Merge Head/Tail
  
# Animation

 - Action Range to Scene
 - Adjust Animation
 - Bake Constrained Actions
 - Add Root Bone
 - Transfer Root Motion


# FAQ
- CurveTools allows you to modify selected keyframes even if they are not visible in the dope sheet editor or graph editor.
- Read each tooltip carefully; some actions only affect the current slot, while others affect other animations.

- This addon does not support Expy kit preset, you must make changes of the second line  (preset file) from 
   "skeleton = bpy.context.object.data.expykit_retarget " to "skeleton = bpy.context.object.data.retarget_retarget"
