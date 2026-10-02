# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""MyoGeneratorRemix: volumetric reconstruction of muscles and their parameters.

Package layout (see ``devdocs/ARCHITECTURE.md``):

* ``properties.py``                - scene settings (``scene.myogen``)
* ``core_operators.py``            - attachments, mirroring, checks, export operators
* ``improved_muscle_workflow.py``  - preview, path, ring and final mesh operators
* ``tube.py``                      - path sampling and the tube swept along it
* ``rings.py``                     - section rings sliding on the path (size, turn)
* ``preview.py``                   - loft construction, path and attachment/bone geometry
* ``volume_builder.py``            - solid belly (tube or fan fibres along the path), live preview, final mesh
* ``fan.py``                       - fibres of fan-shaped muscles
* ``curve_utilities.py``           - path-curve validation, sampling and orientation frames
* ``muscle_utilities.py``          - selection helpers and contour alignment
* ``muscle_texture.py``            - procedural muscle material
* ``muscle_metrics.py``            - measurements, plausibility checks, CSV export
* ``myo_record.py``                - the muscle-record contract shared with MUFIS
* ``myoGenerator_panel.py``        - the sidebar UI
"""

import bpy

from .core_operators import (Muscle_Name_Submition, Select_Origin_Op,
                            Select_Insertion_Op, Submit_Origin_Op,
                            Submit_Insertion_Op, Next_Muscle_Op,
                            Calculate_Muscle_Parameters_Op,
                            Check_Muscles_Op, Set_Unit_Scale_Op,
                            MYOGENERATOR_OT_mirror_duplicate,
                            Estimate_Selected_Volumes_Op)
from .properties import MyoGeneratorProperties
from . import preview
from . import volume_builder
from .improved_muscle_workflow import (Muscle_Edit_Path_Op,
                                     Muscle_Reset_Path_Op,
                                     Muscle_Select_Rings_Op,
                                     Muscle_Reset_Rings_Op,
                                     Muscle_Mesh_Generation_Op,
                                     Muscle_Preview_Update_Op,
                                     Muscle_Preview_Stop_Op)
from .myoGenerator_panel import MYOGENERATOR_PT_panel


class MyoGeneratorPreferences(bpy.types.AddonPreferences):
    # __package__ matches both the development and the installed module name.
    """Add-on preferences: the switch that shows the experimental tools in the panel."""
    bl_idname = __package__

    show_advanced: bpy.props.BoolProperty(
        name="Show Advanced (experimental) features",
        description="Enable experimental features in the MyoGenerator panel",
        default=False,
    )

    def draw(self, context):
        self.layout.prop(self, "show_advanced")


def get_preferences(context=None):
    """MyoGeneratorRemix add-on preferences.

    :arg context: Context (default: ``bpy.context``).
    :type context: :class:`bpy.types.Context`
    :return: The preferences, or None when the add-on is loaded under another module name.
    :rtype: :class:`MyoGeneratorPreferences` or None
    """
    addon = (context or bpy.context).preferences.addons.get(__package__)
    return addon.preferences if addon else None


classes = (
    MyoGeneratorPreferences,
    MyoGeneratorProperties,
    Muscle_Name_Submition,
    Select_Origin_Op,
    Select_Insertion_Op,
    Submit_Origin_Op,
    Submit_Insertion_Op,
    Calculate_Muscle_Parameters_Op,
    Check_Muscles_Op,
    Set_Unit_Scale_Op,
    Next_Muscle_Op,
    Estimate_Selected_Volumes_Op,
    Muscle_Edit_Path_Op,
    Muscle_Reset_Path_Op,
    Muscle_Select_Rings_Op,
    Muscle_Reset_Rings_Op,
    Muscle_Mesh_Generation_Op,
    Muscle_Preview_Update_Op,
    Muscle_Preview_Stop_Op,
    MYOGENERATOR_OT_mirror_duplicate,
    MYOGENERATOR_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.myogen = bpy.props.PointerProperty(type=MyoGeneratorProperties)
    preview.register()
    volume_builder.register()


def unregister():
    volume_builder.unregister()
    preview.unregister()
    del bpy.types.Scene.myogen
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
