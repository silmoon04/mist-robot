"""Hide assembly reference graphics and refresh verified native exports."""

from pathlib import Path
import importlib
import sys

import adsk.core


def run(_context: str):
    folder = str(Path(__file__).resolve().parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    import fusion_import
    fusion_import = importlib.reload(fusion_import)
    _, links, _, _, digest = fusion_import._preflight()
    app = adsk.core.Application.get()
    _, design = fusion_import._document_for_input(app, digest)
    design.activateRootComponent()
    root = design.rootComponent
    for component in [root] + [occurrence.component for occurrence in root.allOccurrences]:
        component.isConstructionFolderLightBulbOn = False
        component.isSketchFolderLightBulbOn = False
        component.isJointsFolderLightBulbOn = False
        component.isJointOriginsFolderLightBulbOn = False
        component.isOriginFolderLightBulbOn = False
    for joint in root.asBuiltJoints:
        joint.isLightBulbOn = False
    app.userInterface.activeSelections.clear()
    fusion_import._assert_poses(fusion_import._occurrences(design, links), links)
    return fusion_import.run("export")
