#!/usr/bin/env python3
"""
Test script para curvas pronunciadas con el nuevo sistema de Parallel Transport mejorado

Este script crea curvas con ángulos extremos (>180°) para probar que el sistema
de rotation minimizing frame previene la inversión de caras.
"""

import bpy
import bmesh
from mathutils import Vector
import math

def create_extreme_curve_test():
    """Crear una curva de prueba con ángulos extremos y cambios de dirección bruscos"""
    
    # Limpiar objetos existentes
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Crear curva Bezier con cambios extremos
    bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0))
    curve_obj = bpy.context.active_object
    curve_obj.name = "ExtremeCurve_Test"
    
    # Configurar la curva
    curve_data = curve_obj.data
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 16
    
    # Obtener el spline y configurar puntos extremos
    spline = curve_data.splines[0]
    
    # Agregar más puntos para crear una curva muy compleja
    spline.bezier_points.add(4)  # Total: 5 puntos
    
    # Configurar puntos con ángulos muy pronunciados y inversiones de dirección
    points_data = [
        # Punto 0 - Inicio
        {
            'co': Vector((0, 0, 0)),
            'handle_left': Vector((-0.5, 0, 0)),
            'handle_right': Vector((0.5, 0, 0)),
            'radius': 0.3
        },
        # Punto 1 - Giro brusco 90°
        {
            'co': Vector((2, 1, 0)),
            'handle_left': Vector((1.5, 0, 0)),
            'handle_right': Vector((2.5, 2, 0)),
            'radius': 0.8
        },
        # Punto 2 - Inversión completa >180°
        {
            'co': Vector((1, 4, 1)),
            'handle_left': Vector((3, 3, 1)),
            'handle_right': Vector((-1, 5, 1)),
            'radius': 1.2
        },
        # Punto 3 - Otro giro pronunciado
        {
            'co': Vector((-2, 3, 2)),
            'handle_left': Vector((0, 4, 2)),
            'handle_right': Vector((-4, 2, 2)),
            'radius': 0.9
        },
        # Punto 4 - Final con curva cerrada
        {
            'co': Vector((-1, 0, 3)),
            'handle_left': Vector((-3, 1, 3)),
            'handle_right': Vector((0, 0, 3)),
            'radius': 0.5
        }
    ]
    
    # Aplicar los datos de puntos
    for i, point_data in enumerate(points_data):
        point = spline.bezier_points[i]
        point.co = point_data['co']
        point.handle_left = point_data['handle_left']
        point.handle_right = point_data['handle_right']
        point.radius = point_data['radius']
        point.handle_left_type = 'FREE'
        point.handle_right_type = 'FREE'
    
    return curve_obj

def create_spiral_curve_test():
    """Crear una curva en espiral para probar rotaciones acumulativas"""
    
    bpy.ops.curve.primitive_bezier_curve_add(location=(5, 0, 0))
    curve_obj = bpy.context.active_object
    curve_obj.name = "SpiralCurve_Test"
    
    curve_data = curve_obj.data
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 20
    
    spline = curve_data.splines[0]
    spline.bezier_points.add(6)  # 7 puntos total para espiral completa
    
    # Crear una espiral que rota más de 360°
    for i in range(7):
        angle = i * math.pi / 2  # 90° por segmento = 540° total
        radius = 2.0 + i * 0.3
        height = i * 0.5
        
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = height
        
        # Handles para suavizar la espiral
        handle_angle = angle + math.pi / 4
        handle_radius = 0.8
        
        point = spline.bezier_points[i]
        point.co = Vector((x, y, z))
        point.handle_left = Vector((
            x - handle_radius * math.cos(handle_angle),
            y - handle_radius * math.sin(handle_angle),
            z
        ))
        point.handle_right = Vector((
            x + handle_radius * math.cos(handle_angle),
            y + handle_radius * math.sin(handle_angle),
            z
        ))
        point.radius = 0.6 + i * 0.1
        point.handle_left_type = 'FREE'
        point.handle_right_type = 'FREE'
    
    return curve_obj

