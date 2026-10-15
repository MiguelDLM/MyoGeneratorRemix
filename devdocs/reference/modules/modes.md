# `modes`

Source: `modes.py`

Safe mode switching.

`bpy.ops.object.mode_set` refuses to run when the active object is not
visible ("Cannot edit hidden object"): the object, or a collection holding it,
was hidden while it was being edited or sculpted (e.g. from the *Show in
Scene* panel or the outliner).

## Functions

### `to_object_mode(context=None)`

Return to Object Mode, even if the object being edited is hidden.

If the plain switch is refused, the object and the collections holding it
are shown for the switch and their visibility is restored afterwards.

| Parameter | Type | Description |
|---|---|---|
| `context` | `bpy.types.Context` | Context (default: `bpy.context`). |
