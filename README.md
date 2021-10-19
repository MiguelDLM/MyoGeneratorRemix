#  Muscle_Volume_Sculptor
 Blender add-on to create volumetric muscles 
 
 
## NOTES FOR USE:
- Ensure bone meshes are clean (manifold) and of suitably high res to be able to select attachment areas with the desired precision
- Ensure that your face orientation (e.g. normals) is correct. You can check this by selecting Overlay > Geometry > Face orientation. You can change normals in Edit Mode with Mesh > Normals > Recalculate outside
- Make sure a continuous area is selected for your muscle attachments (no accidental unselected faces in the general attachment area, no faces only connected to other faces by single vertex)
- For attachment select, we recommend using the lasso tool, which can be accessed by left clicking on the select box and selecting the lasso tool


## Summary of Add-on Steps

1. User enters muscle name
2. Code creates empty with that muscle name
3. User selects bone on which muscle originates
4. Bone becomes active object, code switches to edit mode
5. User draws on muscle origin by selecting faces, submits 
6. Code duplicates these faces, separates from bone to create new object representing attachment area, renames this object as “[muscle name] origin”. Then, code selects outer edges, duplicates, makes new object to create boundary loop of attachment, renames this as “[muscle name] origin boundary”. Objects are parented to muscle empty.
7. Repeat steps 4-6 for insertion
8.Curve is created by making a nurbs path between the centroids of the origin and insertion attachment sites. Curve is beveled with the origin boundary loop as a cross section (origin boundary loop is first duplicated and reoriented so that it maintains most of its shape when projected into 2D, then converted to a curve)
9. The curve template has 5 points - beginning and end at centroids of origins and insertions , then points along average normal of origin and insertion, at a distance of .2L from centroid, where L is linear distance between centroids. The 5th point is generated between the points along the normals.
10. The user adjusts tilt of curve, making sure the cross section shape aligns with the origin shape.
11. User adjusts points of curve to get desired curvature (do not move endpoints!)
12. User adjusts bevel extent (goal is to have the end loops of curve volume lined up with origin and insertion so that the vertices can be connected with new faces without any intersections).  **Do not invert bevel ends! (e.g bevel start should *not* be > bevel end)**
13. Code converts curve to mesh
14. User scales edge loops to get muscle shape (e.g. taper or expand insertion, change muscle belly size, etc)
15. Code joins muscle curve volume and boundary loops, bridges edge loops, duplicates origin and insertion areas, joins with muscle curve volume to cap ends, removes duplicate edges at join seams, renames to “[muscle name] volume”
16. Click "calculate volumes", then move on to next muscle. All muscle metrics are stored in a .csv file, so you can work on some muscles in one session, close Blender, then continue with the remaining muscles in a different session.
17. **Extra steps if your muscle has a very flat attachment (I.e. muscle is more parallel rather than perpendicular to bone) and you are unable to line up boundary loops**.
  - Make sure bevel goes all the way to the end on the side of the muscle that has the flat attachment.
  - *If you can still align one end nicely:* perform all steps including “join muscle”. This will result in one nice end and one messy one. Now go and delete the vertices up to the edge loop where you ended your muscle volume (see SI Figure #) to get rid of messy geometry. Then, select this edge loop (select one edge, then go to Select > Edge loop, or use ALT + RMB) and then press F to cap the end. Move and scale the end so that the muscle end intersects completely with the bone. Preferably, don’t let it point out the other side. If it does, make sure that piece is separate from the actual muscle mesh you want to keep (not connected around the side of the bone). Once the muscle end completely intersects the bone, with the muscle active, go to to modifiers > Boolean > Boolean intersection. Select the bone with the eyedropper tool in the “object” field. Click apply. If there is a piece of muscle mesh that jutted out the other side of the bone, delete this in edit mode. 
  - *If both ends are “flat”:* perform all steps except “join muscle”. Then perform steps listed above, starting with selecting the open end loops and filling them. 

**Note**: If you aligned the muscle nicely with the bevels and curvature there should not be any issues with messy geometry (e.g. edges crossing each other). However, if you have a very tight curve in your muscle, of if you used Boolean operations, you could end up with messy geometry. Using Mesh > Clean Up > Merge by distance and playing around with the slider can help clean this up, but be careful because it can smooth over some of the geometry. You can also use Voxel remeshing in Sculpt mode to get a better mesh (since the Boolean intersection operation can result in faces with different number of edges).


 
# Add-on Installation
 
 The add-on currently works for versions 2.91.0 - 2.93.0. Blender can be installed [here](https://www.blender.org/).
 
 To install the add-on, download the Add-on Folder from this repository (make sure it is zipped) and then follow the instructions [here](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html).
 