def create_s_curve_extreme():
    """Crear una curva S extrema con cambios de >180°"""
    
    bpy.ops.curve.primitive_bezier_curve_add(location=(10, 0, 0))
    curve_obj = bpy.context.active_object
    curve_obj.name = "ExtremeSCurve_Test"
    
    curve_data = curve_obj.data
    curve_data.dimensions = '3D'
    
    spline = curve_data.splines[0]
    spline.bezier_points.add(2)  # 3 puntos para S extrema
    
    # S-curve con inversiones muy pronunciadas
    s_points = [
        {
            'co': Vector((0, 0, 0)),
            'handle_left': Vector((-1, 0, 0)),
            'handle_right': Vector((1, 2, 0)),
            'radius': 0.8
        },
        {
            'co': Vector((0, 4, 0)),
            'handle_left': Vector((-2, 2, 0)),
            'handle_right': Vector((2, 6, 0)),
            'radius': 1.5
        },
        {
            'co': Vector((0, 8, 0)),
            'handle_left': Vector((-1, 6, 0)),
            'handle_right': Vector((1, 8, 0)),
            'radius': 0.6
        }
    ]
    
    for i, point_data in enumerate(s_points):
        point = spline.bezier_points[i]
        point.co = point_data['co']
        point.handle_left = point_data['handle_left']
        point.handle_right = point_data['handle_right']
        point.radius = point_data['radius']
        point.handle_left_type = 'FREE'
        point.handle_right_type = 'FREE'
    
    return curve_obj

def test_extreme_curves():
    """Ejecutar todas las pruebas de curvas extremas"""
    
    print("=== Probando Sistema de Parallel Transport Mejorado ===")
    print("Creando curvas con ángulos extremos (>180°)...")
    
    # Crear las curvas de prueba
    extreme_curve = create_extreme_curve_test()
    spiral_curve = create_spiral_curve_test()
    s_curve = create_s_curve_extreme()
    
    # Crear contornos de prueba simples
    bpy.ops.mesh.primitive_circle_add(vertices=8, radius=0.4, location=(0, 0, -1))
    origin_test = bpy.context.active_object
    origin_test.name = "Origin_Test"
    
    bpy.ops.mesh.primitive_circle_add(vertices=8, radius=0.3, location=(0, 8, 4))
    insertion_test = bpy.context.active_object
    insertion_test.name = "Insertion_Test"
    
    print(f"✓ Curva extrema creada: {extreme_curve.name}")
    print(f"✓ Curva espiral creada: {spiral_curve.name}")
    print(f"✓ Curva S extrema creada: {s_curve.name}")
    print(f"✓ Contornos de prueba: {origin_test.name}, {insertion_test.name}")
    
    # Probar detección de inversiones globales
    try:
        from AddonFolder.spline_lofting_utilities import detect_global_inversions
        
        for curve in [extreme_curve, spiral_curve, s_curve]:
            needs_special = detect_global_inversions(curve, num_samples=30)
            print(f"Curva {curve.name}: Necesita manejo especial = {needs_special}")
            
    except ImportError:
        print("⚠ No se pudo importar detect_global_inversions - verifica que el addon esté instalado")
    
    print("\n=== Instrucciones de Prueba ===")
    print("1. Selecciona una de las curvas creadas")
    print("2. Usa el addon MyoGenerator para crear músculos con estas curvas")
    print("3. Observa que NO debe haber inversión de caras en los ángulos pronunciados")
    print("4. El nuevo sistema debería manejar ángulos >180° sin problemas")
    
    print("\n=== Características de las Curvas de Prueba ===")
    print("• ExtremeCurve_Test: Múltiples giros >90°, inversión >180°")
    print("• SpiralCurve_Test: Rotación acumulativa >540°")
    print("• ExtremeSCurve_Test: S-curve con cambios direccionales extremos")
    
    return True

if __name__ == "__main__":
    test_extreme_curves()
