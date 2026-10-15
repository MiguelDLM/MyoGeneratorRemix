"""Safe mode switching.

``bpy.ops.object.mode_set`` refuses to run when the active object is not
visible ("Cannot edit hidden object"): the object, or a collection holding it,
was hidden while it was being edited or sculpted (e.g. from the *Show in
Scene* panel or the outliner).
"""

import bpy


def _layer_collections(layer_collection, obj, path=()):
    """Layer collections (outermost first) on the way to a collection that holds ``obj``."""
    path = path + (layer_collection,)
    if obj.name in layer_collection.collection.objects:
        return path
    for child in layer_collection.children:
        found = _layer_collections(child, obj, path)
        if found:
            return found
    return ()


def to_object_mode(context=None):
    """Return to Object Mode, even if the object being edited is hidden.

    If the plain switch is refused, the object and the collections holding it
    are shown for the switch and their visibility is restored afterwards.

    :arg context: Context (default: ``bpy.context``).
    :type context: :class:`bpy.types.Context`
    """
    context = context or bpy.context
    if context.mode == 'OBJECT':
        return
    obj = context.view_layer.objects.active
    if obj is None:
        return
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
        return
    except RuntimeError:
        pass
    restore = []
    try:
        hidden = obj.hide_get()
    except RuntimeError:
        hidden = False
    restore.append((obj, "hide_viewport", obj.hide_viewport))
    obj.hide_viewport = False
    if hidden:
        obj.hide_set(False)
    for lc in _layer_collections(context.view_layer.layer_collection, obj)[1:]:
        restore.append((lc, "hide_viewport", lc.hide_viewport))
        restore.append((lc, "exclude", lc.exclude))
        restore.append((lc.collection, "hide_viewport", lc.collection.hide_viewport))
        lc.exclude = False
        lc.hide_viewport = False
        lc.collection.hide_viewport = False
    context.view_layer.update()
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    finally:
        for target, attr, value in reversed(restore):
            setattr(target, attr, value)
        if hidden:
            obj.hide_set(True)
