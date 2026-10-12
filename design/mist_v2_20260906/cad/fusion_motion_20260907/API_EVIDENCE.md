Fusion motion API evidence, checked 2026-09-07
================================================

Current implementation note: the documentation review below predates the live fixtures. The first native custom-line implementation failed its axis probe. The passing implementation uses a fixed SketchPoint on a plane whose normal is the intended axis and standard `ZAxisJointDirection`, with a 0.1° transient drive measured before Compute All. The actual 17-component/16-joint fixture passed; see `NATIVE_VERIFICATION.md`. The earlier API review is retained as evidence of what was checked, not presented as proof that the original custom-line implementation worked.

This section is a documentation and installed-stub check performed before Fusion was run. These findings alone do not establish that the nested assembly solves or that its motion is collision-free.

The installed Autodesk Python definitions were read at:

`<LOCAL_HOME>/AppData/Local/Autodesk/webdeploy/production/61bf25b220a2d0307c84c301e65a59ac225d9a1e/API/Python/packages/adsk/defs/adsk/fusion.py`

SHA-256: `6ecdd9cf378b985eed720957c395c967576699477ecfb078a4dc0d740646f205`.

Public Autodesk API pages agree with the relevant signatures. Some unprefixed Autodesk page URLs returned 404 through the browser fetch despite being indexed; the installed definitions were used to check the actual method descriptions in those cases. No community answer is treated as an API contract here.

**As-built revolute creation**

The supported Python call sequence is:

```python
joint_input = owner_component.asBuiltJoints.createInput(
    occurrence_one, occurrence_two, joint_geometry
)
ok = joint_input.setAsRevoluteJointMotion(
    adsk.fusion.JointDirections.CustomJointDirection, axis_entity
)
joint = owner_component.asBuiltJoints.add(joint_input)
motion = adsk.fusion.RevoluteJointMotion.cast(joint.jointMotion)
```

The exact installed signatures are:

```python
AsBuiltJoints.createInput(self, occurrenceOne: Occurrence,
    occurrenceTwo: Occurrence, geometry: JointGeometry) -> AsBuiltJointInput
AsBuiltJointInput.setAsRevoluteJointMotion(self, rotationAxis: JointDirections,
    customRotationAxisEntity: core.Base = None) -> bool
AsBuiltJoints.add(self, input: AsBuiltJointInput) -> AsBuiltJoint
```

The geometry argument is required for the revolute location. `None` is the documented value for a rigid as-built joint. `createInput` and `add` may return null; defining revolute motion returns a success boolean. These APIs were introduced in September 2015. Sources: [createInput](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/AsBuiltJoints_createInput.htm), [setAsRevoluteJointMotion](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/AsBuiltJointInput_setAsRevoluteJointMotion.htm), [add](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/AsBuiltJoints_add.htm); installed classes at lines 3351 and 3521.

**Point and axis geometry**

`JointGeometry.createByPoint(point: core.Base) -> JointGeometry` accepts an actual `ConstructionPoint`, `SketchPoint`, or `BRepVertex`. It does **not** accept a transient `adsk.core.Point3D`. The broad `Base` annotation does not expand the supported types. [Autodesk createByPoint](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/JointGeometry_createByPoint.htm).

For coordinates known numerically in a parametric document, create real sketch geometry first. `SketchPoints.add(point: core.Point3D) -> SketchPoint` accepts coordinates in the sketch. `Sketch.modelToSketchSpace(modelCoordinate: core.Point3D) -> core.Point3D` handles the conversion and is sensitive to assembly context. Installed definitions are at lines 35639 and 33281. A native point owned by a component can then become assembly geometry using `SketchPoint.createForAssemblyContext(occurrence: Occurrence) -> SketchPoint`, line 57132.

Two shortcuts are unsuitable for a parametric helper:

- `ConstructionPointInput.setByPoint(point: core.Base) -> bool` accepts a raw `Point3D` only in direct modeling. A `SketchPoint` or `BRepVertex` is the documented parametric alternative. [Autodesk setByPoint](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_ConstructionPointInput_setByPoint.htm).
- `ConstructionAxisInput.setByLine(line: core.InfiniteLine3D) -> bool` creates a non-parametric axis and fails in parametric modeling. The installed `ConstructionAxes.add` description repeats this restriction. Installed lines 10446 onward and 10205.

A construction axis can instead be created parametrically from real point entities:

```python
axis_input = component.constructionAxes.createInput()
ok = axis_input.setByTwoPoints(point_entity_one, point_entity_two)
axis = component.constructionAxes.add(axis_input)
```

The exact signatures are `ConstructionAxes.createInput(self, occurrenceForCreation: Occurrence = None) -> ConstructionAxisInput`, `ConstructionAxisInput.setByTwoPoints(self, pointEntityOne: core.Base, pointEntityTwo: core.Base) -> bool`, and `ConstructionAxes.add(self, input: ConstructionAxisInput) -> ConstructionAxis`. Both points must be distinct construction points, sketch points, or vertices. This method supports either parametric or direct components and dates to August 2014. [Autodesk setByTwoPoints](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ConstructionAxisInput_setByTwoPoints.htm).

For a custom revolute axis, Autodesk explicitly gives a sketch line, linear edge, planar face, and cylindrical face as supported examples. The text allows other entities that infer an axis but does not expressly enumerate `ConstructionAxis`; passing one remains a runtime acceptance check. A fixed `SketchLine` in the parent link is the documented choice for this helper. Do not pass its transient `Line3D` geometry or an arbitrary `Vector3D` as the axis entity. [Autodesk customRotationAxisEntity](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/RevoluteJointMotion_customRotationAxisEntity.htm); installed `RevoluteJointMotion` at line 55578.

