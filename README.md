# Retarget
Retarget it's a Fork of Expy Kit (https://github.com/pKrime/Expy-Kit) with many new feature 

# New

- Support of Blender 5, (compatibility, action, slot)
- Work in object mode 
- Multi selection support
- Apply scale without breaking the animation
- Vroid preset
- Transfert pose
- Add Root Bone
- Align bone
- Multiple selection support

Lots of bug fixes and more

----------------------
here's all the feature
----------------------

# Binding

 - Bind to Active Armature / Transfer Pose
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
 - Rename Actions from .fbx data
 - Add Root Bone
 - Transfer Root Motion


# FAQ

- This addon does not support Expy kit preset, you must make changes (the Python file) of the second line  from 
   "skeleton = bpy.context.object.data.expykit_retarget " to "skeleton = bpy.context.object.data.retarget_retarget"

- Always check the scale of your armatures 2 before aligning the bone

- "Transfer Root Motion" does not work as expected when there is a lot of selection (this is a known issue)
