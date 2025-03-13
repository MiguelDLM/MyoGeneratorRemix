import bpy, mathutils

#initialize loft_splines node group
def loft_splines_node_group():
    loft_splines = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "Loft-splines")

    loft_splines.color_tag = 'NONE'
    loft_splines.description = ""
    loft_splines.default_group_node_width = 140

    #loft_splines interface
    #Socket Geometry
    geometry_socket = loft_splines.interface.new_socket(name = "Geometry", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    #Socket Switch
    switch_socket = loft_splines.interface.new_socket(name = "Switch", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_socket.default_value = False
    switch_socket.attribute_domain = 'POINT'

    #Socket Value
    value_socket = loft_splines.interface.new_socket(name = "Value", in_out='INPUT', socket_type = 'NodeSocketFloat')
    value_socket.default_value = 0.5
    value_socket.min_value = -10000.0
    value_socket.max_value = 10000.0
    value_socket.subtype = 'NONE'
    value_socket.attribute_domain = 'POINT'

    #Socket Switch
    switch_socket_1 = loft_splines.interface.new_socket(name = "Switch", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_socket_1.default_value = False
    switch_socket_1.attribute_domain = 'POINT'

    #Socket Switch
    switch_socket_2 = loft_splines.interface.new_socket(name = "Switch", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_socket_2.default_value = False
    switch_socket_2.attribute_domain = 'POINT'

    #Socket Switch
    switch_socket_3 = loft_splines.interface.new_socket(name = "Switch", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_socket_3.default_value = False
    switch_socket_3.attribute_domain = 'POINT'

    #Socket True
    true_socket = loft_splines.interface.new_socket(name = "True", in_out='INPUT', socket_type = 'NodeSocketInt')
    true_socket.default_value = 0
    true_socket.min_value = -2147483648
    true_socket.max_value = 2147483647
    true_socket.subtype = 'NONE'
    true_socket.attribute_domain = 'POINT'

    #Socket False
    false_socket = loft_splines.interface.new_socket(name = "False", in_out='INPUT', socket_type = 'NodeSocketGeometry')
    false_socket.attribute_domain = 'POINT'


    #initialize loft_splines nodes
    #node Group Output
    group_output = loft_splines.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    #node Group Input
    group_input = loft_splines.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    #node Store Named Attribute
    store_named_attribute = loft_splines.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute.name = "Store Named Attribute"
    store_named_attribute.data_type = 'FLOAT_VECTOR'
    store_named_attribute.domain = 'CORNER'
    #Selection
    store_named_attribute.inputs[1].default_value = True
    #Name
    store_named_attribute.inputs[2].default_value = "uv_map"

    #node Math.024
    math_024 = loft_splines.nodes.new("ShaderNodeMath")
    math_024.name = "Math.024"
    math_024.operation = 'MULTIPLY'
    math_024.use_clamp = False

    #node Math.026
    math_026 = loft_splines.nodes.new("ShaderNodeMath")
    math_026.name = "Math.026"
    math_026.operation = 'MODULO'
    math_026.use_clamp = False

    #node Duplicate Elements.001
    duplicate_elements_001 = loft_splines.nodes.new("GeometryNodeDuplicateElements")
    duplicate_elements_001.name = "Duplicate Elements.001"
    duplicate_elements_001.domain = 'SPLINE'
    #Selection
    duplicate_elements_001.inputs[1].default_value = True

    #node Resample Curve.003
    resample_curve_003 = loft_splines.nodes.new("GeometryNodeResampleCurve")
    resample_curve_003.name = "Resample Curve.003"
    resample_curve_003.mode = 'COUNT'
    #Selection
    resample_curve_003.inputs[1].default_value = True

    #node Math.025
    math_025 = loft_splines.nodes.new("ShaderNodeMath")
    math_025.name = "Math.025"
    math_025.operation = 'ADD'
    math_025.use_clamp = False

    #node Set Position.003
    set_position_003 = loft_splines.nodes.new("GeometryNodeSetPosition")
    set_position_003.name = "Set Position.003"
    #Selection
    set_position_003.inputs[1].default_value = True
    #Offset
    set_position_003.inputs[3].default_value = (0.0, 0.0, 0.0)

    #node Switch.011
    switch_011 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_011.name = "Switch.011"
    switch_011.input_type = 'INT'

    #node Math.027
    math_027 = loft_splines.nodes.new("ShaderNodeMath")
    math_027.name = "Math.027"
    math_027.operation = 'ADD'
    math_027.use_clamp = False
    #Value_001
    math_027.inputs[1].default_value = 1.0

    #node Math.020
    math_020 = loft_splines.nodes.new("ShaderNodeMath")
    math_020.name = "Math.020"
    math_020.operation = 'SUBTRACT'
    math_020.use_clamp = False

    #node Math.021
    math_021 = loft_splines.nodes.new("ShaderNodeMath")
    math_021.name = "Math.021"
    math_021.operation = 'ADD'
    math_021.use_clamp = False
    #Value_001
    math_021.inputs[1].default_value = 1.0

    #node Math.022
    math_022 = loft_splines.nodes.new("ShaderNodeMath")
    math_022.name = "Math.022"
    math_022.operation = 'MULTIPLY'
    math_022.use_clamp = False

    #node Math.023
    math_023 = loft_splines.nodes.new("ShaderNodeMath")
    math_023.name = "Math.023"
    math_023.operation = 'ADD'
    math_023.use_clamp = False
    #Value_001
    math_023.inputs[1].default_value = 1.0

    #node Switch.003
    switch_003 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_003.name = "Switch.003"
    switch_003.input_type = 'FLOAT'
    #False
    switch_003.inputs[1].default_value = 1.0
    #True
    switch_003.inputs[2].default_value = 0.0

    #node Grid.001
    grid_001 = loft_splines.nodes.new("GeometryNodeMeshGrid")
    grid_001.name = "Grid.001"
    #Size X
    grid_001.inputs[0].default_value = 1.0
    #Size Y
    grid_001.inputs[1].default_value = 1.0

    #node Math.028
    math_028 = loft_splines.nodes.new("ShaderNodeMath")
    math_028.name = "Math.028"
    math_028.operation = 'DIVIDE'
    math_028.use_clamp = False

    #node Math.029
    math_029 = loft_splines.nodes.new("ShaderNodeMath")
    math_029.name = "Math.029"
    math_029.operation = 'MODULO'
    math_029.use_clamp = False

    #node Math.031
    math_031 = loft_splines.nodes.new("ShaderNodeMath")
    math_031.name = "Math.031"
    math_031.operation = 'FLOOR'
    math_031.use_clamp = False

    #node Math.032
    math_032 = loft_splines.nodes.new("ShaderNodeMath")
    math_032.name = "Math.032"
    math_032.operation = 'SUBTRACT'
    math_032.use_clamp = False

    #node Compare.003
    compare_003 = loft_splines.nodes.new("FunctionNodeCompare")
    compare_003.name = "Compare.003"
    compare_003.data_type = 'INT'
    compare_003.mode = 'ELEMENT'
    compare_003.operation = 'EQUAL'

    #node Math.033
    math_033 = loft_splines.nodes.new("ShaderNodeMath")
    math_033.name = "Math.033"
    math_033.operation = 'MULTIPLY'
    math_033.use_clamp = False

    #node Switch.012
    switch_012 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_012.name = "Switch.012"
    switch_012.input_type = 'FLOAT'

    #node Position.002
    position_002 = loft_splines.nodes.new("GeometryNodeInputPosition")
    position_002.name = "Position.002"

    #node Math.030
    math_030 = loft_splines.nodes.new("ShaderNodeMath")
    math_030.name = "Math.030"
    math_030.operation = 'SUBTRACT'
    math_030.use_clamp = False
    #Value_001
    math_030.inputs[1].default_value = 1.0

    #node Math.034
    math_034 = loft_splines.nodes.new("ShaderNodeMath")
    math_034.name = "Math.034"
    math_034.operation = 'MULTIPLY'
    math_034.use_clamp = False

    #node Compare.004
    compare_004 = loft_splines.nodes.new("FunctionNodeCompare")
    compare_004.name = "Compare.004"
    compare_004.data_type = 'INT'
    compare_004.mode = 'ELEMENT'
    compare_004.operation = 'GREATER_EQUAL'

    #node Math.035
    math_035 = loft_splines.nodes.new("ShaderNodeMath")
    math_035.name = "Math.035"
    math_035.operation = 'MODULO'
    math_035.use_clamp = False

    #node Boolean Math.001
    boolean_math_001 = loft_splines.nodes.new("FunctionNodeBooleanMath")
    boolean_math_001.name = "Boolean Math.001"
    boolean_math_001.operation = 'AND'

    #node Switch.017
    switch_017 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_017.name = "Switch.017"
    switch_017.input_type = 'INT'

    #node Switch.014
    switch_014 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_014.name = "Switch.014"
    switch_014.input_type = 'INT'

    #node Compare.005
    compare_005 = loft_splines.nodes.new("FunctionNodeCompare")
    compare_005.name = "Compare.005"
    compare_005.data_type = 'INT'
    compare_005.mode = 'ELEMENT'
    compare_005.operation = 'EQUAL'

    #node Switch.015
    switch_015 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_015.name = "Switch.015"
    switch_015.input_type = 'INT'
    #True
    switch_015.inputs[2].default_value = 0

    #node Math.036
    math_036 = loft_splines.nodes.new("ShaderNodeMath")
    math_036.name = "Math.036"
    math_036.operation = 'SUBTRACT'
    math_036.use_clamp = False
    #Value_001
    math_036.inputs[1].default_value = 1.0

    #node Math.037
    math_037 = loft_splines.nodes.new("ShaderNodeMath")
    math_037.name = "Math.037"
    math_037.operation = 'MULTIPLY'
    math_037.use_clamp = False

    #node Switch.016
    switch_016 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_016.name = "Switch.016"
    switch_016.input_type = 'INT'

    #node Switch.013
    switch_013 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_013.name = "Switch.013"
    switch_013.input_type = 'INT'

    #node Set Spline Cyclic.002
    set_spline_cyclic_002 = loft_splines.nodes.new("GeometryNodeSetSplineCyclic")
    set_spline_cyclic_002.name = "Set Spline Cyclic.002"
    #Selection
    set_spline_cyclic_002.inputs[1].default_value = True

    #node Math.019
    math_019 = loft_splines.nodes.new("ShaderNodeMath")
    math_019.name = "Math.019"
    math_019.operation = 'ADD'
    math_019.use_clamp = False
    #Value_001
    math_019.inputs[1].default_value = 1.0

    #node Compare
    compare = loft_splines.nodes.new("FunctionNodeCompare")
    compare.name = "Compare"
    compare.data_type = 'INT'
    compare.mode = 'ELEMENT'
    compare.operation = 'EQUAL'
    #B_INT
    compare.inputs[3].default_value = 1

    #node Edge Neighbors
    edge_neighbors = loft_splines.nodes.new("GeometryNodeInputMeshEdgeNeighbors")
    edge_neighbors.name = "Edge Neighbors"

    #node Set Position.002
    set_position_002 = loft_splines.nodes.new("GeometryNodeSetPosition")
    set_position_002.name = "Set Position.002"
    #Selection
    set_position_002.inputs[1].default_value = True
    #Offset
    set_position_002.inputs[3].default_value = (0.0, 0.0, 0.0)

    #node Merge by Distance
    merge_by_distance = loft_splines.nodes.new("GeometryNodeMergeByDistance")
    merge_by_distance.name = "Merge by Distance"
    merge_by_distance.mode = 'ALL'
    #Distance
    merge_by_distance.inputs[2].default_value = 9.999999747378752e-06

    #node Curve to Mesh
    curve_to_mesh = loft_splines.nodes.new("GeometryNodeCurveToMesh")
    curve_to_mesh.name = "Curve to Mesh"
    #Fill Caps
    curve_to_mesh.inputs[2].default_value = False

    #node Boolean Math
    boolean_math = loft_splines.nodes.new("FunctionNodeBooleanMath")
    boolean_math.name = "Boolean Math"
    boolean_math.operation = 'OR'

    #node Switch
    switch = loft_splines.nodes.new("GeometryNodeSwitch")
    switch.name = "Switch"
    switch.input_type = 'GEOMETRY'

    #node Switch.010
    switch_010 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_010.name = "Switch.010"
    switch_010.input_type = 'GEOMETRY'

    #node Resample Curve.006
    resample_curve_006 = loft_splines.nodes.new("GeometryNodeResampleCurve")
    resample_curve_006.name = "Resample Curve.006"
    resample_curve_006.mode = 'EVALUATED'
    #Selection
    resample_curve_006.inputs[1].default_value = True

    #node Set Spline Type.002
    set_spline_type_002 = loft_splines.nodes.new("GeometryNodeCurveSplineType")
    set_spline_type_002.name = "Set Spline Type.002"
    set_spline_type_002.spline_type = 'CATMULL_ROM'
    #Selection
    set_spline_type_002.inputs[1].default_value = True

    #node Set Spline Type.001
    set_spline_type_001 = loft_splines.nodes.new("GeometryNodeCurveSplineType")
    set_spline_type_001.name = "Set Spline Type.001"
    set_spline_type_001.spline_type = 'BEZIER'
    #Selection
    set_spline_type_001.inputs[1].default_value = True

    #node Set Handle Type.001
    set_handle_type_001 = loft_splines.nodes.new("GeometryNodeCurveSetHandles")
    set_handle_type_001.name = "Set Handle Type.001"
    set_handle_type_001.handle_type = 'AUTO'
    set_handle_type_001.mode = {'LEFT', 'RIGHT'}
    #Selection
    set_handle_type_001.inputs[1].default_value = True

    #node Resample Curve.005
    resample_curve_005 = loft_splines.nodes.new("GeometryNodeResampleCurve")
    resample_curve_005.name = "Resample Curve.005"
    resample_curve_005.mode = 'EVALUATED'
    #Selection
    resample_curve_005.inputs[1].default_value = True

    #node Set Spline Resolution.001
    set_spline_resolution_001 = loft_splines.nodes.new("GeometryNodeSetSplineResolution")
    set_spline_resolution_001.name = "Set Spline Resolution.001"
    #Selection
    set_spline_resolution_001.inputs[1].default_value = True

    #node Subdivide Curve.001
    subdivide_curve_001 = loft_splines.nodes.new("GeometryNodeSubdivideCurve")
    subdivide_curve_001.name = "Subdivide Curve.001"

    #node Math
    math = loft_splines.nodes.new("ShaderNodeMath")
    math.name = "Math"
    math.operation = 'SUBTRACT'
    math.use_clamp = False
    #Value_001
    math.inputs[1].default_value = 1.0

    #node Switch.018
    switch_018 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_018.name = "Switch.018"
    switch_018.input_type = 'GEOMETRY'

    #node Index.006
    index_006 = loft_splines.nodes.new("GeometryNodeInputIndex")
    index_006.name = "Index.006"

    #node Switch.002
    switch_002 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_002.name = "Switch.002"
    switch_002.input_type = 'INT'

    #node Math.001
    math_001 = loft_splines.nodes.new("ShaderNodeMath")
    math_001.name = "Math.001"
    math_001.operation = 'DIVIDE'
    math_001.use_clamp = False

    #node Domain Size.001
    domain_size_001 = loft_splines.nodes.new("GeometryNodeAttributeDomainSize")
    domain_size_001.name = "Domain Size.001"
    domain_size_001.component = 'CURVE'

    #node Switch.001
    switch_001 = loft_splines.nodes.new("GeometryNodeSwitch")
    switch_001.name = "Switch.001"
    switch_001.input_type = 'GEOMETRY'

    #node Resample Curve.004
    resample_curve_004 = loft_splines.nodes.new("GeometryNodeResampleCurve")
    resample_curve_004.name = "Resample Curve.004"
    resample_curve_004.mode = 'COUNT'
    #Selection
    resample_curve_004.inputs[1].default_value = True

    #node Curve Line.001
    curve_line_001 = loft_splines.nodes.new("GeometryNodeCurvePrimitiveLine")
    curve_line_001.name = "Curve Line.001"
    curve_line_001.mode = 'POINTS'
    #Start
    curve_line_001.inputs[0].default_value = (0.0, 0.0, 0.0)
    #End
    curve_line_001.inputs[1].default_value = (0.0, 0.0, 1.0)

    #node Geometry Proximity
    geometry_proximity = loft_splines.nodes.new("GeometryNodeProximity")
    geometry_proximity.name = "Geometry Proximity"
    geometry_proximity.target_element = 'EDGES'
    #Group ID
    geometry_proximity.inputs[1].default_value = 0
    #Source Position
    geometry_proximity.inputs[2].default_value = (0.0, 0.0, 0.0)
    #Sample Group ID
    geometry_proximity.inputs[3].default_value = 0

    #node Sample Index
    sample_index = loft_splines.nodes.new("GeometryNodeSampleIndex")
    sample_index.name = "Sample Index"
    sample_index.clamp = True
    sample_index.data_type = 'FLOAT_VECTOR'
    sample_index.domain = 'POINT'

    #node Sample Index.001
    sample_index_001 = loft_splines.nodes.new("GeometryNodeSampleIndex")
    sample_index_001.name = "Sample Index.001"
    sample_index_001.clamp = True
    sample_index_001.data_type = 'FLOAT_VECTOR'
    sample_index_001.domain = 'POINT'

    #node Viewer
    viewer = loft_splines.nodes.new("GeometryNodeViewer")
    viewer.name = "Viewer"
    viewer.data_type = 'FLOAT'
    viewer.domain = 'AUTO'
    #Value
    viewer.inputs[1].default_value = 0.0

    #node Delete Geometry
    delete_geometry = loft_splines.nodes.new("GeometryNodeDeleteGeometry")
    delete_geometry.name = "Delete Geometry"
    delete_geometry.domain = 'EDGE'
    delete_geometry.mode = 'ALL'

    #node Math.002
    math_002 = loft_splines.nodes.new("ShaderNodeMath")
    math_002.name = "Math.002"
    math_002.operation = 'LESS_THAN'
    math_002.use_clamp = False
    #Value_001
    math_002.inputs[1].default_value = 0.0010000000474974513





    #Set locations
    group_output.location = (2253.976806640625, 103.1391372680664)
    group_input.location = (-3134.2138671875, 184.89576721191406)
    store_named_attribute.location = (-178.12777709960938, 174.09860229492188)
    math_024.location = (-1380.0030517578125, 207.15460205078125)
    math_026.location = (-1560.0030517578125, 207.15460205078125)
    duplicate_elements_001.location = (-1380.0030517578125, 407.15460205078125)
    resample_curve_003.location = (-1560.0030517578125, 407.15460205078125)
    math_025.location = (-1200.0030517578125, 207.15460205078125)
    set_position_003.location = (-820.0030517578125, 427.15460205078125)
    switch_011.location = (-780.0030517578125, 127.15460968017578)
    math_027.location = (-960.0030517578125, 7.154609680175781)
    math_020.location = (-1140.0030517578125, -292.84539794921875)
    math_021.location = (-1140.0030517578125, -132.84539794921875)
    math_022.location = (-960.0030517578125, -192.84539794921875)
    math_023.location = (-780.0030517578125, -192.84539794921875)
    switch_003.location = (-1320.0030517578125, -292.84539794921875)
    grid_001.location = (-460.8050231933594, 140.216552734375)
    math_028.location = (-440.0030212402344, -112.84539031982422)
    math_029.location = (-440.0030212402344, -272.84539794921875)
    math_031.location = (-260.0030212402344, -112.84539031982422)
    math_032.location = (-80.00302124023438, -112.84539031982422)
    compare_003.location = (-260.0030212402344, -272.84539794921875)
    math_033.location = (-80.00302124023438, -272.84539794921875)
    switch_012.location = (99.99697875976562, -112.84539031982422)
    position_002.location = (-1200.0030517578125, 307.15460205078125)
    math_030.location = (-440.0030212402344, -432.8453674316406)
    math_034.location = (-260.0030212402344, -452.8453674316406)
    compare_004.location = (-80.00302124023438, -452.8453674316406)
    math_035.location = (-80.00302124023438, -632.8453369140625)
    boolean_math_001.location = (879.9969482421875, 167.15460205078125)
    switch_017.location = (1059.9969482421875, 167.15460205078125)
    switch_014.location = (699.9969482421875, 167.15460205078125)
    compare_005.location = (699.9969482421875, -12.845390319824219)
    switch_015.location = (879.9969482421875, 7.154609680175781)
    math_036.location = (519.9969482421875, -172.84539794921875)
    math_037.location = (339.9969787597656, -172.84539794921875)
    switch_016.location = (339.9969787597656, 87.15460968017578)
    switch_013.location = (519.9969482421875, 87.15460968017578)
    set_spline_cyclic_002.location = (-580.0030517578125, 427.15460205078125)
    math_019.location = (-580.0030517578125, 607.1546020507812)
    compare.location = (1439.9969482421875, 147.15460205078125)
    edge_neighbors.location = (1259.9969482421875, 67.15460968017578)
    set_position_002.location = (1439.9969482421875, 387.15460205078125)
    merge_by_distance.location = (1639.9969482421875, 227.15460205078125)
    curve_to_mesh.location = (973.3402099609375, 677.6331787109375)
    boolean_math.location = (1439.9969482421875, -32.84539031982422)
    switch.location = (1800.3353271484375, 375.0978088378906)
    switch_010.location = (379.9969787597656, 707.1546630859375)
    resample_curve_006.location = (-0.003021240234375, 527.1546020507812)
    set_spline_type_002.location = (-180.00302124023438, 527.1546020507812)
    set_spline_type_001.location = (-180.00302124023438, 707.1546630859375)
    set_handle_type_001.location = (-0.003021240234375, 707.1546630859375)
    resample_curve_005.location = (179.99697875976562, 707.1546630859375)
    set_spline_resolution_001.location = (-360.0030212402344, 547.1546020507812)
    subdivide_curve_001.location = (-360.0030212402344, 387.15460205078125)
    math.location = (379.9969787597656, 527.1546020507812)
    switch_018.location = (619.9969482421875, 567.1546020507812)
    index_006.location = (-1780.0030517578125, 87.15460968017578)
    switch_002.location = (-1547.8126220703125, 591.4889526367188)
    math_001.location = (-1737.7681884765625, 710.90771484375)
    domain_size_001.location = (-1923.8677978515625, 699.01318359375)
    switch_001.location = (-2135.257080078125, 686.4427490234375)
    resample_curve_004.location = (-2558.747314453125, 707.3619384765625)
    curve_line_001.location = (-2583.858642578125, 143.85205078125)
    geometry_proximity.location = (1154.328369140625, 802.4251708984375)
    sample_index.location = (-1000.0030517578125, 427.15460205078125)
    sample_index_001.location = (1180.67431640625, 403.0409240722656)
    viewer.location = (983.8426513671875, 839.1236572265625)
    delete_geometry.location = (2063.976806640625, 635.10302734375)
    math_002.location = (1343.26220703125, 652.775390625)

    #Set dimensions
    group_output.width, group_output.height = 140.0, 100.0
    group_input.width, group_input.height = 140.0, 100.0
    store_named_attribute.width, store_named_attribute.height = 140.0, 100.0
    math_024.width, math_024.height = 140.0, 100.0
    math_026.width, math_026.height = 140.0, 100.0
    duplicate_elements_001.width, duplicate_elements_001.height = 140.0, 100.0
    resample_curve_003.width, resample_curve_003.height = 140.0, 100.0
    math_025.width, math_025.height = 140.0, 100.0
    set_position_003.width, set_position_003.height = 140.0, 100.0
    switch_011.width, switch_011.height = 140.0, 100.0
    math_027.width, math_027.height = 140.0, 100.0
    math_020.width, math_020.height = 140.0, 100.0
    math_021.width, math_021.height = 140.0, 100.0
    math_022.width, math_022.height = 140.0, 100.0
    math_023.width, math_023.height = 140.0, 100.0
    switch_003.width, switch_003.height = 140.0, 100.0
    grid_001.width, grid_001.height = 140.0, 100.0
    math_028.width, math_028.height = 140.0, 100.0
    math_029.width, math_029.height = 140.0, 100.0
    math_031.width, math_031.height = 140.0, 100.0
    math_032.width, math_032.height = 140.0, 100.0
    compare_003.width, compare_003.height = 140.0, 100.0
    math_033.width, math_033.height = 140.0, 100.0
    switch_012.width, switch_012.height = 140.0, 100.0
    position_002.width, position_002.height = 140.0, 100.0
    math_030.width, math_030.height = 140.0, 100.0
    math_034.width, math_034.height = 140.0, 100.0
    compare_004.width, compare_004.height = 140.0, 100.0
    math_035.width, math_035.height = 140.0, 100.0
    boolean_math_001.width, boolean_math_001.height = 140.0, 100.0
    switch_017.width, switch_017.height = 140.0, 100.0
    switch_014.width, switch_014.height = 140.0, 100.0
    compare_005.width, compare_005.height = 140.0, 100.0
    switch_015.width, switch_015.height = 140.0, 100.0
    math_036.width, math_036.height = 140.0, 100.0
    math_037.width, math_037.height = 140.0, 100.0
    switch_016.width, switch_016.height = 140.0, 100.0
    switch_013.width, switch_013.height = 140.0, 100.0
    set_spline_cyclic_002.width, set_spline_cyclic_002.height = 140.0, 100.0
    math_019.width, math_019.height = 140.0, 100.0
    compare.width, compare.height = 140.0, 100.0
    edge_neighbors.width, edge_neighbors.height = 140.0, 100.0
    set_position_002.width, set_position_002.height = 140.0, 100.0
    merge_by_distance.width, merge_by_distance.height = 140.0, 100.0
    curve_to_mesh.width, curve_to_mesh.height = 140.0, 100.0
    boolean_math.width, boolean_math.height = 140.0, 100.0
    switch.width, switch.height = 140.0, 100.0
    switch_010.width, switch_010.height = 140.0, 100.0
    resample_curve_006.width, resample_curve_006.height = 140.0, 100.0
    set_spline_type_002.width, set_spline_type_002.height = 140.0, 100.0
    set_spline_type_001.width, set_spline_type_001.height = 140.0, 100.0
    set_handle_type_001.width, set_handle_type_001.height = 140.0, 100.0
    resample_curve_005.width, resample_curve_005.height = 140.0, 100.0
    set_spline_resolution_001.width, set_spline_resolution_001.height = 140.0, 100.0
    subdivide_curve_001.width, subdivide_curve_001.height = 140.0, 100.0
    math.width, math.height = 140.0, 100.0
    switch_018.width, switch_018.height = 140.0, 100.0
    index_006.width, index_006.height = 140.0, 100.0
    switch_002.width, switch_002.height = 140.0, 100.0
    math_001.width, math_001.height = 140.0, 100.0
    domain_size_001.width, domain_size_001.height = 140.0, 100.0
    switch_001.width, switch_001.height = 140.0, 100.0
    resample_curve_004.width, resample_curve_004.height = 140.0, 100.0
    curve_line_001.width, curve_line_001.height = 140.0, 100.0
    geometry_proximity.width, geometry_proximity.height = 140.0, 100.0
    sample_index.width, sample_index.height = 140.0, 100.0
    sample_index_001.width, sample_index_001.height = 140.0, 100.0
    viewer.width, viewer.height = 140.0, 100.0
    delete_geometry.width, delete_geometry.height = 140.0, 100.0
    math_002.width, math_002.height = 269.2425842285156, 100.0

    #initialize loft_splines links
    #math_029.Value -> compare_003.A
    loft_splines.links.new(math_029.outputs[0], compare_003.inputs[2])
    #boolean_math_001.Boolean -> switch_017.Switch
    loft_splines.links.new(boolean_math_001.outputs[0], switch_017.inputs[0])
    #resample_curve_003.Curve -> duplicate_elements_001.Geometry
    loft_splines.links.new(resample_curve_003.outputs[0], duplicate_elements_001.inputs[0])
    #math_023.Value -> math_030.Value
    loft_splines.links.new(math_023.outputs[0], math_030.inputs[0])
    #math_030.Value -> compare_003.B
    loft_splines.links.new(math_030.outputs[0], compare_003.inputs[3])
    #curve_line_001.Curve -> resample_curve_003.Curve
    loft_splines.links.new(curve_line_001.outputs[0], resample_curve_003.inputs[0])
    #switch_001.Output -> sample_index.Geometry
    loft_splines.links.new(switch_001.outputs[0], sample_index.inputs[0])
    #math_031.Value -> math_033.Value
    loft_splines.links.new(math_031.outputs[0], math_033.inputs[0])
    #position_002.Position -> sample_index.Value
    loft_splines.links.new(position_002.outputs[0], sample_index.inputs[1])
    #math_030.Value -> math_033.Value
    loft_splines.links.new(math_030.outputs[0], math_033.inputs[1])
    #duplicate_elements_001.Geometry -> set_position_003.Geometry
    loft_splines.links.new(duplicate_elements_001.outputs[0], set_position_003.inputs[0])
    #math_032.Value -> switch_012.False
    loft_splines.links.new(math_032.outputs[0], switch_012.inputs[1])
    #boolean_math.Boolean -> switch.Switch
    loft_splines.links.new(boolean_math.outputs[0], switch.inputs[0])
    #sample_index.Value -> set_position_003.Position
    loft_splines.links.new(sample_index.outputs[0], set_position_003.inputs[2])
    #math_033.Value -> switch_012.True
    loft_splines.links.new(math_033.outputs[0], switch_012.inputs[2])
    #set_position_002.Geometry -> merge_by_distance.Geometry
    loft_splines.links.new(set_position_002.outputs[0], merge_by_distance.inputs[0])
    #switch_001.Output -> domain_size_001.Geometry
    loft_splines.links.new(switch_001.outputs[0], domain_size_001.inputs[0])
    #compare_003.Result -> switch_012.Switch
    loft_splines.links.new(compare_003.outputs[0], switch_012.inputs[0])
    #edge_neighbors.Face Count -> compare.A
    loft_splines.links.new(edge_neighbors.outputs[0], compare.inputs[2])
    #domain_size_001.Spline Count -> resample_curve_003.Count
    loft_splines.links.new(domain_size_001.outputs[4], resample_curve_003.inputs[2])
    #compare.Result -> merge_by_distance.Selection
    loft_splines.links.new(compare.outputs[0], merge_by_distance.inputs[1])
    #math_026.Value -> math_024.Value
    loft_splines.links.new(math_026.outputs[0], math_024.inputs[0])
    #merge_by_distance.Geometry -> switch.True
    loft_splines.links.new(merge_by_distance.outputs[0], switch.inputs[2])
    #math_025.Value -> sample_index.Index
    loft_splines.links.new(math_025.outputs[0], sample_index.inputs[2])
    #switch_003.Output -> math_020.Value
    loft_splines.links.new(switch_003.outputs[0], math_020.inputs[1])
    #set_position_002.Geometry -> switch.False
    loft_splines.links.new(set_position_002.outputs[0], switch.inputs[1])
    #index_006.Index -> math_026.Value
    loft_splines.links.new(index_006.outputs[0], math_026.inputs[0])
    #switch_002.Output -> switch_011.False
    loft_splines.links.new(switch_002.outputs[0], switch_011.inputs[1])
    #math_024.Value -> math_025.Value
    loft_splines.links.new(math_024.outputs[0], math_025.inputs[0])
    #switch_002.Output -> math_027.Value
    loft_splines.links.new(switch_002.outputs[0], math_027.inputs[0])
    #set_spline_resolution_001.Geometry -> set_spline_type_002.Curve
    loft_splines.links.new(set_spline_resolution_001.outputs[0], set_spline_type_002.inputs[0])
    #duplicate_elements_001.Duplicate Index -> math_025.Value
    loft_splines.links.new(duplicate_elements_001.outputs[1], math_025.inputs[1])
    #math_027.Value -> switch_011.True
    loft_splines.links.new(math_027.outputs[0], switch_011.inputs[2])
    #set_spline_type_002.Curve -> resample_curve_006.Curve
    loft_splines.links.new(set_spline_type_002.outputs[0], resample_curve_006.inputs[0])
    #switch_002.Output -> math_024.Value
    loft_splines.links.new(switch_002.outputs[0], math_024.inputs[1])
    #switch_011.Output -> grid_001.Vertices X
    loft_splines.links.new(switch_011.outputs[0], grid_001.inputs[2])
    #resample_curve_006.Curve -> switch_010.True
    loft_splines.links.new(resample_curve_006.outputs[0], switch_010.inputs[2])
    #switch_002.Output -> duplicate_elements_001.Amount
    loft_splines.links.new(switch_002.outputs[0], duplicate_elements_001.inputs[2])
    #switch_002.Output -> math_034.Value
    loft_splines.links.new(switch_002.outputs[0], math_034.inputs[0])
    #switch_010.Output -> switch_018.False
    loft_splines.links.new(switch_010.outputs[0], switch_018.inputs[1])
    #domain_size_001.Spline Count -> math_026.Value
    loft_splines.links.new(domain_size_001.outputs[4], math_026.inputs[1])
    #math_023.Value -> math_034.Value
    loft_splines.links.new(math_023.outputs[0], math_034.inputs[1])
    #subdivide_curve_001.Curve -> switch_018.True
    loft_splines.links.new(subdivide_curve_001.outputs[0], switch_018.inputs[2])
    #set_spline_type_001.Curve -> set_handle_type_001.Curve
    loft_splines.links.new(set_spline_type_001.outputs[0], set_handle_type_001.inputs[0])
    #index_006.Index -> compare_004.A
    loft_splines.links.new(index_006.outputs[0], compare_004.inputs[2])
    #set_spline_cyclic_002.Geometry -> subdivide_curve_001.Curve
    loft_splines.links.new(set_spline_cyclic_002.outputs[0], subdivide_curve_001.inputs[0])
    #math_034.Value -> compare_004.B
    loft_splines.links.new(math_034.outputs[0], compare_004.inputs[3])
    #math.Value -> switch_018.Switch
    loft_splines.links.new(math.outputs[0], switch_018.inputs[0])
    #position_002.Position -> sample_index_001.Value
    loft_splines.links.new(position_002.outputs[0], sample_index_001.inputs[1])
    #index_006.Index -> math_035.Value
    loft_splines.links.new(index_006.outputs[0], math_035.inputs[0])
    #resample_curve_004.Curve -> switch_001.True
    loft_splines.links.new(resample_curve_004.outputs[0], switch_001.inputs[2])
    #math_023.Value -> math_035.Value
    loft_splines.links.new(math_023.outputs[0], math_035.inputs[1])
    #store_named_attribute.Geometry -> set_position_002.Geometry
    loft_splines.links.new(store_named_attribute.outputs[0], set_position_002.inputs[0])
    #sample_index_001.Value -> set_position_002.Position
    loft_splines.links.new(sample_index_001.outputs[0], set_position_002.inputs[2])
    #index_006.Index -> switch_016.False
    loft_splines.links.new(index_006.outputs[0], switch_016.inputs[1])
    #domain_size_001.Spline Count -> math_020.Value
    loft_splines.links.new(domain_size_001.outputs[4], math_020.inputs[0])
    #switch_012.Output -> switch_016.True
    loft_splines.links.new(switch_012.outputs[0], switch_016.inputs[2])
    #math_001.Value -> switch_002.False
    loft_splines.links.new(math_001.outputs[0], switch_002.inputs[1])
    #math_021.Value -> math_022.Value
    loft_splines.links.new(math_021.outputs[0], math_022.inputs[0])
    #switch_016.Output -> switch_013.False
    loft_splines.links.new(switch_016.outputs[0], switch_013.inputs[1])
    #domain_size_001.Point Count -> math_001.Value
    loft_splines.links.new(domain_size_001.outputs[0], math_001.inputs[0])
    #math_020.Value -> math_022.Value
    loft_splines.links.new(math_020.outputs[0], math_022.inputs[1])
    #compare_004.Result -> switch_013.Switch
    loft_splines.links.new(compare_004.outputs[0], switch_013.inputs[0])
    #domain_size_001.Spline Count -> math_001.Value
    loft_splines.links.new(domain_size_001.outputs[4], math_001.inputs[1])
    #math_022.Value -> math_023.Value
    loft_splines.links.new(math_022.outputs[0], math_023.inputs[0])
    #math_035.Value -> switch_013.True
    loft_splines.links.new(math_035.outputs[0], switch_013.inputs[2])
    #grid_001.Mesh -> store_named_attribute.Geometry
    loft_splines.links.new(grid_001.outputs[0], store_named_attribute.inputs[0])
    #set_spline_cyclic_002.Geometry -> set_spline_resolution_001.Geometry
    loft_splines.links.new(set_spline_cyclic_002.outputs[0], set_spline_resolution_001.inputs[0])
    #switch_016.Output -> switch_014.False
    loft_splines.links.new(switch_016.outputs[0], switch_014.inputs[1])
    #grid_001.UV Map -> store_named_attribute.Value
    loft_splines.links.new(grid_001.outputs[1], store_named_attribute.inputs[3])
    #set_spline_resolution_001.Geometry -> set_spline_type_001.Curve
    loft_splines.links.new(set_spline_resolution_001.outputs[0], set_spline_type_001.inputs[0])
    #switch_013.Output -> switch_014.True
    loft_splines.links.new(switch_013.outputs[0], switch_014.inputs[2])
    #switch_018.Output -> curve_to_mesh.Curve
    loft_splines.links.new(switch_018.outputs[0], curve_to_mesh.inputs[0])
    #math_023.Value -> grid_001.Vertices Y
    loft_splines.links.new(math_023.outputs[0], grid_001.inputs[3])
    #set_handle_type_001.Curve -> resample_curve_005.Curve
    loft_splines.links.new(set_handle_type_001.outputs[0], resample_curve_005.inputs[0])
    #math_002.Value -> delete_geometry.Selection
    loft_splines.links.new(math_002.outputs[0], delete_geometry.inputs[1])
    #index_006.Index -> compare_005.A
    loft_splines.links.new(index_006.outputs[0], compare_005.inputs[2])
    #switch_018.Output -> viewer.Geometry
    loft_splines.links.new(switch_018.outputs[0], viewer.inputs[0])
    #math_019.Value -> set_spline_resolution_001.Resolution
    loft_splines.links.new(math_019.outputs[0], set_spline_resolution_001.inputs[2])
    #switch_014.Output -> switch_015.False
    loft_splines.links.new(switch_014.outputs[0], switch_015.inputs[1])
    #curve_to_mesh.Mesh -> geometry_proximity.Geometry
    loft_splines.links.new(curve_to_mesh.outputs[0], geometry_proximity.inputs[0])
    #resample_curve_005.Curve -> switch_010.False
    loft_splines.links.new(resample_curve_005.outputs[0], switch_010.inputs[1])
    #compare_005.Result -> switch_015.Switch
    loft_splines.links.new(compare_005.outputs[0], switch_015.inputs[0])
    #geometry_proximity.Distance -> math_002.Value
    loft_splines.links.new(geometry_proximity.outputs[1], math_002.inputs[0])
    #switch_018.Output -> sample_index_001.Geometry
    loft_splines.links.new(switch_018.outputs[0], sample_index_001.inputs[0])
    #switch_011.Output -> math_037.Value
    loft_splines.links.new(switch_011.outputs[0], math_037.inputs[0])
    #switch.Output -> delete_geometry.Geometry
    loft_splines.links.new(switch.outputs[0], delete_geometry.inputs[0])
    #set_position_003.Geometry -> set_spline_cyclic_002.Geometry
    loft_splines.links.new(set_position_003.outputs[0], set_spline_cyclic_002.inputs[0])
    #math_023.Value -> math_037.Value
    loft_splines.links.new(math_023.outputs[0], math_037.inputs[1])
    #index_006.Index -> math_028.Value
    loft_splines.links.new(index_006.outputs[0], math_028.inputs[0])
    #math_037.Value -> math_036.Value
    loft_splines.links.new(math_037.outputs[0], math_036.inputs[0])
    #math_028.Value -> math_031.Value
    loft_splines.links.new(math_028.outputs[0], math_031.inputs[0])
    #math_036.Value -> compare_005.B
    loft_splines.links.new(math_036.outputs[0], compare_005.inputs[3])
    #math_023.Value -> math_028.Value
    loft_splines.links.new(math_023.outputs[0], math_028.inputs[1])
    #index_006.Index -> math_032.Value
    loft_splines.links.new(index_006.outputs[0], math_032.inputs[0])
    #math_031.Value -> math_032.Value
    loft_splines.links.new(math_031.outputs[0], math_032.inputs[1])
    #switch_014.Output -> switch_017.False
    loft_splines.links.new(switch_014.outputs[0], switch_017.inputs[1])
    #index_006.Index -> math_029.Value
    loft_splines.links.new(index_006.outputs[0], math_029.inputs[0])
    #switch_015.Output -> switch_017.True
    loft_splines.links.new(switch_015.outputs[0], switch_017.inputs[2])
    #math_023.Value -> math_029.Value
    loft_splines.links.new(math_023.outputs[0], math_029.inputs[1])
    #switch_017.Output -> sample_index_001.Index
    loft_splines.links.new(switch_017.outputs[0], sample_index_001.inputs[2])
    #group_input.Switch -> switch_003.Switch
    loft_splines.links.new(group_input.outputs[2], switch_003.inputs[0])
    #group_input.Switch -> boolean_math_001.Boolean
    loft_splines.links.new(group_input.outputs[2], boolean_math_001.inputs[1])
    #group_input.Switch -> switch_016.Switch
    loft_splines.links.new(group_input.outputs[2], switch_016.inputs[0])
    #group_input.Switch -> set_spline_cyclic_002.Cyclic
    loft_splines.links.new(group_input.outputs[2], set_spline_cyclic_002.inputs[2])
    #group_input.Switch -> boolean_math.Boolean
    loft_splines.links.new(group_input.outputs[2], boolean_math.inputs[1])
    #group_input.Value -> math_021.Value
    loft_splines.links.new(group_input.outputs[1], math_021.inputs[0])
    #group_input.Value -> math_019.Value
    loft_splines.links.new(group_input.outputs[1], math_019.inputs[0])
    #group_input.Value -> subdivide_curve_001.Cuts
    loft_splines.links.new(group_input.outputs[1], subdivide_curve_001.inputs[1])
    #group_input.Switch -> switch_011.Switch
    loft_splines.links.new(group_input.outputs[0], switch_011.inputs[0])
    #group_input.Switch -> boolean_math_001.Boolean
    loft_splines.links.new(group_input.outputs[0], boolean_math_001.inputs[0])
    #group_input.Switch -> switch_014.Switch
    loft_splines.links.new(group_input.outputs[0], switch_014.inputs[0])
    #group_input.Switch -> boolean_math.Boolean
    loft_splines.links.new(group_input.outputs[0], boolean_math.inputs[0])
    #group_input.False -> switch_001.False
    loft_splines.links.new(group_input.outputs[6], switch_001.inputs[1])
    #group_input.False -> resample_curve_004.Curve
    loft_splines.links.new(group_input.outputs[6], resample_curve_004.inputs[0])
    #group_input.Switch -> switch_010.Switch
    loft_splines.links.new(group_input.outputs[3], switch_010.inputs[0])
    #group_input.Switch -> math.Value
    loft_splines.links.new(group_input.outputs[3], math.inputs[0])
    #group_input.Switch -> switch_002.Switch
    loft_splines.links.new(group_input.outputs[4], switch_002.inputs[0])
    #group_input.Switch -> switch_001.Switch
    loft_splines.links.new(group_input.outputs[4], switch_001.inputs[0])
    #group_input.True -> switch_002.True
    loft_splines.links.new(group_input.outputs[5], switch_002.inputs[2])
    #group_input.True -> resample_curve_004.Count
    loft_splines.links.new(group_input.outputs[5], resample_curve_004.inputs[2])
    #delete_geometry.Geometry -> group_output.Geometry
    loft_splines.links.new(delete_geometry.outputs[0], group_output.inputs[0])
    return loft_splines

loft_splines = loft_splines_node_group()

#initialize instances_on_points node group
def instances_on_points_node_group():
    instances_on_points = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "instances on points")

    instances_on_points.color_tag = 'NONE'
    instances_on_points.description = ""
    instances_on_points.default_group_node_width = 140
    

    instances_on_points.is_modifier = True

    #instances_on_points interface
    #Socket Geometry
    geometry_socket_1 = instances_on_points.interface.new_socket(name = "Geometry", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'

    #Socket Curve
    curve_socket = instances_on_points.interface.new_socket(name = "Curve", in_out='INPUT', socket_type = 'NodeSocketObject')
    curve_socket.attribute_domain = 'POINT'

    #Socket Instances
    instances_socket = instances_on_points.interface.new_socket(name = "Instances", in_out='INPUT', socket_type = 'NodeSocketGeometry')
    instances_socket.attribute_domain = 'POINT'


    #initialize instances_on_points nodes
    #node Group Input
    group_input_1 = instances_on_points.nodes.new("NodeGroupInput")
    group_input_1.name = "Group Input"

    #node Group Output
    group_output_1 = instances_on_points.nodes.new("NodeGroupOutput")
    group_output_1.name = "Group Output"
    group_output_1.is_active_output = True

    #node Capture Attribute
    capture_attribute = instances_on_points.nodes.new("GeometryNodeCaptureAttribute")
    capture_attribute.name = "Capture Attribute"
    capture_attribute.active_index = 1
    capture_attribute.capture_items.clear()
    capture_attribute.capture_items.new('FLOAT', "Tangent")
    capture_attribute.capture_items["Tangent"].data_type = 'FLOAT_VECTOR'
    capture_attribute.capture_items.new('FLOAT', "Normal")
    capture_attribute.capture_items["Normal"].data_type = 'FLOAT_VECTOR'
    capture_attribute.domain = 'POINT'

    #node Curve Tangent
    curve_tangent = instances_on_points.nodes.new("GeometryNodeInputTangent")
    curve_tangent.name = "Curve Tangent"

    #node Normal
    normal = instances_on_points.nodes.new("GeometryNodeInputNormal")
    normal.name = "Normal"

    #node Set Spline Resolution
    set_spline_resolution = instances_on_points.nodes.new("GeometryNodeSetSplineResolution")
    set_spline_resolution.name = "Set Spline Resolution"
    #Selection
    set_spline_resolution.inputs[1].default_value = True
    #Resolution
    set_spline_resolution.inputs[2].default_value = 1

    #node Axes to Rotation
    axes_to_rotation = instances_on_points.nodes.new("FunctionNodeAxesToRotation")
    axes_to_rotation.name = "Axes to Rotation"
    axes_to_rotation.primary_axis = 'Z'
    axes_to_rotation.secondary_axis = 'X'

    #node Curve to Points
    curve_to_points = instances_on_points.nodes.new("GeometryNodeCurveToPoints")
    curve_to_points.name = "Curve to Points"
    curve_to_points.mode = 'COUNT'

    #node Instance on Points
    instance_on_points = instances_on_points.nodes.new("GeometryNodeInstanceOnPoints")
    instance_on_points.name = "Instance on Points"
    #Selection
    instance_on_points.inputs[1].default_value = True
    #Pick Instance
    instance_on_points.inputs[3].default_value = True
    #Instance Index
    instance_on_points.inputs[4].default_value = 0
    #Rotation
    instance_on_points.inputs[5].default_value = (0.0, 0.0, 0.0)
    #Scale
    instance_on_points.inputs[6].default_value = (1.0, 1.0, 1.0)

    #node Set Position
    set_position = instances_on_points.nodes.new("GeometryNodeSetPosition")
    set_position.name = "Set Position"
    #Selection
    set_position.inputs[1].default_value = True
    #Position
    set_position.inputs[2].default_value = (0.0, 0.0, 0.0)

    #node Vector Math
    vector_math = instances_on_points.nodes.new("ShaderNodeVectorMath")
    vector_math.name = "Vector Math"
    vector_math.operation = 'SCALE'
    #Scale
    vector_math.inputs[3].default_value = -1.0

    #node Evaluate on Domain
    evaluate_on_domain = instances_on_points.nodes.new("GeometryNodeFieldOnDomain")
    evaluate_on_domain.name = "Evaluate on Domain"
    evaluate_on_domain.data_type = 'FLOAT_VECTOR'
    evaluate_on_domain.domain = 'CURVE'

    #node Position
    position = instances_on_points.nodes.new("GeometryNodeInputPosition")
    position.name = "Position"

    #node Split to Instances
    split_to_instances = instances_on_points.nodes.new("GeometryNodeSplitToInstances")
    split_to_instances.name = "Split to Instances"
    split_to_instances.domain = 'CURVE'
    #Selection
    split_to_instances.inputs[1].default_value = True

    #node Index
    index = instances_on_points.nodes.new("GeometryNodeInputIndex")
    index.name = "Index"

    #node Object Info.001
    object_info_001 = instances_on_points.nodes.new("GeometryNodeObjectInfo")
    object_info_001.name = "Object Info.001"
    object_info_001.transform_space = 'ORIGINAL'
    #As Instance
    object_info_001.inputs[1].default_value = False

    #node Domain Size
    domain_size = instances_on_points.nodes.new("GeometryNodeAttributeDomainSize")
    domain_size.name = "Domain Size"
    domain_size.component = 'INSTANCES'





    #Set locations
    group_input_1.location = (-927.136962890625, -20.12396812438965)
    group_output_1.location = (657.84716796875, -97.55744171142578)
    capture_attribute.location = (-355.6344299316406, -50.691402435302734)
    curve_tangent.location = (-578.3789672851562, -71.52287292480469)
    normal.location = (-582.9609985351562, -127.89032745361328)
    set_spline_resolution.location = (-159.99998474121094, -4.5803985595703125)
    axes_to_rotation.location = (204.70306396484375, -170.9261016845703)
    curve_to_points.location = (137.11985778808594, 61.882667541503906)
    instance_on_points.location = (417.5549621582031, -85.73841857910156)
    set_position.location = (-372.94976806640625, -235.23834228515625)
    vector_math.location = (-564.9046020507812, -303.32171630859375)
    evaluate_on_domain.location = (-761.2567138671875, -391.15313720703125)
    position.location = (-931.967529296875, -505.5574951171875)
    split_to_instances.location = (-170.66258239746094, -246.9695587158203)
    index.location = (-334.5162353515625, -391.7499694824219)
    object_info_001.location = (-590.9154663085938, 152.3704071044922)
    domain_size.location = (26.30615234375, -315.3614501953125)

    #Set dimensions
    group_input_1.width, group_input_1.height = 140.0, 100.0
    group_output_1.width, group_output_1.height = 140.0, 100.0
    capture_attribute.width, capture_attribute.height = 140.0, 100.0
    curve_tangent.width, curve_tangent.height = 140.0, 100.0
    normal.width, normal.height = 140.0, 100.0
    set_spline_resolution.width, set_spline_resolution.height = 140.0, 100.0
    axes_to_rotation.width, axes_to_rotation.height = 140.0, 100.0
    curve_to_points.width, curve_to_points.height = 140.0, 100.0
    instance_on_points.width, instance_on_points.height = 140.0, 100.0
    set_position.width, set_position.height = 140.0, 100.0
    vector_math.width, vector_math.height = 140.0, 100.0
    evaluate_on_domain.width, evaluate_on_domain.height = 140.0, 100.0
    position.width, position.height = 140.0, 100.0
    split_to_instances.width, split_to_instances.height = 140.0, 100.0
    index.width, index.height = 140.0, 100.0
    object_info_001.width, object_info_001.height = 140.0, 100.0
    domain_size.width, domain_size.height = 140.0, 100.0

    #initialize instances_on_points links
    #curve_tangent.Tangent -> capture_attribute.Tangent
    instances_on_points.links.new(curve_tangent.outputs[0], capture_attribute.inputs[1])
    #normal.Normal -> capture_attribute.Normal
    instances_on_points.links.new(normal.outputs[0], capture_attribute.inputs[2])
    #capture_attribute.Geometry -> set_spline_resolution.Geometry
    instances_on_points.links.new(capture_attribute.outputs[0], set_spline_resolution.inputs[0])
    #capture_attribute.Tangent -> axes_to_rotation.Primary Axis
    instances_on_points.links.new(capture_attribute.outputs[1], axes_to_rotation.inputs[0])
    #capture_attribute.Normal -> axes_to_rotation.Secondary Axis
    instances_on_points.links.new(capture_attribute.outputs[2], axes_to_rotation.inputs[1])
    #set_spline_resolution.Geometry -> curve_to_points.Curve
    instances_on_points.links.new(set_spline_resolution.outputs[0], curve_to_points.inputs[0])
    #curve_to_points.Points -> instance_on_points.Points
    instances_on_points.links.new(curve_to_points.outputs[0], instance_on_points.inputs[0])
    #vector_math.Vector -> set_position.Offset
    instances_on_points.links.new(vector_math.outputs[0], set_position.inputs[3])
    #evaluate_on_domain.Value -> vector_math.Vector
    instances_on_points.links.new(evaluate_on_domain.outputs[0], vector_math.inputs[0])
    #position.Position -> evaluate_on_domain.Value
    instances_on_points.links.new(position.outputs[0], evaluate_on_domain.inputs[0])
    #set_position.Geometry -> split_to_instances.Geometry
    instances_on_points.links.new(set_position.outputs[0], split_to_instances.inputs[0])
    #index.Index -> split_to_instances.Group ID
    instances_on_points.links.new(index.outputs[0], split_to_instances.inputs[2])
    #split_to_instances.Instances -> instance_on_points.Instance
    instances_on_points.links.new(split_to_instances.outputs[0], instance_on_points.inputs[2])
    #object_info_001.Geometry -> capture_attribute.Geometry
    instances_on_points.links.new(object_info_001.outputs[4], capture_attribute.inputs[0])
    #group_input_1.Curve -> object_info_001.Object
    instances_on_points.links.new(group_input_1.outputs[0], object_info_001.inputs[0])
    #group_input_1.Instances -> set_position.Geometry
    instances_on_points.links.new(group_input_1.outputs[1], set_position.inputs[0])
    #split_to_instances.Instances -> domain_size.Geometry
    instances_on_points.links.new(split_to_instances.outputs[0], domain_size.inputs[0])
    #domain_size.Instance Count -> curve_to_points.Count
    instances_on_points.links.new(domain_size.outputs[5], curve_to_points.inputs[1])
    #instance_on_points.Instances -> group_output_1.Geometry
    instances_on_points.links.new(instance_on_points.outputs[0], group_output_1.inputs[0])
    return instances_on_points

instances_on_points = instances_on_points_node_group()

#initialize loft_mesh node group
def loft_mesh_node_group():
    loft_mesh = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "Loft-mesh")

    loft_mesh.color_tag = 'NONE'
    loft_mesh.description = ""
    loft_mesh.default_group_node_width = 140
    


    #loft_mesh interface
    #Socket Geometry
    geometry_socket_2 = loft_mesh.interface.new_socket(name = "Geometry", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket_2.attribute_domain = 'POINT'

    #Socket Switch
    switch_socket_4 = loft_mesh.interface.new_socket(name = "Switch", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_socket_4.default_value = False
    switch_socket_4.attribute_domain = 'POINT'

    #Socket Value
    value_socket_1 = loft_mesh.interface.new_socket(name = "Value", in_out='INPUT', socket_type = 'NodeSocketFloat')
    value_socket_1.default_value = 0.5
    value_socket_1.min_value = -10000.0
    value_socket_1.max_value = 10000.0
    value_socket_1.subtype = 'NONE'
    value_socket_1.attribute_domain = 'POINT'

    #Socket Switch
    switch_socket_5 = loft_mesh.interface.new_socket(name = "Switch", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_socket_5.default_value = False
    switch_socket_5.attribute_domain = 'POINT'

    #Socket Switch
    switch_socket_6 = loft_mesh.interface.new_socket(name = "Switch", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_socket_6.default_value = False
    switch_socket_6.attribute_domain = 'POINT'

    #Socket Switch
    switch_socket_7 = loft_mesh.interface.new_socket(name = "Switch", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_socket_7.default_value = False
    switch_socket_7.attribute_domain = 'POINT'

    #Socket True
    true_socket_1 = loft_mesh.interface.new_socket(name = "True", in_out='INPUT', socket_type = 'NodeSocketInt')
    true_socket_1.default_value = 0
    true_socket_1.min_value = -2147483648
    true_socket_1.max_value = 2147483647
    true_socket_1.subtype = 'NONE'
    true_socket_1.attribute_domain = 'POINT'

    #Socket Splines
    splines_socket = loft_mesh.interface.new_socket(name = "Splines", in_out='INPUT', socket_type = 'NodeSocketGeometry')
    splines_socket.attribute_domain = 'POINT'


    #initialize loft_mesh nodes
    #node Group Output
    group_output_2 = loft_mesh.nodes.new("NodeGroupOutput")
    group_output_2.name = "Group Output"
    group_output_2.is_active_output = True

    #node Group Input
    group_input_2 = loft_mesh.nodes.new("NodeGroupInput")
    group_input_2.name = "Group Input"

    #node Store Named Attribute
    store_named_attribute_1 = loft_mesh.nodes.new("GeometryNodeStoreNamedAttribute")
    store_named_attribute_1.name = "Store Named Attribute"
    store_named_attribute_1.data_type = 'FLOAT_VECTOR'
    store_named_attribute_1.domain = 'CORNER'
    #Selection
    store_named_attribute_1.inputs[1].default_value = True
    #Name
    store_named_attribute_1.inputs[2].default_value = "uv_map"

    #node Math.024
    math_024_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_024_1.name = "Math.024"
    math_024_1.operation = 'MULTIPLY'
    math_024_1.use_clamp = False

    #node Math.026
    math_026_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_026_1.name = "Math.026"
    math_026_1.operation = 'MODULO'
    math_026_1.use_clamp = False

    #node Duplicate Elements.001
    duplicate_elements_001_1 = loft_mesh.nodes.new("GeometryNodeDuplicateElements")
    duplicate_elements_001_1.name = "Duplicate Elements.001"
    duplicate_elements_001_1.domain = 'SPLINE'
    #Selection
    duplicate_elements_001_1.inputs[1].default_value = True

    #node Resample Curve.003
    resample_curve_003_1 = loft_mesh.nodes.new("GeometryNodeResampleCurve")
    resample_curve_003_1.name = "Resample Curve.003"
    resample_curve_003_1.mode = 'COUNT'
    #Selection
    resample_curve_003_1.inputs[1].default_value = True

    #node Math.025
    math_025_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_025_1.name = "Math.025"
    math_025_1.operation = 'ADD'
    math_025_1.use_clamp = False

    #node Set Position.003
    set_position_003_1 = loft_mesh.nodes.new("GeometryNodeSetPosition")
    set_position_003_1.name = "Set Position.003"
    #Selection
    set_position_003_1.inputs[1].default_value = True
    #Offset
    set_position_003_1.inputs[3].default_value = (0.0, 0.0, 0.0)

    #node Switch.011
    switch_011_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_011_1.name = "Switch.011"
    switch_011_1.input_type = 'INT'

    #node Math.027
    math_027_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_027_1.name = "Math.027"
    math_027_1.operation = 'ADD'
    math_027_1.use_clamp = False
    #Value_001
    math_027_1.inputs[1].default_value = 1.0

    #node Math.020
    math_020_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_020_1.name = "Math.020"
    math_020_1.operation = 'SUBTRACT'
    math_020_1.use_clamp = False

    #node Math.021
    math_021_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_021_1.name = "Math.021"
    math_021_1.operation = 'ADD'
    math_021_1.use_clamp = False
    #Value_001
    math_021_1.inputs[1].default_value = 1.0

    #node Math.022
    math_022_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_022_1.name = "Math.022"
    math_022_1.operation = 'MULTIPLY'
    math_022_1.use_clamp = False

    #node Math.023
    math_023_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_023_1.name = "Math.023"
    math_023_1.operation = 'ADD'
    math_023_1.use_clamp = False
    #Value_001
    math_023_1.inputs[1].default_value = 1.0

    #node Switch.003
    switch_003_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_003_1.name = "Switch.003"
    switch_003_1.input_type = 'FLOAT'
    #False
    switch_003_1.inputs[1].default_value = 1.0
    #True
    switch_003_1.inputs[2].default_value = 0.0

    #node Grid.001
    grid_001_1 = loft_mesh.nodes.new("GeometryNodeMeshGrid")
    grid_001_1.name = "Grid.001"
    #Size X
    grid_001_1.inputs[0].default_value = 1.0
    #Size Y
    grid_001_1.inputs[1].default_value = 1.0

    #node Math.028
    math_028_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_028_1.name = "Math.028"
    math_028_1.operation = 'DIVIDE'
    math_028_1.use_clamp = False

    #node Math.029
    math_029_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_029_1.name = "Math.029"
    math_029_1.operation = 'MODULO'
    math_029_1.use_clamp = False

    #node Math.031
    math_031_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_031_1.name = "Math.031"
    math_031_1.operation = 'FLOOR'
    math_031_1.use_clamp = False

    #node Math.032
    math_032_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_032_1.name = "Math.032"
    math_032_1.operation = 'SUBTRACT'
    math_032_1.use_clamp = False

    #node Compare.003
    compare_003_1 = loft_mesh.nodes.new("FunctionNodeCompare")
    compare_003_1.name = "Compare.003"
    compare_003_1.data_type = 'INT'
    compare_003_1.mode = 'ELEMENT'
    compare_003_1.operation = 'EQUAL'

    #node Math.033
    math_033_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_033_1.name = "Math.033"
    math_033_1.operation = 'MULTIPLY'
    math_033_1.use_clamp = False

    #node Switch.012
    switch_012_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_012_1.name = "Switch.012"
    switch_012_1.input_type = 'FLOAT'

    #node Position.002
    position_002_1 = loft_mesh.nodes.new("GeometryNodeInputPosition")
    position_002_1.name = "Position.002"

    #node Math.030
    math_030_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_030_1.name = "Math.030"
    math_030_1.operation = 'SUBTRACT'
    math_030_1.use_clamp = False
    #Value_001
    math_030_1.inputs[1].default_value = 1.0

    #node Math.034
    math_034_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_034_1.name = "Math.034"
    math_034_1.operation = 'MULTIPLY'
    math_034_1.use_clamp = False

    #node Compare.004
    compare_004_1 = loft_mesh.nodes.new("FunctionNodeCompare")
    compare_004_1.name = "Compare.004"
    compare_004_1.data_type = 'INT'
    compare_004_1.mode = 'ELEMENT'
    compare_004_1.operation = 'GREATER_EQUAL'

    #node Math.035
    math_035_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_035_1.name = "Math.035"
    math_035_1.operation = 'MODULO'
    math_035_1.use_clamp = False

    #node Boolean Math.001
    boolean_math_001_1 = loft_mesh.nodes.new("FunctionNodeBooleanMath")
    boolean_math_001_1.name = "Boolean Math.001"
    boolean_math_001_1.operation = 'AND'

    #node Switch.017
    switch_017_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_017_1.name = "Switch.017"
    switch_017_1.input_type = 'INT'

    #node Switch.014
    switch_014_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_014_1.name = "Switch.014"
    switch_014_1.input_type = 'INT'

    #node Compare.005
    compare_005_1 = loft_mesh.nodes.new("FunctionNodeCompare")
    compare_005_1.name = "Compare.005"
    compare_005_1.data_type = 'INT'
    compare_005_1.mode = 'ELEMENT'
    compare_005_1.operation = 'EQUAL'

    #node Switch.015
    switch_015_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_015_1.name = "Switch.015"
    switch_015_1.input_type = 'INT'
    #True
    switch_015_1.inputs[2].default_value = 0

    #node Math.036
    math_036_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_036_1.name = "Math.036"
    math_036_1.operation = 'SUBTRACT'
    math_036_1.use_clamp = False
    #Value_001
    math_036_1.inputs[1].default_value = 1.0

    #node Math.037
    math_037_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_037_1.name = "Math.037"
    math_037_1.operation = 'MULTIPLY'
    math_037_1.use_clamp = False

    #node Switch.016
    switch_016_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_016_1.name = "Switch.016"
    switch_016_1.input_type = 'INT'

    #node Switch.013
    switch_013_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_013_1.name = "Switch.013"
    switch_013_1.input_type = 'INT'

    #node Set Spline Cyclic.002
    set_spline_cyclic_002_1 = loft_mesh.nodes.new("GeometryNodeSetSplineCyclic")
    set_spline_cyclic_002_1.name = "Set Spline Cyclic.002"
    #Selection
    set_spline_cyclic_002_1.inputs[1].default_value = True

    #node Math.019
    math_019_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_019_1.name = "Math.019"
    math_019_1.operation = 'ADD'
    math_019_1.use_clamp = False
    #Value_001
    math_019_1.inputs[1].default_value = 1.0

    #node Compare
    compare_1 = loft_mesh.nodes.new("FunctionNodeCompare")
    compare_1.name = "Compare"
    compare_1.data_type = 'INT'
    compare_1.mode = 'ELEMENT'
    compare_1.operation = 'EQUAL'
    #B_INT
    compare_1.inputs[3].default_value = 1

    #node Edge Neighbors
    edge_neighbors_1 = loft_mesh.nodes.new("GeometryNodeInputMeshEdgeNeighbors")
    edge_neighbors_1.name = "Edge Neighbors"

    #node Set Position.002
    set_position_002_1 = loft_mesh.nodes.new("GeometryNodeSetPosition")
    set_position_002_1.name = "Set Position.002"
    #Selection
    set_position_002_1.inputs[1].default_value = True
    #Offset
    set_position_002_1.inputs[3].default_value = (0.0, 0.0, 0.0)

    #node Merge by Distance
    merge_by_distance_1 = loft_mesh.nodes.new("GeometryNodeMergeByDistance")
    merge_by_distance_1.name = "Merge by Distance"
    merge_by_distance_1.mode = 'ALL'
    #Distance
    merge_by_distance_1.inputs[2].default_value = 9.999999747378752e-06

    #node Boolean Math
    boolean_math_1 = loft_mesh.nodes.new("FunctionNodeBooleanMath")
    boolean_math_1.name = "Boolean Math"
    boolean_math_1.operation = 'OR'

    #node Switch
    switch_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_1.name = "Switch"
    switch_1.input_type = 'GEOMETRY'

    #node Switch.010
    switch_010_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_010_1.name = "Switch.010"
    switch_010_1.input_type = 'GEOMETRY'

    #node Resample Curve.006
    resample_curve_006_1 = loft_mesh.nodes.new("GeometryNodeResampleCurve")
    resample_curve_006_1.name = "Resample Curve.006"
    resample_curve_006_1.mode = 'EVALUATED'
    #Selection
    resample_curve_006_1.inputs[1].default_value = True

    #node Set Spline Type.002
    set_spline_type_002_1 = loft_mesh.nodes.new("GeometryNodeCurveSplineType")
    set_spline_type_002_1.name = "Set Spline Type.002"
    set_spline_type_002_1.spline_type = 'CATMULL_ROM'
    #Selection
    set_spline_type_002_1.inputs[1].default_value = True

    #node Set Spline Type.001
    set_spline_type_001_1 = loft_mesh.nodes.new("GeometryNodeCurveSplineType")
    set_spline_type_001_1.name = "Set Spline Type.001"
    set_spline_type_001_1.spline_type = 'BEZIER'
    #Selection
    set_spline_type_001_1.inputs[1].default_value = True

    #node Set Handle Type.001
    set_handle_type_001_1 = loft_mesh.nodes.new("GeometryNodeCurveSetHandles")
    set_handle_type_001_1.name = "Set Handle Type.001"
    set_handle_type_001_1.handle_type = 'AUTO'
    set_handle_type_001_1.mode = {'LEFT', 'RIGHT'}
    #Selection
    set_handle_type_001_1.inputs[1].default_value = True

    #node Resample Curve.005
    resample_curve_005_1 = loft_mesh.nodes.new("GeometryNodeResampleCurve")
    resample_curve_005_1.name = "Resample Curve.005"
    resample_curve_005_1.mode = 'EVALUATED'
    #Selection
    resample_curve_005_1.inputs[1].default_value = True

    #node Set Spline Resolution.001
    set_spline_resolution_001_1 = loft_mesh.nodes.new("GeometryNodeSetSplineResolution")
    set_spline_resolution_001_1.name = "Set Spline Resolution.001"
    #Selection
    set_spline_resolution_001_1.inputs[1].default_value = True

    #node Subdivide Curve.001
    subdivide_curve_001_1 = loft_mesh.nodes.new("GeometryNodeSubdivideCurve")
    subdivide_curve_001_1.name = "Subdivide Curve.001"

    #node Math
    math_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_1.name = "Math"
    math_1.operation = 'SUBTRACT'
    math_1.use_clamp = False
    #Value_001
    math_1.inputs[1].default_value = 1.0

    #node Switch.018
    switch_018_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_018_1.name = "Switch.018"
    switch_018_1.input_type = 'GEOMETRY'

    #node Index.006
    index_006_1 = loft_mesh.nodes.new("GeometryNodeInputIndex")
    index_006_1.name = "Index.006"

    #node Switch.002
    switch_002_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_002_1.name = "Switch.002"
    switch_002_1.input_type = 'INT'

    #node Math.001
    math_001_1 = loft_mesh.nodes.new("ShaderNodeMath")
    math_001_1.name = "Math.001"
    math_001_1.operation = 'DIVIDE'
    math_001_1.use_clamp = False

    #node Domain Size.001
    domain_size_001_1 = loft_mesh.nodes.new("GeometryNodeAttributeDomainSize")
    domain_size_001_1.name = "Domain Size.001"
    domain_size_001_1.component = 'CURVE'

    #node Switch.001
    switch_001_1 = loft_mesh.nodes.new("GeometryNodeSwitch")
    switch_001_1.name = "Switch.001"
    switch_001_1.input_type = 'GEOMETRY'

    #node Resample Curve.004
    resample_curve_004_1 = loft_mesh.nodes.new("GeometryNodeResampleCurve")
    resample_curve_004_1.name = "Resample Curve.004"
    resample_curve_004_1.mode = 'COUNT'
    #Selection
    resample_curve_004_1.inputs[1].default_value = True

    #node Curve Line.001
    curve_line_001_1 = loft_mesh.nodes.new("GeometryNodeCurvePrimitiveLine")
    curve_line_001_1.name = "Curve Line.001"
    curve_line_001_1.mode = 'POINTS'
    #Start
    curve_line_001_1.inputs[0].default_value = (0.0, 0.0, 0.0)
    #End
    curve_line_001_1.inputs[1].default_value = (0.0, 0.0, 1.0)

    #node Sample Index
    sample_index_1 = loft_mesh.nodes.new("GeometryNodeSampleIndex")
    sample_index_1.name = "Sample Index"
    sample_index_1.clamp = True
    sample_index_1.data_type = 'FLOAT_VECTOR'
    sample_index_1.domain = 'POINT'

    #node Sample Index.001
    sample_index_001_1 = loft_mesh.nodes.new("GeometryNodeSampleIndex")
    sample_index_001_1.name = "Sample Index.001"
    sample_index_001_1.clamp = True
    sample_index_001_1.data_type = 'FLOAT_VECTOR'
    sample_index_001_1.domain = 'POINT'

    #Set locations
    group_output_2.location = (2513.917724609375, 0.0)
    group_input_2.location = (-2523.917724609375, 0.0)
    store_named_attribute_1.location = (81.813232421875, 70.95946502685547)
    math_024_1.location = (-1120.06201171875, 104.01547241210938)
    math_026_1.location = (-1300.06201171875, 104.01547241210938)
    duplicate_elements_001_1.location = (-1120.06201171875, 304.0154724121094)
    resample_curve_003_1.location = (-1300.06201171875, 304.0154724121094)
    math_025_1.location = (-940.06201171875, 104.01547241210938)
    set_position_003_1.location = (-560.06201171875, 324.0154724121094)
    switch_011_1.location = (-520.06201171875, 24.015472412109375)
    math_027_1.location = (-700.06201171875, -95.98452758789062)
    math_020_1.location = (-880.06201171875, -395.9845275878906)
    math_021_1.location = (-880.06201171875, -235.98452758789062)
    math_022_1.location = (-700.06201171875, -295.9845275878906)
    math_023_1.location = (-520.06201171875, -295.9845275878906)
    switch_003_1.location = (-1060.06201171875, -395.9845275878906)
    grid_001_1.location = (-200.864013671875, 37.077415466308594)
    math_028_1.location = (-180.06201171875, -215.98452758789062)
    math_029_1.location = (-180.06201171875, -375.9845275878906)
    math_031_1.location = (-0.06201171875, -215.98452758789062)
    math_032_1.location = (179.93798828125, -215.98452758789062)
    compare_003_1.location = (-0.06201171875, -375.9845275878906)
    math_033_1.location = (179.93798828125, -375.9845275878906)
    switch_012_1.location = (359.93798828125, -215.98452758789062)
    position_002_1.location = (-940.06201171875, 204.01547241210938)
    math_030_1.location = (-180.06201171875, -535.9844970703125)
    math_034_1.location = (-0.06201171875, -555.9844970703125)
    compare_004_1.location = (179.93798828125, -555.9844970703125)
    math_035_1.location = (179.93798828125, -735.9844970703125)
    boolean_math_001_1.location = (1139.93798828125, 64.01547241210938)
    switch_017_1.location = (1319.93798828125, 64.01547241210938)
    switch_014_1.location = (959.93798828125, 64.01547241210938)
    compare_005_1.location = (959.93798828125, -115.98452758789062)
    switch_015_1.location = (1139.93798828125, -95.98452758789062)
    math_036_1.location = (779.93798828125, -275.9845275878906)
    math_037_1.location = (599.93798828125, -275.9845275878906)
    switch_016_1.location = (599.93798828125, -15.984527587890625)
    switch_013_1.location = (779.93798828125, -15.984527587890625)
    set_spline_cyclic_002_1.location = (-320.06201171875, 324.0154724121094)
    math_019_1.location = (-320.06201171875, 504.0154724121094)
    compare_1.location = (1699.93798828125, 44.015472412109375)
    edge_neighbors_1.location = (1519.93798828125, -35.984527587890625)
    set_position_002_1.location = (1699.93798828125, 284.0154724121094)
    merge_by_distance_1.location = (1899.93798828125, 124.01547241210938)
    boolean_math_1.location = (1699.93798828125, -135.98452758789062)
    switch_1.location = (2060.2763671875, 271.95867919921875)
    switch_010_1.location = (639.93798828125, 604.0155029296875)
    resample_curve_006_1.location = (259.93798828125, 424.0154724121094)
    set_spline_type_002_1.location = (79.93798828125, 424.0154724121094)
    set_spline_type_001_1.location = (79.93798828125, 604.0155029296875)
    set_handle_type_001_1.location = (259.93798828125, 604.0155029296875)
    resample_curve_005_1.location = (439.93798828125, 604.0155029296875)
    set_spline_resolution_001_1.location = (-100.06201171875, 444.0154724121094)
    subdivide_curve_001_1.location = (-100.06201171875, 284.0154724121094)
    math_1.location = (639.93798828125, 424.0154724121094)
    switch_018_1.location = (879.93798828125, 464.0154724121094)
    index_006_1.location = (-1520.06201171875, -15.984527587890625)
    switch_002_1.location = (-1287.87158203125, 488.34979248046875)
    math_001_1.location = (-1477.8271484375, 607.7685546875)
    domain_size_001_1.location = (-1663.9267578125, 595.8740234375)
    switch_001_1.location = (-1875.316162109375, 583.3035888671875)
    resample_curve_004_1.location = (-2298.806396484375, 604.2227783203125)
    curve_line_001_1.location = (-2323.917724609375, 40.712921142578125)
    sample_index_1.location = (-740.06201171875, 324.0154724121094)
    sample_index_001_1.location = (1440.6153564453125, 299.90179443359375)

    #Set dimensions
    group_output_2.width, group_output_2.height = 140.0, 100.0
    group_input_2.width, group_input_2.height = 140.0, 100.0
    store_named_attribute_1.width, store_named_attribute_1.height = 140.0, 100.0
    math_024_1.width, math_024_1.height = 140.0, 100.0
    math_026_1.width, math_026_1.height = 140.0, 100.0
    duplicate_elements_001_1.width, duplicate_elements_001_1.height = 140.0, 100.0
    resample_curve_003_1.width, resample_curve_003_1.height = 140.0, 100.0
    math_025_1.width, math_025_1.height = 140.0, 100.0
    set_position_003_1.width, set_position_003_1.height = 140.0, 100.0
    switch_011_1.width, switch_011_1.height = 140.0, 100.0
    math_027_1.width, math_027_1.height = 140.0, 100.0
    math_020_1.width, math_020_1.height = 140.0, 100.0
    math_021_1.width, math_021_1.height = 140.0, 100.0
    math_022_1.width, math_022_1.height = 140.0, 100.0
    math_023_1.width, math_023_1.height = 140.0, 100.0
    switch_003_1.width, switch_003_1.height = 140.0, 100.0
    grid_001_1.width, grid_001_1.height = 140.0, 100.0
    math_028_1.width, math_028_1.height = 140.0, 100.0
    math_029_1.width, math_029_1.height = 140.0, 100.0
    math_031_1.width, math_031_1.height = 140.0, 100.0
    math_032_1.width, math_032_1.height = 140.0, 100.0
    compare_003_1.width, compare_003_1.height = 140.0, 100.0
    math_033_1.width, math_033_1.height = 140.0, 100.0
    switch_012_1.width, switch_012_1.height = 140.0, 100.0
    position_002_1.width, position_002_1.height = 140.0, 100.0
    math_030_1.width, math_030_1.height = 140.0, 100.0
    math_034_1.width, math_034_1.height = 140.0, 100.0
    compare_004_1.width, compare_004_1.height = 140.0, 100.0
    math_035_1.width, math_035_1.height = 140.0, 100.0
    boolean_math_001_1.width, boolean_math_001_1.height = 140.0, 100.0
    switch_017_1.width, switch_017_1.height = 140.0, 100.0
    switch_014_1.width, switch_014_1.height = 140.0, 100.0
    compare_005_1.width, compare_005_1.height = 140.0, 100.0
    switch_015_1.width, switch_015_1.height = 140.0, 100.0
    math_036_1.width, math_036_1.height = 140.0, 100.0
    math_037_1.width, math_037_1.height = 140.0, 100.0
    switch_016_1.width, switch_016_1.height = 140.0, 100.0
    switch_013_1.width, switch_013_1.height = 140.0, 100.0
    set_spline_cyclic_002_1.width, set_spline_cyclic_002_1.height = 140.0, 100.0
    math_019_1.width, math_019_1.height = 140.0, 100.0
    compare_1.width, compare_1.height = 140.0, 100.0
    edge_neighbors_1.width, edge_neighbors_1.height = 140.0, 100.0
    set_position_002_1.width, set_position_002_1.height = 140.0, 100.0
    merge_by_distance_1.width, merge_by_distance_1.height = 140.0, 100.0
    boolean_math_1.width, boolean_math_1.height = 140.0, 100.0
    switch_1.width, switch_1.height = 140.0, 100.0
    switch_010_1.width, switch_010_1.height = 140.0, 100.0
    resample_curve_006_1.width, resample_curve_006_1.height = 140.0, 100.0
    set_spline_type_002_1.width, set_spline_type_002_1.height = 140.0, 100.0
    set_spline_type_001_1.width, set_spline_type_001_1.height = 140.0, 100.0
    set_handle_type_001_1.width, set_handle_type_001_1.height = 140.0, 100.0
    resample_curve_005_1.width, resample_curve_005_1.height = 140.0, 100.0
    set_spline_resolution_001_1.width, set_spline_resolution_001_1.height = 140.0, 100.0
    subdivide_curve_001_1.width, subdivide_curve_001_1.height = 140.0, 100.0
    math_1.width, math_1.height = 140.0, 100.0
    switch_018_1.width, switch_018_1.height = 140.0, 100.0
    index_006_1.width, index_006_1.height = 140.0, 100.0
    switch_002_1.width, switch_002_1.height = 140.0, 100.0
    math_001_1.width, math_001_1.height = 140.0, 100.0
    domain_size_001_1.width, domain_size_001_1.height = 140.0, 100.0
    switch_001_1.width, switch_001_1.height = 140.0, 100.0
    resample_curve_004_1.width, resample_curve_004_1.height = 140.0, 100.0
    curve_line_001_1.width, curve_line_001_1.height = 140.0, 100.0
    sample_index_1.width, sample_index_1.height = 140.0, 100.0
    sample_index_001_1.width, sample_index_001_1.height = 140.0, 100.0

    #initialize loft_mesh links
    #math_029_1.Value -> compare_003_1.A
    loft_mesh.links.new(math_029_1.outputs[0], compare_003_1.inputs[2])
    #boolean_math_001_1.Boolean -> switch_017_1.Switch
    loft_mesh.links.new(boolean_math_001_1.outputs[0], switch_017_1.inputs[0])
    #resample_curve_003_1.Curve -> duplicate_elements_001_1.Geometry
    loft_mesh.links.new(resample_curve_003_1.outputs[0], duplicate_elements_001_1.inputs[0])
    #math_023_1.Value -> math_030_1.Value
    loft_mesh.links.new(math_023_1.outputs[0], math_030_1.inputs[0])
    #math_030_1.Value -> compare_003_1.B
    loft_mesh.links.new(math_030_1.outputs[0], compare_003_1.inputs[3])
    #curve_line_001_1.Curve -> resample_curve_003_1.Curve
    loft_mesh.links.new(curve_line_001_1.outputs[0], resample_curve_003_1.inputs[0])
    #switch_001_1.Output -> sample_index_1.Geometry
    loft_mesh.links.new(switch_001_1.outputs[0], sample_index_1.inputs[0])
    #math_031_1.Value -> math_033_1.Value
    loft_mesh.links.new(math_031_1.outputs[0], math_033_1.inputs[0])
    #position_002_1.Position -> sample_index_1.Value
    loft_mesh.links.new(position_002_1.outputs[0], sample_index_1.inputs[1])
    #math_030_1.Value -> math_033_1.Value
    loft_mesh.links.new(math_030_1.outputs[0], math_033_1.inputs[1])
    #duplicate_elements_001_1.Geometry -> set_position_003_1.Geometry
    loft_mesh.links.new(duplicate_elements_001_1.outputs[0], set_position_003_1.inputs[0])
    #math_032_1.Value -> switch_012_1.False
    loft_mesh.links.new(math_032_1.outputs[0], switch_012_1.inputs[1])
    #boolean_math_1.Boolean -> switch_1.Switch
    loft_mesh.links.new(boolean_math_1.outputs[0], switch_1.inputs[0])
    #sample_index_1.Value -> set_position_003_1.Position
    loft_mesh.links.new(sample_index_1.outputs[0], set_position_003_1.inputs[2])
    #math_033_1.Value -> switch_012_1.True
    loft_mesh.links.new(math_033_1.outputs[0], switch_012_1.inputs[2])
    #set_position_002_1.Geometry -> merge_by_distance_1.Geometry
    loft_mesh.links.new(set_position_002_1.outputs[0], merge_by_distance_1.inputs[0])
    #switch_001_1.Output -> domain_size_001_1.Geometry
    loft_mesh.links.new(switch_001_1.outputs[0], domain_size_001_1.inputs[0])
    #compare_003_1.Result -> switch_012_1.Switch
    loft_mesh.links.new(compare_003_1.outputs[0], switch_012_1.inputs[0])
    #edge_neighbors_1.Face Count -> compare_1.A
    loft_mesh.links.new(edge_neighbors_1.outputs[0], compare_1.inputs[2])
    #domain_size_001_1.Spline Count -> resample_curve_003_1.Count
    loft_mesh.links.new(domain_size_001_1.outputs[4], resample_curve_003_1.inputs[2])
    #compare_1.Result -> merge_by_distance_1.Selection
    loft_mesh.links.new(compare_1.outputs[0], merge_by_distance_1.inputs[1])
    #math_026_1.Value -> math_024_1.Value
    loft_mesh.links.new(math_026_1.outputs[0], math_024_1.inputs[0])
    #merge_by_distance_1.Geometry -> switch_1.True
    loft_mesh.links.new(merge_by_distance_1.outputs[0], switch_1.inputs[2])
    #math_025_1.Value -> sample_index_1.Index
    loft_mesh.links.new(math_025_1.outputs[0], sample_index_1.inputs[2])
    #switch_003_1.Output -> math_020_1.Value
    loft_mesh.links.new(switch_003_1.outputs[0], math_020_1.inputs[1])
    #set_position_002_1.Geometry -> switch_1.False
    loft_mesh.links.new(set_position_002_1.outputs[0], switch_1.inputs[1])
    #index_006_1.Index -> math_026_1.Value
    loft_mesh.links.new(index_006_1.outputs[0], math_026_1.inputs[0])
    #switch_002_1.Output -> switch_011_1.False
    loft_mesh.links.new(switch_002_1.outputs[0], switch_011_1.inputs[1])
    #math_024_1.Value -> math_025_1.Value
    loft_mesh.links.new(math_024_1.outputs[0], math_025_1.inputs[0])
    #switch_002_1.Output -> math_027_1.Value
    loft_mesh.links.new(switch_002_1.outputs[0], math_027_1.inputs[0])
    #set_spline_resolution_001_1.Geometry -> set_spline_type_002_1.Curve
    loft_mesh.links.new(set_spline_resolution_001_1.outputs[0], set_spline_type_002_1.inputs[0])
    #duplicate_elements_001_1.Duplicate Index -> math_025_1.Value
    loft_mesh.links.new(duplicate_elements_001_1.outputs[1], math_025_1.inputs[1])
    #math_027_1.Value -> switch_011_1.True
    loft_mesh.links.new(math_027_1.outputs[0], switch_011_1.inputs[2])
    #set_spline_type_002_1.Curve -> resample_curve_006_1.Curve
    loft_mesh.links.new(set_spline_type_002_1.outputs[0], resample_curve_006_1.inputs[0])
    #switch_002_1.Output -> math_024_1.Value
    loft_mesh.links.new(switch_002_1.outputs[0], math_024_1.inputs[1])
    #switch_011_1.Output -> grid_001_1.Vertices X
    loft_mesh.links.new(switch_011_1.outputs[0], grid_001_1.inputs[2])
    #resample_curve_006_1.Curve -> switch_010_1.True
    loft_mesh.links.new(resample_curve_006_1.outputs[0], switch_010_1.inputs[2])
    #switch_002_1.Output -> duplicate_elements_001_1.Amount
    loft_mesh.links.new(switch_002_1.outputs[0], duplicate_elements_001_1.inputs[2])
    #switch_002_1.Output -> math_034_1.Value
    loft_mesh.links.new(switch_002_1.outputs[0], math_034_1.inputs[0])
    #switch_010_1.Output -> switch_018_1.False
    loft_mesh.links.new(switch_010_1.outputs[0], switch_018_1.inputs[1])
    #domain_size_001_1.Spline Count -> math_026_1.Value
    loft_mesh.links.new(domain_size_001_1.outputs[4], math_026_1.inputs[1])
    #math_023_1.Value -> math_034_1.Value
    loft_mesh.links.new(math_023_1.outputs[0], math_034_1.inputs[1])
    #subdivide_curve_001_1.Curve -> switch_018_1.True
    loft_mesh.links.new(subdivide_curve_001_1.outputs[0], switch_018_1.inputs[2])
    #set_spline_type_001_1.Curve -> set_handle_type_001_1.Curve
    loft_mesh.links.new(set_spline_type_001_1.outputs[0], set_handle_type_001_1.inputs[0])
    #index_006_1.Index -> compare_004_1.A
    loft_mesh.links.new(index_006_1.outputs[0], compare_004_1.inputs[2])
    #set_spline_cyclic_002_1.Geometry -> subdivide_curve_001_1.Curve
    loft_mesh.links.new(set_spline_cyclic_002_1.outputs[0], subdivide_curve_001_1.inputs[0])
    #math_034_1.Value -> compare_004_1.B
    loft_mesh.links.new(math_034_1.outputs[0], compare_004_1.inputs[3])
    #math_1.Value -> switch_018_1.Switch
    loft_mesh.links.new(math_1.outputs[0], switch_018_1.inputs[0])
    #position_002_1.Position -> sample_index_001_1.Value
    loft_mesh.links.new(position_002_1.outputs[0], sample_index_001_1.inputs[1])
    #index_006_1.Index -> math_035_1.Value
    loft_mesh.links.new(index_006_1.outputs[0], math_035_1.inputs[0])
    #resample_curve_004_1.Curve -> switch_001_1.True
    loft_mesh.links.new(resample_curve_004_1.outputs[0], switch_001_1.inputs[2])
    #math_023_1.Value -> math_035_1.Value
    loft_mesh.links.new(math_023_1.outputs[0], math_035_1.inputs[1])
    #store_named_attribute_1.Geometry -> set_position_002_1.Geometry
    loft_mesh.links.new(store_named_attribute_1.outputs[0], set_position_002_1.inputs[0])
    #sample_index_001_1.Value -> set_position_002_1.Position
    loft_mesh.links.new(sample_index_001_1.outputs[0], set_position_002_1.inputs[2])
    #index_006_1.Index -> switch_016_1.False
    loft_mesh.links.new(index_006_1.outputs[0], switch_016_1.inputs[1])
    #domain_size_001_1.Spline Count -> math_020_1.Value
    loft_mesh.links.new(domain_size_001_1.outputs[4], math_020_1.inputs[0])
    #switch_012_1.Output -> switch_016_1.True
    loft_mesh.links.new(switch_012_1.outputs[0], switch_016_1.inputs[2])
    #math_001_1.Value -> switch_002_1.False
    loft_mesh.links.new(math_001_1.outputs[0], switch_002_1.inputs[1])
    #math_021_1.Value -> math_022_1.Value
    loft_mesh.links.new(math_021_1.outputs[0], math_022_1.inputs[0])
    #switch_016_1.Output -> switch_013_1.False
    loft_mesh.links.new(switch_016_1.outputs[0], switch_013_1.inputs[1])
    #domain_size_001_1.Point Count -> math_001_1.Value
    loft_mesh.links.new(domain_size_001_1.outputs[0], math_001_1.inputs[0])
    #math_020_1.Value -> math_022_1.Value
    loft_mesh.links.new(math_020_1.outputs[0], math_022_1.inputs[1])
    #compare_004_1.Result -> switch_013_1.Switch
    loft_mesh.links.new(compare_004_1.outputs[0], switch_013_1.inputs[0])
    #domain_size_001_1.Spline Count -> math_001_1.Value
    loft_mesh.links.new(domain_size_001_1.outputs[4], math_001_1.inputs[1])
    #math_022_1.Value -> math_023_1.Value
    loft_mesh.links.new(math_022_1.outputs[0], math_023_1.inputs[0])
    #math_035_1.Value -> switch_013_1.True
    loft_mesh.links.new(math_035_1.outputs[0], switch_013_1.inputs[2])
    #grid_001_1.Mesh -> store_named_attribute_1.Geometry
    loft_mesh.links.new(grid_001_1.outputs[0], store_named_attribute_1.inputs[0])
    #set_spline_cyclic_002_1.Geometry -> set_spline_resolution_001_1.Geometry
    loft_mesh.links.new(set_spline_cyclic_002_1.outputs[0], set_spline_resolution_001_1.inputs[0])
    #switch_016_1.Output -> switch_014_1.False
    loft_mesh.links.new(switch_016_1.outputs[0], switch_014_1.inputs[1])
    #grid_001_1.UV Map -> store_named_attribute_1.Value
    loft_mesh.links.new(grid_001_1.outputs[1], store_named_attribute_1.inputs[3])
    #set_spline_resolution_001_1.Geometry -> set_spline_type_001_1.Curve
    loft_mesh.links.new(set_spline_resolution_001_1.outputs[0], set_spline_type_001_1.inputs[0])
    #switch_013_1.Output -> switch_014_1.True
    loft_mesh.links.new(switch_013_1.outputs[0], switch_014_1.inputs[2])
    #math_023_1.Value -> grid_001_1.Vertices Y
    loft_mesh.links.new(math_023_1.outputs[0], grid_001_1.inputs[3])
    #set_handle_type_001_1.Curve -> resample_curve_005_1.Curve
    loft_mesh.links.new(set_handle_type_001_1.outputs[0], resample_curve_005_1.inputs[0])
    #index_006_1.Index -> compare_005_1.A
    loft_mesh.links.new(index_006_1.outputs[0], compare_005_1.inputs[2])
    #math_019_1.Value -> set_spline_resolution_001_1.Resolution
    loft_mesh.links.new(math_019_1.outputs[0], set_spline_resolution_001_1.inputs[2])
    #switch_014_1.Output -> switch_015_1.False
    loft_mesh.links.new(switch_014_1.outputs[0], switch_015_1.inputs[1])
    #resample_curve_005_1.Curve -> switch_010_1.False
    loft_mesh.links.new(resample_curve_005_1.outputs[0], switch_010_1.inputs[1])
    #compare_005_1.Result -> switch_015_1.Switch
    loft_mesh.links.new(compare_005_1.outputs[0], switch_015_1.inputs[0])
    #switch_018_1.Output -> sample_index_001_1.Geometry
    loft_mesh.links.new(switch_018_1.outputs[0], sample_index_001_1.inputs[0])
    #switch_011_1.Output -> math_037_1.Value
    loft_mesh.links.new(switch_011_1.outputs[0], math_037_1.inputs[0])
    #set_position_003_1.Geometry -> set_spline_cyclic_002_1.Geometry
    loft_mesh.links.new(set_position_003_1.outputs[0], set_spline_cyclic_002_1.inputs[0])
    #math_023_1.Value -> math_037_1.Value
    loft_mesh.links.new(math_023_1.outputs[0], math_037_1.inputs[1])
    #index_006_1.Index -> math_028_1.Value
    loft_mesh.links.new(index_006_1.outputs[0], math_028_1.inputs[0])
    #math_037_1.Value -> math_036_1.Value
    loft_mesh.links.new(math_037_1.outputs[0], math_036_1.inputs[0])
    #math_028_1.Value -> math_031_1.Value
    loft_mesh.links.new(math_028_1.outputs[0], math_031_1.inputs[0])
    #math_036_1.Value -> compare_005_1.B
    loft_mesh.links.new(math_036_1.outputs[0], compare_005_1.inputs[3])
    #math_023_1.Value -> math_028_1.Value
    loft_mesh.links.new(math_023_1.outputs[0], math_028_1.inputs[1])
    #index_006_1.Index -> math_032_1.Value
    loft_mesh.links.new(index_006_1.outputs[0], math_032_1.inputs[0])
    #math_031_1.Value -> math_032_1.Value
    loft_mesh.links.new(math_031_1.outputs[0], math_032_1.inputs[1])
    #switch_014_1.Output -> switch_017_1.False
    loft_mesh.links.new(switch_014_1.outputs[0], switch_017_1.inputs[1])
    #index_006_1.Index -> math_029_1.Value
    loft_mesh.links.new(index_006_1.outputs[0], math_029_1.inputs[0])
    #switch_015_1.Output -> switch_017_1.True
    loft_mesh.links.new(switch_015_1.outputs[0], switch_017_1.inputs[2])
    #math_023_1.Value -> math_029_1.Value
    loft_mesh.links.new(math_023_1.outputs[0], math_029_1.inputs[1])
    #switch_017_1.Output -> sample_index_001_1.Index
    loft_mesh.links.new(switch_017_1.outputs[0], sample_index_001_1.inputs[2])
    #group_input_2.Switch -> switch_003_1.Switch
    loft_mesh.links.new(group_input_2.outputs[2], switch_003_1.inputs[0])
    #group_input_2.Switch -> boolean_math_001_1.Boolean
    loft_mesh.links.new(group_input_2.outputs[2], boolean_math_001_1.inputs[1])
    #group_input_2.Switch -> switch_016_1.Switch
    loft_mesh.links.new(group_input_2.outputs[2], switch_016_1.inputs[0])
    #group_input_2.Switch -> set_spline_cyclic_002_1.Cyclic
    loft_mesh.links.new(group_input_2.outputs[2], set_spline_cyclic_002_1.inputs[2])
    #group_input_2.Switch -> boolean_math_1.Boolean
    loft_mesh.links.new(group_input_2.outputs[2], boolean_math_1.inputs[1])
    #group_input_2.Value -> math_021_1.Value
    loft_mesh.links.new(group_input_2.outputs[1], math_021_1.inputs[0])
    #group_input_2.Value -> math_019_1.Value
    loft_mesh.links.new(group_input_2.outputs[1], math_019_1.inputs[0])
    #group_input_2.Value -> subdivide_curve_001_1.Cuts
    loft_mesh.links.new(group_input_2.outputs[1], subdivide_curve_001_1.inputs[1])
    #group_input_2.Switch -> switch_011_1.Switch
    loft_mesh.links.new(group_input_2.outputs[0], switch_011_1.inputs[0])
    #group_input_2.Switch -> boolean_math_001_1.Boolean
    loft_mesh.links.new(group_input_2.outputs[0], boolean_math_001_1.inputs[0])
    #group_input_2.Switch -> switch_014_1.Switch
    loft_mesh.links.new(group_input_2.outputs[0], switch_014_1.inputs[0])
    #group_input_2.Switch -> boolean_math_1.Boolean
    loft_mesh.links.new(group_input_2.outputs[0], boolean_math_1.inputs[0])
    #group_input_2.Splines -> switch_001_1.False
    loft_mesh.links.new(group_input_2.outputs[6], switch_001_1.inputs[1])
    #group_input_2.Splines -> resample_curve_004_1.Curve
    loft_mesh.links.new(group_input_2.outputs[6], resample_curve_004_1.inputs[0])
    #group_input_2.Switch -> switch_010_1.Switch
    loft_mesh.links.new(group_input_2.outputs[3], switch_010_1.inputs[0])
    #group_input_2.Switch -> math_1.Value
    loft_mesh.links.new(group_input_2.outputs[3], math_1.inputs[0])
    #group_input_2.Switch -> switch_002_1.Switch
    loft_mesh.links.new(group_input_2.outputs[4], switch_002_1.inputs[0])
    #group_input_2.Switch -> switch_001_1.Switch
    loft_mesh.links.new(group_input_2.outputs[4], switch_001_1.inputs[0])
    #group_input_2.True -> switch_002_1.True
    loft_mesh.links.new(group_input_2.outputs[5], switch_002_1.inputs[2])
    #group_input_2.True -> resample_curve_004_1.Count
    loft_mesh.links.new(group_input_2.outputs[5], resample_curve_004_1.inputs[2])
    #switch_1.Output -> group_output_2.Geometry
    loft_mesh.links.new(switch_1.outputs[0], group_output_2.inputs[0])
    return loft_mesh

loft_mesh = loft_mesh_node_group()

#initialize index_rotation node group
def index_rotation_node_group():
    index_rotation = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "index rotation")

    index_rotation.color_tag = 'NONE'
    index_rotation.description = ""
    index_rotation.default_group_node_width = 140
    

    index_rotation.is_modifier = True

    #index_rotation interface
    #Socket Geometry
    geometry_socket_3 = index_rotation.interface.new_socket(name = "Geometry", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket_3.attribute_domain = 'POINT'

    #Socket Geometry
    geometry_socket_4 = index_rotation.interface.new_socket(name = "Geometry", in_out='INPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket_4.attribute_domain = 'POINT'

    #Socket Value
    value_socket_2 = index_rotation.interface.new_socket(name = "Value", in_out='INPUT', socket_type = 'NodeSocketInt')
    value_socket_2.default_value = 0
    value_socket_2.min_value = -2147483648
    value_socket_2.max_value = 2147483647
    value_socket_2.subtype = 'NONE'
    value_socket_2.attribute_domain = 'POINT'


    #initialize index_rotation nodes
    #node Group Input
    group_input_3 = index_rotation.nodes.new("NodeGroupInput")
    group_input_3.name = "Group Input"

    #node Group Output
    group_output_3 = index_rotation.nodes.new("NodeGroupOutput")
    group_output_3.name = "Group Output"
    group_output_3.is_active_output = True

    #node Sort Elements
    sort_elements = index_rotation.nodes.new("GeometryNodeSortElements")
    sort_elements.name = "Sort Elements"
    sort_elements.domain = 'CURVE'
    #Selection
    sort_elements.inputs[1].default_value = True
    #Group ID
    sort_elements.inputs[2].default_value = 0
    #Sort Weight
    sort_elements.inputs[3].default_value = 0.0

    #node Curve to Points
    curve_to_points_1 = index_rotation.nodes.new("GeometryNodeCurveToPoints")
    curve_to_points_1.name = "Curve to Points"
    curve_to_points_1.mode = 'EVALUATED'

    #node Math
    math_2 = index_rotation.nodes.new("ShaderNodeMath")
    math_2.name = "Math"
    math_2.operation = 'WRAP'
    math_2.use_clamp = False
    #Value_002
    math_2.inputs[2].default_value = 1.0

    #node Points to Curves
    points_to_curves = index_rotation.nodes.new("GeometryNodePointsToCurves")
    points_to_curves.name = "Points to Curves"
    #Curve Group ID
    points_to_curves.inputs[1].default_value = 0

    #node Index.002
    index_002 = index_rotation.nodes.new("GeometryNodeInputIndex")
    index_002.name = "Index.002"

    #node Domain Size
    domain_size_1 = index_rotation.nodes.new("GeometryNodeAttributeDomainSize")
    domain_size_1.name = "Domain Size"
    domain_size_1.component = 'POINTCLOUD'

    #node Math.001
    math_001_2 = index_rotation.nodes.new("ShaderNodeMath")
    math_001_2.name = "Math.001"
    math_001_2.operation = 'ADD'
    math_001_2.use_clamp = False





    #Set locations
    group_input_3.location = (-1041.51025390625, 127.2029037475586)
    group_output_3.location = (427.47821044921875, 25.14803123474121)
    sort_elements.location = (200.31396484375, 237.19253540039062)
    curve_to_points_1.location = (-808.9818115234375, 198.03616333007812)
    math_2.location = (-425.9422302246094, -59.20063018798828)
    points_to_curves.location = (-156.00001525878906, 149.73861694335938)
    index_002.location = (-808.9669799804688, -192.98953247070312)
    domain_size_1.location = (-641.4945678710938, -31.762344360351562)
    math_001_2.location = (-643.3131713867188, -227.27114868164062)

    #Set dimensions
    group_input_3.width, group_input_3.height = 140.0, 100.0
    group_output_3.width, group_output_3.height = 140.0, 100.0
    sort_elements.width, sort_elements.height = 140.0, 100.0
    curve_to_points_1.width, curve_to_points_1.height = 140.0, 100.0
    math_2.width, math_2.height = 140.0, 100.0
    points_to_curves.width, points_to_curves.height = 140.0, 100.0
    index_002.width, index_002.height = 140.0, 100.0
    domain_size_1.width, domain_size_1.height = 140.0, 100.0
    math_001_2.width, math_001_2.height = 140.0, 100.0

    #initialize index_rotation links
    #curve_to_points_1.Points -> points_to_curves.Points
    index_rotation.links.new(curve_to_points_1.outputs[0], points_to_curves.inputs[0])
    #math_001_2.Value -> math_2.Value
    index_rotation.links.new(math_001_2.outputs[0], math_2.inputs[0])
    #index_002.Index -> math_001_2.Value
    index_rotation.links.new(index_002.outputs[0], math_001_2.inputs[0])
    #points_to_curves.Curves -> sort_elements.Geometry
    index_rotation.links.new(points_to_curves.outputs[0], sort_elements.inputs[0])
    #domain_size_1.Point Count -> math_2.Value
    index_rotation.links.new(domain_size_1.outputs[0], math_2.inputs[1])
    #math_2.Value -> points_to_curves.Weight
    index_rotation.links.new(math_2.outputs[0], points_to_curves.inputs[2])
    #curve_to_points_1.Points -> domain_size_1.Geometry
    index_rotation.links.new(curve_to_points_1.outputs[0], domain_size_1.inputs[0])
    #group_input_3.Geometry -> curve_to_points_1.Curve
    index_rotation.links.new(group_input_3.outputs[0], curve_to_points_1.inputs[0])
    #group_input_3.Value -> math_001_2.Value
    index_rotation.links.new(group_input_3.outputs[1], math_001_2.inputs[1])
    #sort_elements.Geometry -> group_output_3.Geometry
    index_rotation.links.new(sort_elements.outputs[0], group_output_3.inputs[0])
    return index_rotation

index_rotation = index_rotation_node_group()

#initialize loft_path node group
def loft_path_node_group():
    if "Loft-path" in bpy.data.node_groups:
        return bpy.data.node_groups["Loft-path"]
    
    loft_path = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "Loft-path")

    loft_path.color_tag = 'NONE'
    loft_path.description = ""
    loft_path.default_group_node_width = 140
    

    loft_path.is_modifier = True

    #loft_path interface
    #Socket Mesh
    mesh_socket = loft_path.interface.new_socket(name = "Mesh", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
    mesh_socket.attribute_domain = 'POINT'

    #Socket Bezier/Catmull/Poly
    bezier_catmull_poly_socket = loft_path.interface.new_socket(name = "Bezier/Catmull/Poly", in_out='INPUT', socket_type = 'NodeSocketInt')
    bezier_catmull_poly_socket.default_value = 0
    bezier_catmull_poly_socket.min_value = 0
    bezier_catmull_poly_socket.max_value = 2
    bezier_catmull_poly_socket.subtype = 'NONE'
    bezier_catmull_poly_socket.attribute_domain = 'POINT'

    #Socket Resample Count
    resample_count_socket = loft_path.interface.new_socket(name = "Resample Count", in_out='INPUT', socket_type = 'NodeSocketInt')
    resample_count_socket.default_value = 10
    resample_count_socket.min_value = 2
    resample_count_socket.max_value = 2147483647
    resample_count_socket.subtype = 'NONE'
    resample_count_socket.attribute_domain = 'POINT'

    #Socket Subdivide
    subdivide_socket = loft_path.interface.new_socket(name = "Subdivide", in_out='INPUT', socket_type = 'NodeSocketInt')
    subdivide_socket.default_value = 2
    subdivide_socket.min_value = 0
    subdivide_socket.max_value = 2147483647
    subdivide_socket.subtype = 'NONE'
    subdivide_socket.attribute_domain = 'POINT'

    #Socket Resample Splines
    resample_splines_socket = loft_path.interface.new_socket(name = "Resample Splines", in_out='INPUT', socket_type = 'NodeSocketBool')
    resample_splines_socket.default_value = True
    resample_splines_socket.attribute_domain = 'POINT'

    #Socket Cyclic Splines
    cyclic_splines_socket = loft_path.interface.new_socket(name = "Cyclic Splines", in_out='INPUT', socket_type = 'NodeSocketBool')
    cyclic_splines_socket.default_value = False
    cyclic_splines_socket.attribute_domain = 'POINT'

    #Socket Cyclic Loft
    cyclic_loft_socket = loft_path.interface.new_socket(name = "Cyclic Loft", in_out='INPUT', socket_type = 'NodeSocketBool')
    cyclic_loft_socket.default_value = False
    cyclic_loft_socket.attribute_domain = 'POINT'

    #Socket curve
    curve_socket_1 = loft_path.interface.new_socket(name = "curve", in_out='INPUT', socket_type = 'NodeSocketObject')
    curve_socket_1.attribute_domain = 'POINT'

    #Socket Origin rotation
    origin_rotation_socket = loft_path.interface.new_socket(name = "Origin rotation", in_out='INPUT', socket_type = 'NodeSocketInt')
    origin_rotation_socket.default_value = 85
    origin_rotation_socket.min_value = -2147483648
    origin_rotation_socket.max_value = 2147483647
    origin_rotation_socket.subtype = 'NONE'
    origin_rotation_socket.attribute_domain = 'POINT'

    #Socket Insertion rotation
    insertion_rotation_socket = loft_path.interface.new_socket(name = "Insertion rotation", in_out='INPUT', socket_type = 'NodeSocketInt')
    insertion_rotation_socket.default_value = 85
    insertion_rotation_socket.min_value = -2147483648
    insertion_rotation_socket.max_value = 2147483647
    insertion_rotation_socket.subtype = 'NONE'
    insertion_rotation_socket.attribute_domain = 'POINT'

    #Socket Origin
    origin_socket = loft_path.interface.new_socket(name = "Origin", in_out='INPUT', socket_type = 'NodeSocketObject')
    origin_socket.attribute_domain = 'POINT'

    #Socket Insertion
    insertion_socket = loft_path.interface.new_socket(name = "Insertion", in_out='INPUT', socket_type = 'NodeSocketObject')
    insertion_socket.attribute_domain = 'POINT'

    #Socket Swap origin-insertion
    swap_origin_insertion_socket = loft_path.interface.new_socket(name = "Swap origin-insertion", in_out='INPUT', socket_type = 'NodeSocketBool')
    swap_origin_insertion_socket.default_value = False
    swap_origin_insertion_socket.attribute_domain = 'POINT'

    #Socket Switch direction origin
    switch_direction_origin_socket = loft_path.interface.new_socket(name = "Switch direction origin", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_direction_origin_socket.default_value = False
    switch_direction_origin_socket.attribute_domain = 'POINT'

    #Socket Switch direction insertion
    switch_direction_insertion_socket = loft_path.interface.new_socket(name = "Switch direction insertion", in_out='INPUT', socket_type = 'NodeSocketBool')
    switch_direction_insertion_socket.default_value = False
    switch_direction_insertion_socket.attribute_domain = 'POINT'


    #initialize loft_path nodes
    #node Group Output
    group_output_4 = loft_path.nodes.new("NodeGroupOutput")
    group_output_4.name = "Group Output"
    group_output_4.is_active_output = True

    #node Group Input
    group_input_4 = loft_path.nodes.new("NodeGroupInput")
    group_input_4.name = "Group Input"

    #node Group
    group = loft_path.nodes.new("GeometryNodeGroup")
    group.name = "Group"
    group.node_tree = loft_splines

    #node Mesh to Curve
    mesh_to_curve = loft_path.nodes.new("GeometryNodeMeshToCurve")
    mesh_to_curve.name = "Mesh to Curve"
    #Selection
    mesh_to_curve.inputs[1].default_value = True

    #node Group.001
    group_001 = loft_path.nodes.new("GeometryNodeGroup")
    group_001.name = "Group.001"
    group_001.node_tree = instances_on_points

    #node Loft-mesh
    loft_mesh_1 = loft_path.nodes.new("GeometryNodeGroup")
    loft_mesh_1.name = "Loft-mesh"
    loft_mesh_1.node_tree = loft_mesh
    #Socket_1
    loft_mesh_1.inputs[0].default_value = True
    #Socket_2
    loft_mesh_1.inputs[1].default_value = 0.0
    #Socket_3
    loft_mesh_1.inputs[2].default_value = False
    #Socket_4
    loft_mesh_1.inputs[3].default_value = False
    #Socket_5
    loft_mesh_1.inputs[4].default_value = False
    #Socket_6
    loft_mesh_1.inputs[5].default_value = 0

    #node Viewer
    viewer_1 = loft_path.nodes.new("GeometryNodeViewer")
    viewer_1.name = "Viewer"
    viewer_1.data_type = 'FLOAT'
    viewer_1.domain = 'AUTO'
    #Value
    viewer_1.inputs[1].default_value = 0.0

    #node Realize Instances
    realize_instances = loft_path.nodes.new("GeometryNodeRealizeInstances")
    realize_instances.name = "Realize Instances"
    #Selection
    realize_instances.inputs[1].default_value = True
    #Realize All
    realize_instances.inputs[2].default_value = True
    #Depth
    realize_instances.inputs[3].default_value = 0

    #node Object Info
    object_info = loft_path.nodes.new("GeometryNodeObjectInfo")
    object_info.name = "Object Info"
    object_info.transform_space = 'RELATIVE'
    #As Instance
    object_info.inputs[1].default_value = False

    #node Object Info.001
    object_info_001_1 = loft_path.nodes.new("GeometryNodeObjectInfo")
    object_info_001_1.name = "Object Info.001"
    object_info_001_1.transform_space = 'RELATIVE'
    #As Instance
    object_info_001_1.inputs[1].default_value = False

    #node Join Geometry
    join_geometry = loft_path.nodes.new("GeometryNodeJoinGeometry")
    join_geometry.name = "Join Geometry"

    #node Resample Curve
    resample_curve = loft_path.nodes.new("GeometryNodeResampleCurve")
    resample_curve.name = "Resample Curve"
    resample_curve.mode = 'COUNT'
    #Selection
    resample_curve.inputs[1].default_value = True

    #node Resample Curve.001
    resample_curve_001 = loft_path.nodes.new("GeometryNodeResampleCurve")
    resample_curve_001.name = "Resample Curve.001"
    resample_curve_001.mode = 'COUNT'
    #Selection
    resample_curve_001.inputs[1].default_value = True

    #node Group.002
    group_002 = loft_path.nodes.new("GeometryNodeGroup")
    group_002.name = "Group.002"
    group_002.node_tree = index_rotation

    #node Group.003
    group_003 = loft_path.nodes.new("GeometryNodeGroup")
    group_003.name = "Group.003"
    group_003.node_tree = index_rotation

    #node Math
    math_3 = loft_path.nodes.new("ShaderNodeMath")
    math_3.name = "Math"
    math_3.operation = 'MAXIMUM'
    math_3.use_clamp = False

    #node Domain Size
    domain_size_2 = loft_path.nodes.new("GeometryNodeAttributeDomainSize")
    domain_size_2.name = "Domain Size"
    domain_size_2.component = 'CURVE'

    #node Domain Size.001
    domain_size_001_2 = loft_path.nodes.new("GeometryNodeAttributeDomainSize")
    domain_size_001_2.name = "Domain Size.001"
    domain_size_001_2.component = 'CURVE'

    #node Switch
    switch_2 = loft_path.nodes.new("GeometryNodeSwitch")
    switch_2.name = "Switch"
    switch_2.input_type = 'OBJECT'

    #node Switch.001
    switch_001_2 = loft_path.nodes.new("GeometryNodeSwitch")
    switch_001_2.name = "Switch.001"
    switch_001_2.input_type = 'OBJECT'

    #node Switch.002
    switch_002_2 = loft_path.nodes.new("GeometryNodeSwitch")
    switch_002_2.name = "Switch.002"
    switch_002_2.input_type = 'GEOMETRY'

    #node Reverse Curve
    reverse_curve = loft_path.nodes.new("GeometryNodeReverseCurve")
    reverse_curve.name = "Reverse Curve"
    #Selection
    reverse_curve.inputs[1].default_value = True

    #node Switch.003
    switch_003_2 = loft_path.nodes.new("GeometryNodeSwitch")
    switch_003_2.name = "Switch.003"
    switch_003_2.input_type = 'GEOMETRY'

    #node Reverse Curve.001
    reverse_curve_001 = loft_path.nodes.new("GeometryNodeReverseCurve")
    reverse_curve_001.name = "Reverse Curve.001"
    #Selection
    reverse_curve_001.inputs[1].default_value = True





    #Set locations
    group_output_4.location = (1068.824462890625, 382.23272705078125)
    group_input_4.location = (-3182.948486328125, 173.57347106933594)
    group.location = (-306.916259765625, 168.11273193359375)
    mesh_to_curve.location = (-124.6654052734375, 154.07159423828125)
    group_001.location = (84.0908203125, 92.68875122070312)
    loft_mesh_1.location = (692.9475708007812, 57.439483642578125)
    viewer_1.location = (942.6893310546875, 4.4673614501953125)
    realize_instances.location = (493.69122314453125, 16.834152221679688)
    object_info.location = (-2219.97119140625, 516.0083618164062)
    object_info_001_1.location = (-2227.03466796875, 301.5230712890625)
    join_geometry.location = (-584.8364868164062, 261.8656005859375)
    resample_curve.location = (-1430.9541015625, 500.9258117675781)
    resample_curve_001.location = (-1362.746337890625, 233.80575561523438)
    group_002.location = (-1956.537109375, 472.2096252441406)
    group_003.location = (-1997.790283203125, 208.74264526367188)
    math_3.location = (-1604.627197265625, 335.0115051269531)
    domain_size_2.location = (-1785.927490234375, 515.31201171875)
    domain_size_001_2.location = (-1750.469970703125, 218.4763641357422)
    switch_2.location = (-2615.124267578125, 559.909912109375)
    switch_001_2.location = (-2610.15966796875, 406.21893310546875)
    switch_002_2.location = (-917.6954345703125, 488.1066589355469)
    reverse_curve.location = (-1140.878662109375, 567.7201538085938)
    switch_003_2.location = (-907.6489868164062, 220.36605834960938)
    reverse_curve_001.location = (-1130.8321533203125, 299.97955322265625)

    #Set dimensions
    group_output_4.width, group_output_4.height = 140.0, 100.0
    group_input_4.width, group_input_4.height = 140.0, 100.0
    group.width, group.height = 140.0, 100.0
    mesh_to_curve.width, mesh_to_curve.height = 140.0, 100.0
    group_001.width, group_001.height = 323.52197265625, 100.0
    loft_mesh_1.width, loft_mesh_1.height = 140.0, 100.0
    viewer_1.width, viewer_1.height = 140.0, 100.0
    realize_instances.width, realize_instances.height = 140.0, 100.0
    object_info.width, object_info.height = 140.0, 100.0
    object_info_001_1.width, object_info_001_1.height = 140.0, 100.0
    join_geometry.width, join_geometry.height = 140.0, 100.0
    resample_curve.width, resample_curve.height = 140.0, 100.0
    resample_curve_001.width, resample_curve_001.height = 140.0, 100.0
    group_002.width, group_002.height = 140.0, 100.0
    group_003.width, group_003.height = 140.0, 100.0
    math_3.width, math_3.height = 140.0, 100.0
    domain_size_2.width, domain_size_2.height = 140.0, 100.0
    domain_size_001_2.width, domain_size_001_2.height = 140.0, 100.0
    switch_2.width, switch_2.height = 140.0, 100.0
    switch_001_2.width, switch_001_2.height = 140.0, 100.0
    switch_002_2.width, switch_002_2.height = 140.0, 100.0
    reverse_curve.width, reverse_curve.height = 140.0, 100.0
    switch_003_2.width, switch_003_2.height = 140.0, 100.0
    reverse_curve_001.width, reverse_curve_001.height = 140.0, 100.0

    #initialize loft_path links
    #group_input_4.Cyclic Loft -> group.Switch
    loft_path.links.new(group_input_4.outputs[5], group.inputs[2])
    #group_input_4.Subdivide -> group.Value
    loft_path.links.new(group_input_4.outputs[2], group.inputs[1])
    #group_input_4.Cyclic Splines -> group.Switch
    loft_path.links.new(group_input_4.outputs[4], group.inputs[0])
    #group_input_4.Bezier/Catmull/Poly -> group.Switch
    loft_path.links.new(group_input_4.outputs[0], group.inputs[3])
    #group_input_4.Resample Splines -> group.Switch
    loft_path.links.new(group_input_4.outputs[3], group.inputs[4])
    #group_input_4.Resample Count -> group.True
    loft_path.links.new(group_input_4.outputs[1], group.inputs[5])
    #group.Geometry -> mesh_to_curve.Mesh
    loft_path.links.new(group.outputs[0], mesh_to_curve.inputs[0])
    #group_input_4.curve -> group_001.Curve
    loft_path.links.new(group_input_4.outputs[6], group_001.inputs[0])
    #mesh_to_curve.Curve -> group_001.Instances
    loft_path.links.new(mesh_to_curve.outputs[0], group_001.inputs[1])
    #realize_instances.Geometry -> loft_mesh_1.Splines
    loft_path.links.new(realize_instances.outputs[0], loft_mesh_1.inputs[6])
    #group_001.Geometry -> realize_instances.Geometry
    loft_path.links.new(group_001.outputs[0], realize_instances.inputs[0])
    #loft_mesh_1.Geometry -> viewer_1.Geometry
    loft_path.links.new(loft_mesh_1.outputs[0], viewer_1.inputs[0])
    #loft_mesh_1.Geometry -> group_output_4.Mesh
    loft_path.links.new(loft_mesh_1.outputs[0], group_output_4.inputs[0])
    #join_geometry.Geometry -> group.False
    loft_path.links.new(join_geometry.outputs[0], group.inputs[6])
    #group_002.Geometry -> resample_curve.Curve
    loft_path.links.new(group_002.outputs[0], resample_curve.inputs[0])
    #group_003.Geometry -> resample_curve_001.Curve
    loft_path.links.new(group_003.outputs[0], resample_curve_001.inputs[0])
    #math_3.Value -> resample_curve.Count
    loft_path.links.new(math_3.outputs[0], resample_curve.inputs[2])
    #object_info.Geometry -> group_002.Geometry
    loft_path.links.new(object_info.outputs[4], group_002.inputs[0])
    #group_input_4.Origin rotation -> group_002.Value
    loft_path.links.new(group_input_4.outputs[7], group_002.inputs[1])
    #object_info_001_1.Geometry -> group_003.Geometry
    loft_path.links.new(object_info_001_1.outputs[4], group_003.inputs[0])
    #group_input_4.Insertion rotation -> group_003.Value
    loft_path.links.new(group_input_4.outputs[8], group_003.inputs[1])
    #switch_002_2.Output -> join_geometry.Geometry
    loft_path.links.new(switch_002_2.outputs[0], join_geometry.inputs[0])
    #group_002.Geometry -> domain_size_2.Geometry
    loft_path.links.new(group_002.outputs[0], domain_size_2.inputs[0])
    #math_3.Value -> resample_curve_001.Count
    loft_path.links.new(math_3.outputs[0], resample_curve_001.inputs[2])
    #group_003.Geometry -> domain_size_001_2.Geometry
    loft_path.links.new(group_003.outputs[0], domain_size_001_2.inputs[0])
    #domain_size_2.Point Count -> math_3.Value
    loft_path.links.new(domain_size_2.outputs[0], math_3.inputs[0])
    #domain_size_001_2.Point Count -> math_3.Value
    loft_path.links.new(domain_size_001_2.outputs[0], math_3.inputs[1])
    #group_input_4.Swap origin-insertion -> switch_2.Switch
    loft_path.links.new(group_input_4.outputs[11], switch_2.inputs[0])
    #group_input_4.Swap origin-insertion -> switch_001_2.Switch
    loft_path.links.new(group_input_4.outputs[11], switch_001_2.inputs[0])
    #group_input_4.Origin -> switch_2.True
    loft_path.links.new(group_input_4.outputs[9], switch_2.inputs[2])
    #group_input_4.Insertion -> switch_2.False
    loft_path.links.new(group_input_4.outputs[10], switch_2.inputs[1])
    #group_input_4.Origin -> switch_001_2.False
    loft_path.links.new(group_input_4.outputs[9], switch_001_2.inputs[1])
    #group_input_4.Insertion -> switch_001_2.True
    loft_path.links.new(group_input_4.outputs[10], switch_001_2.inputs[2])
    #switch_001_2.Output -> object_info_001_1.Object
    loft_path.links.new(switch_001_2.outputs[0], object_info_001_1.inputs[0])
    #switch_2.Output -> object_info.Object
    loft_path.links.new(switch_2.outputs[0], object_info.inputs[0])
    #resample_curve.Curve -> switch_002_2.True
    loft_path.links.new(resample_curve.outputs[0], switch_002_2.inputs[2])
    #resample_curve.Curve -> reverse_curve.Curve
    loft_path.links.new(resample_curve.outputs[0], reverse_curve.inputs[0])
    #reverse_curve.Curve -> switch_002_2.False
    loft_path.links.new(reverse_curve.outputs[0], switch_002_2.inputs[1])
    #group_input_4.Switch direction origin -> switch_002_2.Switch
    loft_path.links.new(group_input_4.outputs[12], switch_002_2.inputs[0])
    #reverse_curve_001.Curve -> switch_003_2.False
    loft_path.links.new(reverse_curve_001.outputs[0], switch_003_2.inputs[1])
    #resample_curve_001.Curve -> reverse_curve_001.Curve
    loft_path.links.new(resample_curve_001.outputs[0], reverse_curve_001.inputs[0])
    #resample_curve_001.Curve -> switch_003_2.True
    loft_path.links.new(resample_curve_001.outputs[0], switch_003_2.inputs[2])
    #group_input_4.Switch direction insertion -> switch_003_2.Switch
    loft_path.links.new(group_input_4.outputs[13], switch_003_2.inputs[0])
    #switch_003_2.Output -> join_geometry.Geometry
    loft_path.links.new(switch_003_2.outputs[0], join_geometry.inputs[0])
    return loft_path

loft_path = loft_path_node_group()

