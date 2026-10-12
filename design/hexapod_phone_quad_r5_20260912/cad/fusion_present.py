"""Hide assembly reference graphics and refresh verified native exports."""

from pathlib import Path
import importlib.util

import adsk.core


def run(_context: str):
    source = Path(__file__).resolve().with_name('fusion_runtime_r5.py')
    spec = importlib.util.spec_from_file_location('hex_quad_r5_runtime_loader', source)
    loader = importlib.util.module_from_spec(spec)
    exec(compile(source.read_bytes(), str(source), 'exec'), loader.__dict__)
    fusion_import = loader.load_runtime()
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