`JointGeometry.createByCurve(curve: core.Base, keyPointType: JointKeyPointTypes) -> JointGeometry` accepts a `BRepEdge` or `SketchCurve`; the documented list does not include a construction axis. `createByPlanarFace(face, edge, keyPointType)` and `createByProfile(profile, sketchCurve, keyPointType)` can also define a frame. The computed primary, secondary, and third axes correspond to Z, X, and Y respectively. Those vectors and the origin are read-only calculated results. Do not assume the joint's Z direction equals global Z. [Autodesk JointGeometry](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/JointGeometry.htm); installed class at line 19413.

**Assembly context and rigid groups**

The collection used for creation determines the owner. `design.rootComponent.asBuiltJoints` creates root-owned joints; changing the UI's active component is not the way to choose that owner. Autodesk's simple as-built sample also uses the root collection. [As-built sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/AsBuiltJointSample_Sample.htm), [components and proxies](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ComponentsProxies_UM.htm).

For this nested assembly, root-owned joints should receive both occurrences and datum geometry in root assembly context. A full-path leaf occurrence identifies the correct instance. Create the datum in the parent link's native component, then call `native_datum.createForAssemblyContext(parent_leaf_occurrence)` before passing it to the root joint. This preserves the datum's association with the moving parent link. Using raw native geometry from a nested component would omit the instance path. This design follows Autodesk's proxy model; it has not been tested with this assembly in Fusion.

`Occurrence.createForAssemblyContext` specifically requires a native occurrence in the installed signature. Avoid wrapping an occurrence that is already a full-path proxy. Native sketch points and construction axes have their own proxy creators. Transform and inspect positions with `Occurrence.transform2`, which replaced the retired `transform` because the latter can return incorrect results. [Autodesk transform2](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrence_transform2.htm); installed line 24689.

If a construction axis is created in a non-root component using geometry from another component, set `ConstructionAxisInput.creationOccurrence` (or the optional `ConstructionAxes.createInput` argument). If the datum and its input geometry are native to the same parent-link component, that cross-component condition does not arise. [Autodesk creationOccurrence](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ConstructionAxisInput_creationOccurrence.htm).

The exact rigid-group signature is:

```python
RigidGroups.add(self, occurrences: core.ObjectCollection,
    includeChildren: bool) -> RigidGroup
```

Use `root.rigidGroups.add(collection_of_link_leaf_occurrences, False)` to group the explicitly selected leaves. `includeChildren=False` avoids adding all descendants of a selected container. The collection is an `adsk.core.ObjectCollection`, not a Python list. The method returns the new group or null and dates to September 2015. [Autodesk RigidGroups.add](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/RigidGroups_add.htm).

Autodesk says its aggregate as-built joint and rigid-group queries flatten the assembly for manipulation and return nested relationships as proxies. This supports using root context across nested links, but does not prove solver compatibility or absence of overconstraint in this particular tree. [Autodesk Component](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Component.htm).

The installed `Occurrence` class has no `isFlexible` property. Do not invent a flexible-subassembly setter. It has two separate grounding flags: `isGrounded` means pinned; `isGroundToParent` grounds to the parent. Both moving leaves and their ancestor state need inspection so inherited grounding does not defeat the joints. The proposed assembly should retain one intended chassis anchor while clearing unintended constraints on moving links. This last sentence is an implementation recommendation, not a guarantee that one anchor is sufficient. [Autodesk isGrounded](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrence_isGrounded.htm), [isGroundToParent](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrence_isGroundToParent.htm). The second property was introduced in May 2024.

**Limits, driving, and sign verification**

`RevoluteJointMotion.rotationLimits -> JointLimits` returns the limits object. Set its float properties `minimumValue`, `maximumValue`, and optionally `restValue`, plus the independent booleans `isMinimumValueEnabled`, `isMaximumValueEnabled`, and `isRestValueEnabled`. Angular values are radians, not degrees or `ValueInput` objects. `RevoluteJointMotion.rotationValue` is a read/write float in radians and drives the joint. Autodesk's revolute sample sets limits after creating the joint. [Revolute sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/RevoluteJointMotionSample_Sample.htm), [maximumValue units](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/JointLimits_maximumValue.htm); installed `JointLimits` at line 19879 and `RevoluteJointMotion` at line 55578.

`rotationAxisVector` is read-only and can be null when obtained from an input rather than a created joint. The `rotationAxis` setter only accepts X/Y/Z standard directions; set `customRotationAxisEntity` to change to a custom direction. Do not assign `CustomJointDirection` to the `rotationAxis` property itself. Installed `RevoluteJointMotion` descriptions establish these restrictions.

Neither the inspected Autodesk documentation nor installed definitions establish a positive rotation sign for occurrence one relative to occurrence two. They also do not establish that a newly created as-built joint's `rotationValue` is always zero. Child as occurrence one and parent as occurrence two is therefore an implementation choice whose sign requires measurement.

The helper should capture its initial API rotation `r0` and physical coordinate `q0`, then perform a small reversible drive and compare the child transform relative to the parent before trusting sign `s`. The mapping is `r = r0 + s * (q - q0)`, with `s` measured as +1 or -1. Sort the two mapped limit endpoints before assigning minimum and maximum. Restore the original pose after the probe. Measuring only `rotationAxisVector` does not identify which occurrence rotated positively. This is a proposed runtime validation, not a completed test.

When changing an existing as-built joint's geometry or motion type, Autodesk requires its timeline marker immediately before that joint, using `joint.timelineObject.rollTo(True)`. The initial input construction does not need that edit operation. [Autodesk AsBuiltJoint](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/AsBuiltJoint.htm).
