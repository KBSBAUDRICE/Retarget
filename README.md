# Retarget 
Retarget it's a Fork of Expy Kit (https://github.com/pKrime/Expy-Kit) and Animaide (https://github.com/aresdevo/animaide) since v2.0.0 with many new feature (COMPATIBLE ONLY WITH BLENDER 5 AND HIGHER VERSIONS).
It is a retargeting tool, with many presets (Mixamo, Unreal, Vroid, MMD etc.) to make the task easier. You can add your own preset in the N-panel

# TUTO
- https://www.youtube.com/playlist?list=PLdUXkJ3Y-ZqGYr9qKwNFjUItzbfWL3Has

# Blender Extension
- https://extensions.blender.org/add-ons/retarget/

# PREVIEW


![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/%7B35C7CD33-9A89-41FC-B115-91FD731ADDAF%7D.png)

![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/Image%20du%20presse-papiers.jpg)

![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/AnimAide.png)

![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/animaide_f.png)

![Picture](https://github.com/KBSBAUDRICE/Retarget/blob/main/Image/action_manager.png)
----------------------
# FEATURES
----------------------
# Animaide

- CurveTools
- AnimOffset
- KeyManager

# Binding

 - Bind to Active Armature
 - Unbind Armature
 - Apply/disable/Remove constraints 
 - Select Constrained Controls
 - Align Bones
  
# Conversion

 - Rigify Game Friendly
 - Renames Bones (rig convertion)
 - Extract Metarig (convert any humanoid rig to rigify)
 - Apply As Rest Pose and align the mesh to this new rest pose
 - Apply Scale / Create Scale Offset ( AND FIX THE ANIMATION)
 - Merge Head/Tail
  
# Animation

 - Action Range to Scene
 - Adjust Animation
 - Bake Constrained Actions ; "Include similar actions" allow you to bake multiple actions at once
 - Add Root Bone
 - Transfer Root Motion

# Rigging

- Surface Rig: Quickly add a rig on the surface of a mesh and on grease pencil


# Action Manager 
For managing actions in Blend files and the resource explorer. It offers 5 modes; see this tutorial for more information. 


# LOCATION

It can be found in the context menu (right click) 


# FAQ
- CurveTools allows you to modify selected keyframes even if they are not visible in the dope sheet editor or graph editor.
- Read each tooltip carefully; some actions only affect the current slot, while others affect other animations.

- This addon does not support Expy kit preset, you must make changes of the second line  (preset file) from 
   "skeleton = bpy.context.object.data.expykit_retarget " to "skeleton = bpy.context.object.data.retarget_retarget"

# Special Thank

- pKrime for Expy-Kit
- aresdevo for animaide
- Pullusb for Surface Rig
