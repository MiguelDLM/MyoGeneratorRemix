#  MyoGeneratorRemix Blender Add-On
Blender add-on to create volumetric muscles   

MyogeneratorRemix is a re-imagination of the MyoGenerator add-on created by Eva C. Herbst and Niccolo Fioritti taking advantage of the new features of Blender and specially of the Geometry Nodes. This version of the add-on has been updated to work with Blender 4.3.2 and includes a number of new features, improvements, and bug fixes present in the original add-on.

:pencil: Read the original paper from the Herbst et al. 2022 [paper](https://doi.org/10.1098/rsos.220519), wrote with Luke E. Meade, Stephan
Lautenschlager, and Torsten M. Scheyer. If you use this method, please cite the original paper (Herbst et al. 2022) regarding the method. The Add-on  can be cited as:

```
Díaz de León-Muñoz, E. M. (2025). MyoGeneratorRemix: A Blender Add-On for Creating Volumetric Muscles [Computer software]. Retrieved from
[Github](https://github.com/MiguelDLM/MyoGeneratorRemix).
```


## Note about Alfa Release 0.1

The curve is not being configured correctly in the Geometry Nodes, for this reason, the user must configure the curve manually by selecting the *muscle object* and going to *Modifiers* in the *Properties Panel* and selecting the *Curve* option in the *Geometry Nodes* modifier. The Curve is already there, the user only needs to select it and press *Enter*.

![Curve Fix](https://github.com/MiguelDLM/MyoGeneratorRemix/blob/main/curve-fix.png)
## 

## Output of Add-On
- muscle volume mesh, origin area, insertion area, origin boundary loop, insertion boundary loop
- .csv file with all of the muscle metrics (name, origin area, insertion area, origin centroid, insertion centroid, linear length, muscle length, muscle volume). Linear length is calculated as the Euclidean distance between origin and insertion centroids, muscle length is calculated as the length of the curve of the Blender muscle (sum of edge lengths constituting the curve). Headers are included, and multiple muscles are written to the same file as rows.
- The add-on automatically organizes your muscle components (attachment areas and volume) inside collections


## Notes for User
- Start with a new Blender file, and import your bone meshes.
- Do not rename the collections. The default Blender collection is named "Collection" and the muscle hierarchies will be created as part of this collection. The bone meshes you import should also automatically be part of this collection.
- Ensure bone meshes are clean (manifold, no intersecting edges and faces) and of suitably high resolution to be able to select attachment areas with the desired precision

- Ensure that the model in your scene is at the correct scale (i.e. if you took a measurement tool, the resulting dimensions would be correct). This is necessary because the add-on will apply scaling to the muscle areas etc, in other words it assumes the geometry as visible in the scene is the correct dimension. At the beginning of the add-on, the scale, rotation, and location of all objects is applied (setting scale = 1, and rotations and locations = to 0).
- Make sure a continuous area is selected for your muscle attachments (no accidental unselected faces in the general attachment area, no faces only connected to other faces by single vertex)
- For attachment select, we recommend using the lasso tool, which can be accessed by left clicking on the select box and selecting the lasso tool
- All objects must be visible for the muscle volume updating to work!


## Summary of Add-on Steps

![AddOn](https://github.com/MiguelDLM/MyoGeneratorRemix/blob/main/Myogenerator_Addon_Fig_lowres.png)

1. User enters folder and file name for saving data.
2. User enters muscle name
3. Code creates empty with that muscle name
4. User selects bone on which muscle originates
5. Bone becomes active object, code switches to edit mode
6. User draws on muscle origin by selecting faces, submits 
7. Code duplicates these faces, separates from bone to create new object representing attachment area, renames this object as “[muscle name] origin”. Then, code convert the mesh into curves
8. Repeat steps 4-6 for insertion
9. Curve is created by making a nurbs path between the centroids of the origin and insertion attachment sites. A Geometry Nodes modifier is added to the curve to create a tube volume. This GN modifier creates a loft transition between the origin and insertion surfaces along the curve.
10. Since usually the origin and insertion boundaries are not equal in size and number of vertices, the connection can be not as expected, for this reason, the following options can be used to fix this:
  -Rotate the vertex of the origin and insertion boundary loops to correctly link them without twisted geometry
  -Swap the origin and insertion boundary (only if the origin and insertion are placed in the wrong order)
  -Switch the direction of the vertices. Sometimes the vertices for one object are clockwise and for the other object are counterclockwise. The conections work by connecting the vertices in the same order, so if the vertices are not connected correctly, the user can switch the direction of the vertices of one of the objects.

11. The user can define the mesh resolution by adjusting the number of subdivisions and resampling.
12. Code converts curve to mesh
13. Code resets add-on so that user can create new muscle.
14. User can adjust muscle meshes iteratively - e.g., once a second muscle is made, the first muscle belly can be scaled to meet the second muscle, etc.
25. Code calculates volumes of all muscles in the muscles collection, adds metric to .csv file. Volumes can be updated at any point. If you change a muscle (e.g. scale the muscle belly etc), click "calculate muscle parameters" to update the csv file.


 
## Add-on Installation
 
 The add-on currently works for versions 4.2 Blender and above which can be installed [here](https://www.blender.org/).
 
 To install the add-on, download this repository, extract all, zip the Add-on folder, and then follow the instructions [here](https://docs.blender.org/manual/en/latest/editors/preferences/addons.html), selecting the zipped Add-on Folder
 
