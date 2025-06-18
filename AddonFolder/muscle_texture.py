import bpy

def create_muscle_material():
    """
    Create or get the procedural muscle material based on the method described by Ned Poreyra (https://www.artstation.com/artwork/Rb8LO)
    Returns the material object, creating it only if it doesn't exist.
    """
    # Check if material already exists
    existing_material = bpy.data.materials.get("Muscle")
    if existing_material:
        return existing_material
    
    # Create new material
    mat = bpy.data.materials.new(name="Muscle")
    mat.use_nodes = True
    
    # Initialize muscle node group
    return _build_muscle_node_tree(mat)

def _build_muscle_node_tree(mat):
    """Build the muscle material node tree"""

    muscle = mat.node_tree
    #start with a clean node tree
    for node in muscle.nodes:
        muscle.nodes.remove(node)
    

    #muscle interface

    #initialize muscle nodes
    #node Principled BSDF
    principled_bsdf = muscle.nodes.new("ShaderNodeBsdfPrincipled")
    principled_bsdf.name = "Principled BSDF"
    principled_bsdf.distribution = 'MULTI_GGX'
    principled_bsdf.subsurface_method = 'RANDOM_WALK'
    
    # Use socket names instead of indices for better compatibility
    #Metallic
    principled_bsdf.inputs["Metallic"].default_value = 0.0
    #Roughness
    principled_bsdf.inputs["Roughness"].default_value = 0.5
    #IOR
    principled_bsdf.inputs["IOR"].default_value = 1.5
    #Alpha
    principled_bsdf.inputs["Alpha"].default_value = 1.0
    
    # Subsurface properties
    if "Subsurface Weight" in principled_bsdf.inputs:
        principled_bsdf.inputs["Subsurface Weight"].default_value = 0.3
    elif "Subsurface" in principled_bsdf.inputs:
        principled_bsdf.inputs["Subsurface"].default_value = 0.3
        
    if "Subsurface Radius" in principled_bsdf.inputs:
        principled_bsdf.inputs["Subsurface Radius"].default_value = (0.1, 0.1, 0.1)
    
    if "Subsurface Scale" in principled_bsdf.inputs:
        principled_bsdf.inputs["Subsurface Scale"].default_value = 0.05
    
    if "Subsurface Anisotropy" in principled_bsdf.inputs:
        principled_bsdf.inputs["Subsurface Anisotropy"].default_value = 0.0
        
    # Specular properties
    if "Specular IOR Level" in principled_bsdf.inputs:
        principled_bsdf.inputs["Specular IOR Level"].default_value = 0.5
    elif "Specular" in principled_bsdf.inputs:
        principled_bsdf.inputs["Specular"].default_value = 0.5
        
    if "Specular Tint" in principled_bsdf.inputs:
        principled_bsdf.inputs["Specular Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
        
    # Anisotropic properties
    if "Anisotropic" in principled_bsdf.inputs:
        principled_bsdf.inputs["Anisotropic"].default_value = 0.0
    if "Anisotropic Rotation" in principled_bsdf.inputs:
        principled_bsdf.inputs["Anisotropic Rotation"].default_value = 0.0
    # Tangent
    if "Tangent" in principled_bsdf.inputs:
        principled_bsdf.inputs["Tangent"].default_value = (0.0, 0.0, 0.0)
    
    # Transmission Weight
    if "Transmission Weight" in principled_bsdf.inputs:
        principled_bsdf.inputs["Transmission Weight"].default_value = 0.0
    elif "Transmission" in principled_bsdf.inputs:
        principled_bsdf.inputs["Transmission"].default_value = 0.0
    
    # Coat Weight
    if "Coat Weight" in principled_bsdf.inputs:
        principled_bsdf.inputs["Coat Weight"].default_value = 1.0
    elif "Clearcoat" in principled_bsdf.inputs:
        principled_bsdf.inputs["Clearcoat"].default_value = 1.0
    
    # Coat Roughness
    if "Coat Roughness" in principled_bsdf.inputs:
        principled_bsdf.inputs["Coat Roughness"].default_value = 0.20000000298023224
    elif "Clearcoat Roughness" in principled_bsdf.inputs:
        principled_bsdf.inputs["Clearcoat Roughness"].default_value = 0.20000000298023224
    
    # Coat IOR
    if "Coat IOR" in principled_bsdf.inputs:
        principled_bsdf.inputs["Coat IOR"].default_value = 1.4500000476837158
    elif "Clearcoat IOR" in principled_bsdf.inputs:
        principled_bsdf.inputs["Clearcoat IOR"].default_value = 1.4500000476837158
    
    # Coat Tint
    if "Coat Tint" in principled_bsdf.inputs:
        principled_bsdf.inputs["Coat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    elif "Clearcoat Tint" in principled_bsdf.inputs:
        principled_bsdf.inputs["Clearcoat Tint"].default_value = (1.0, 1.0, 1.0, 1.0)
    
    # Coat Normal
    if "Coat Normal" in principled_bsdf.inputs:
        principled_bsdf.inputs["Coat Normal"].default_value = (0.0, 0.0, 0.0)
    elif "Clearcoat Normal" in principled_bsdf.inputs:
        principled_bsdf.inputs["Clearcoat Normal"].default_value = (0.0, 0.0, 0.0)
    
    # Sheen Weight
    if "Sheen Weight" in principled_bsdf.inputs:
        principled_bsdf.inputs["Sheen Weight"].default_value = 0.0
    elif "Sheen" in principled_bsdf.inputs:
        principled_bsdf.inputs["Sheen"].default_value = 0.0
    
    # Sheen Roughness
    if "Sheen Roughness" in principled_bsdf.inputs:
        principled_bsdf.inputs["Sheen Roughness"].default_value = 0.5
    elif "Sheen Tint" in principled_bsdf.inputs:
        principled_bsdf.inputs["Sheen Tint"].default_value = 0.5
    
    # Emission Color
    if "Emission Color" in principled_bsdf.inputs:
        principled_bsdf.inputs["Emission Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    elif "Emission" in principled_bsdf.inputs:
        principled_bsdf.inputs["Emission"].default_value = (1.0, 1.0, 1.0, 1.0)
    
    # Emission Strength
    if "Emission Strength" in principled_bsdf.inputs:
        principled_bsdf.inputs["Emission Strength"].default_value = 0.0

    #node Material Output
    material_output = muscle.nodes.new("ShaderNodeOutputMaterial")
    material_output.name = "Material Output"
    material_output.is_active_output = True
    material_output.target = 'ALL'
    # Displacement
    if "Displacement" in material_output.inputs:
        material_output.inputs["Displacement"].default_value = (0.0, 0.0, 0.0)

    #node Bump
    bump = muscle.nodes.new("ShaderNodeBump")
    bump.name = "Bump"
    bump.invert = True
    # Strength
    if "Strength" in bump.inputs:
        bump.inputs["Strength"].default_value = 0.4333333373069763
    # Distance
    if "Distance" in bump.inputs:
        bump.inputs["Distance"].default_value = 4.0
    # Normal
    if "Normal" in bump.inputs:
        bump.inputs["Normal"].default_value = (0.0, 0.0, 0.0)

    #node Voronoi Texture
    voronoi_texture = muscle.nodes.new("ShaderNodeTexVoronoi")
    voronoi_texture.name = "Voronoi Texture"
    voronoi_texture.distance = 'EUCLIDEAN'
    voronoi_texture.feature = 'F1'
    voronoi_texture.normalize = True
    voronoi_texture.voronoi_dimensions = '3D'
    # Scale
    if "Scale" in voronoi_texture.inputs:
        voronoi_texture.inputs["Scale"].default_value = 12.0
    # Detail
    if "Detail" in voronoi_texture.inputs:
        voronoi_texture.inputs["Detail"].default_value = 0.7999999523162842
    # Roughness
    if "Roughness" in voronoi_texture.inputs:
        voronoi_texture.inputs["Roughness"].default_value = 0.5
    # Lacunarity
    if "Lacunarity" in voronoi_texture.inputs:
        voronoi_texture.inputs["Lacunarity"].default_value = 2.0
    # Randomness
    if "Randomness" in voronoi_texture.inputs:
        voronoi_texture.inputs["Randomness"].default_value = 1.0

    #node Mapping
    mapping = muscle.nodes.new("ShaderNodeMapping")
    mapping.name = "Mapping"
    mapping.vector_type = 'POINT'
    # Location
    if "Location" in mapping.inputs:
        mapping.inputs["Location"].default_value = (5.0, 0.0, 5.0)
    # Rotation
    if "Rotation" in mapping.inputs:
        mapping.inputs["Rotation"].default_value = (0.0, 0.0, 0.0)
    # Scale
    if "Scale" in mapping.inputs:
        mapping.inputs["Scale"].default_value = (2.0, 12.0, 2.0)

    #node Texture Coordinate
    texture_coordinate = muscle.nodes.new("ShaderNodeTexCoord")
    texture_coordinate.name = "Texture Coordinate"
    texture_coordinate.from_instancer = False

    #node Color Ramp
    color_ramp = muscle.nodes.new("ShaderNodeValToRGB")
    color_ramp.name = "Color Ramp"
    color_ramp.color_ramp.color_mode = 'RGB'
    color_ramp.color_ramp.hue_interpolation = 'NEAR'
    color_ramp.color_ramp.interpolation = 'LINEAR'

    #initialize color ramp elements
    color_ramp.color_ramp.elements.remove(color_ramp.color_ramp.elements[0])
    color_ramp_cre_0 = color_ramp.color_ramp.elements[0]
    color_ramp_cre_0.position = 0.0
    color_ramp_cre_0.alpha = 1.0
    color_ramp_cre_0.color = (0.0, 0.0, 0.0, 1.0)

    color_ramp_cre_1 = color_ramp.color_ramp.elements.new(0.7319999933242798)
    color_ramp_cre_1.alpha = 1.0
    color_ramp_cre_1.color = (1.0, 1.0, 1.0, 1.0)


    #node Mix
    mix = muscle.nodes.new("ShaderNodeMix")
    mix.name = "Mix"
    mix.blend_type = 'MIX'
    mix.clamp_factor = True
    mix.clamp_result = False
    mix.data_type = 'RGBA'
    mix.factor_mode = 'UNIFORM'
    # A Color
    if "A" in mix.inputs:
        mix.inputs["A"].default_value = (0.6038241982460022, 0.045186202973127365, 0.022173907607793808, 1.0)
    # B Color
    if "B" in mix.inputs:
        mix.inputs["B"].default_value = (0.11697008460760117, 0.004391433671116829, 0.0015176383312791586, 1.0)

    #node Noise Texture
    noise_texture = muscle.nodes.new("ShaderNodeTexNoise")
    noise_texture.name = "Noise Texture"
    noise_texture.noise_dimensions = '3D'
    noise_texture.noise_type = 'FBM'
    noise_texture.normalize = True
    # Scale
    if "Scale" in noise_texture.inputs:
        noise_texture.inputs["Scale"].default_value = 7.0
    # Detail
    if "Detail" in noise_texture.inputs:
        noise_texture.inputs["Detail"].default_value = 1.0
    # Roughness
    if "Roughness" in noise_texture.inputs:
        noise_texture.inputs["Roughness"].default_value = 0.5
    # Lacunarity
    if "Lacunarity" in noise_texture.inputs:
        noise_texture.inputs["Lacunarity"].default_value = 2.0
    # Distortion
    if "Distortion" in noise_texture.inputs:
        noise_texture.inputs["Distortion"].default_value = 0.0

    #node Mix.001
    mix_001 = muscle.nodes.new("ShaderNodeMix")
    mix_001.name = "Mix.001"
    mix_001.blend_type = 'SOFT_LIGHT'
    mix_001.clamp_factor = True
    mix_001.clamp_result = False
    mix_001.data_type = 'RGBA'
    mix_001.factor_mode = 'UNIFORM'
    # Factor
    if "Factor" in mix_001.inputs:
        mix_001.inputs["Factor"].default_value = 0.5

    #node Color Ramp.001
    color_ramp_001 = muscle.nodes.new("ShaderNodeValToRGB")
    color_ramp_001.name = "Color Ramp.001"
    color_ramp_001.color_ramp.color_mode = 'RGB'
    color_ramp_001.color_ramp.hue_interpolation = 'NEAR'
    color_ramp_001.color_ramp.interpolation = 'LINEAR'

    #initialize color ramp elements
    color_ramp_001.color_ramp.elements.remove(color_ramp_001.color_ramp.elements[0])
    color_ramp_001_cre_0 = color_ramp_001.color_ramp.elements[0]
    color_ramp_001_cre_0.position = 0.3957272469997406
    color_ramp_001_cre_0.alpha = 1.0
    color_ramp_001_cre_0.color = (0.0, 0.0, 0.0, 1.0)

    color_ramp_001_cre_1 = color_ramp_001.color_ramp.elements.new(1.0)
    color_ramp_001_cre_1.alpha = 1.0
    color_ramp_001_cre_1.color = (1.0, 1.0, 1.0, 1.0)


    #node Mapping.001
    mapping_001 = muscle.nodes.new("ShaderNodeMapping")
    mapping_001.name = "Mapping.001"
    mapping_001.vector_type = 'POINT'
    # Location
    if "Location" in mapping_001.inputs:
        mapping_001.inputs["Location"].default_value = (0.0, 0.0, 0.0)
    # Rotation
    if "Rotation" in mapping_001.inputs:
        mapping_001.inputs["Rotation"].default_value = (0.0, 0.0, 0.0)
    # Scale
    if "Scale" in mapping_001.inputs:
        mapping_001.inputs["Scale"].default_value = (1.0, 1.0, 1.0)

    #node Gradient Texture
    gradient_texture = muscle.nodes.new("ShaderNodeTexGradient")
    gradient_texture.name = "Gradient Texture"
    gradient_texture.gradient_type = 'LINEAR'

    #node Color Ramp.002
    color_ramp_002 = muscle.nodes.new("ShaderNodeValToRGB")
    color_ramp_002.name = "Color Ramp.002"
    color_ramp_002.color_ramp.color_mode = 'RGB'
    color_ramp_002.color_ramp.hue_interpolation = 'NEAR'
    color_ramp_002.color_ramp.interpolation = 'EASE'

    #initialize color ramp elements
    color_ramp_002.color_ramp.elements.remove(color_ramp_002.color_ramp.elements[0])
    color_ramp_002_cre_0 = color_ramp_002.color_ramp.elements[0]
    color_ramp_002_cre_0.position = 0.0
    color_ramp_002_cre_0.alpha = 1.0
    color_ramp_002_cre_0.color = (0.5, 0.5, 0.5, 1.0)

    color_ramp_002_cre_1 = color_ramp_002.color_ramp.elements.new(0.0818181037902832)
    color_ramp_002_cre_1.alpha = 1.0
    color_ramp_002_cre_1.color = (0.0, 0.0, 0.0, 1.0)

    color_ramp_002_cre_2 = color_ramp_002.color_ramp.elements.new(0.922727108001709)
    color_ramp_002_cre_2.alpha = 1.0
    color_ramp_002_cre_2.color = (0.0, 0.0, 0.0, 1.0)

    color_ramp_002_cre_3 = color_ramp_002.color_ramp.elements.new(1.0)
    color_ramp_002_cre_3.alpha = 1.0
    color_ramp_002_cre_3.color = (1.0, 1.0, 1.0, 1.0)


    #node Mix.002
    mix_002 = muscle.nodes.new("ShaderNodeMix")
    mix_002.name = "Mix.002"
    mix_002.blend_type = 'MIX'
    mix_002.clamp_factor = True
    mix_002.clamp_result = False
    mix_002.data_type = 'RGBA'
    mix_002.factor_mode = 'UNIFORM'
    # B Color
    if "B" in mix_002.inputs:
        mix_002.inputs["B"].default_value = (0.5, 0.5, 0.5, 1.0)

    #node Mix.003
    mix_003 = muscle.nodes.new("ShaderNodeMix")
    mix_003.name = "Mix.003"
    mix_003.blend_type = 'ADD'
    mix_003.clamp_factor = True
    mix_003.clamp_result = False
    mix_003.data_type = 'RGBA'
    mix_003.factor_mode = 'UNIFORM'
    # Factor
    if "Factor" in mix_003.inputs:
        mix_003.inputs["Factor"].default_value = 0.5
    # B Color
    if "B" in mix_003.inputs:
        mix_003.inputs["B"].default_value = (0.5, 0.5, 0.5, 1.0)


    #Set locations
    principled_bsdf.location = (180.08399963378906, 296.2430725097656)
    material_output.location = (468.8333740234375, 287.4768981933594)
    bump.location = (-0.1737518310546875, 156.9415740966797)
    voronoi_texture.location = (-855.2374267578125, 85.02146911621094)
    mapping.location = (-1101.263427734375, 88.7633285522461)
    texture_coordinate.location = (-1314.74560546875, 70.61038208007812)
    color_ramp.location = (-421.1051330566406, 44.06411361694336)
    mix.location = (-226.4066162109375, 420.8203125)
    noise_texture.location = (-852.3905029296875, -268.9551696777344)
    mix_001.location = (-589.5138549804688, 66.40495300292969)
    color_ramp_001.location = (-675.242919921875, -278.13525390625)
    mapping_001.location = (-1105.9901123046875, 514.7693481445312)
    gradient_texture.location = (-853.4522705078125, 451.54949951171875)
    color_ramp_002.location = (-635.2454833984375, 449.2889709472656)
    mix_002.location = (-41.19255065917969, 426.6008605957031)
    mix_003.location = (-136.00042724609375, -52.22281265258789)

    #Set dimensions
    principled_bsdf.width, principled_bsdf.height = 240.0, 100.0
    material_output.width, material_output.height = 140.0, 100.0
    bump.width, bump.height = 140.0, 100.0
    voronoi_texture.width, voronoi_texture.height = 140.0, 100.0
    mapping.width, mapping.height = 140.0, 100.0
    texture_coordinate.width, texture_coordinate.height = 140.0, 100.0
    color_ramp.width, color_ramp.height = 240.0, 100.0
    mix.width, mix.height = 140.0, 100.0
    noise_texture.width, noise_texture.height = 140.0, 100.0
    mix_001.width, mix_001.height = 140.0, 100.0
    color_ramp_001.width, color_ramp_001.height = 240.0, 100.0
    mapping_001.width, mapping_001.height = 140.0, 100.0
    gradient_texture.width, gradient_texture.height = 140.0, 100.0
    color_ramp_002.width, color_ramp_002.height = 240.0, 100.0
    mix_002.width, mix_002.height = 140.0, 100.0
    mix_003.width, mix_003.height = 140.0, 100.0

    #initialize muscle links
    #principled_bsdf.BSDF -> material_output.Surface
    muscle.links.new(principled_bsdf.outputs["BSDF"], material_output.inputs["Surface"])
    #bump.Normal -> principled_bsdf.Normal
    muscle.links.new(bump.outputs["Normal"], principled_bsdf.inputs["Normal"])
    #texture_coordinate.Generated -> mapping.Vector
    muscle.links.new(texture_coordinate.outputs["Generated"], mapping.inputs["Vector"])
    #mapping.Vector -> voronoi_texture.Vector
    muscle.links.new(mapping.outputs["Vector"], voronoi_texture.inputs["Vector"])
    #mix_001.Result -> color_ramp.Fac
    muscle.links.new(mix_001.outputs["Result"], color_ramp.inputs["Fac"])
    #color_ramp.Color -> mix.Factor
    muscle.links.new(color_ramp.outputs["Color"], mix.inputs["Factor"])
    #voronoi_texture.Distance -> mix_001.A
    muscle.links.new(voronoi_texture.outputs["Distance"], mix_001.inputs["A"])
    #mapping.Vector -> noise_texture.Vector
    muscle.links.new(mapping.outputs["Vector"], noise_texture.inputs["Vector"])
    #noise_texture.Fac -> color_ramp_001.Fac
    muscle.links.new(noise_texture.outputs["Fac"], color_ramp_001.inputs["Fac"])
    #color_ramp_001.Color -> mix_001.B
    muscle.links.new(color_ramp_001.outputs["Color"], mix_001.inputs["B"])
    #texture_coordinate.Generated -> mapping_001.Vector
    muscle.links.new(texture_coordinate.outputs["Generated"], mapping_001.inputs["Vector"])
    #mapping_001.Vector -> gradient_texture.Vector
    muscle.links.new(mapping_001.outputs["Vector"], gradient_texture.inputs["Vector"])
    #gradient_texture.Color -> color_ramp_002.Fac
    muscle.links.new(gradient_texture.outputs["Fac"], color_ramp_002.inputs["Fac"])
    #color_ramp_002.Color -> mix_002.Factor
    muscle.links.new(color_ramp_002.outputs["Color"], mix_002.inputs["Factor"])
    #mix.Result -> mix_002.A
    muscle.links.new(mix.outputs["Result"], mix_002.inputs["A"])
    #mix_002.Result -> principled_bsdf.Base Color
    muscle.links.new(mix_002.outputs["Result"], principled_bsdf.inputs["Base Color"])
    #color_ramp.Color -> mix_003.A
    muscle.links.new(color_ramp.outputs["Color"], mix_003.inputs["A"])
    #mix_003.Result -> bump.Height
    muscle.links.new(mix_003.outputs["Result"], bump.inputs["Height"])
    
    return mat

def apply_muscle_material(mesh_obj):
    """
    Apply the muscle material to a mesh object.
    Creates the material if it doesn't exist.
    """
    if not mesh_obj or mesh_obj.type != 'MESH':
        return False
    
    # Get or create the muscle material
    muscle_material = create_muscle_material()
    
    # Clear existing materials and apply the muscle material
    mesh_obj.data.materials.clear()
    mesh_obj.data.materials.append(muscle_material)
    
    return True

