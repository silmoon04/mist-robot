"""Check the real supplier teeth in a native, isolated right-angle fixture."""
import importlib.util
import json
import math
from pathlib import Path
import sys
import adsk.core
import adsk.fusion

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE/'vendor_pair_probe'


def load(name, path):
    module_spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(module_spec)
    sys.modules[name]=module
    exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    return module


def matrix(base, phase):
    t=math.radians(phase)
    ry=[[math.cos(t),0,math.sin(t)],[0,1,0],[-math.sin(t),0,math.cos(t)]]
    result=adsk.core.Matrix3D.create()
    for row in range(3):
        for col in range(3):
            result.setCell(row,col,sum(base[row][k]*ry[k][col] for k in range(3)))
    return result


def run(_context: str):
    OUTPUT.mkdir(exist_ok=True)
    native=load('mist_pair_native',HERE.parent/'native_parts.py')
    step=load('mist_pair_step',HERE/'purchased_step.py')
    app=adsk.core.Application.get()
    previous=app.activeDocument
    report={'status':'started','native_execution':True,'collision_checks':[]}
    try:
        document=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        document.name='MIST KHK native tooth mesh test'
        design=adsk.fusion.Design.cast(app.activeProduct)
        design.designType=adsk.fusion.DesignTypes.ParametricDesignType
        root=design.rootComponent
        root.attributes.add('MIST','build_role','vendor_pair_probe_20260907')
        operation={'path':str(ROOT/'references/KHK_SM1_20/SM1-20_On.stp'),
                   'sha256':'c4aebaa418f6955130f9bf4f4a798dc478b181fea47327865db2d7aedb386a98'}
        occurrences=[]
        bodies=[]
        for name in ('vertical_input','wheel_output'):
            occurrence=root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occurrence.component.name=name
            bodies.append(step.import_single_solid(occurrence.component,name,operation))
            occurrences.append(occurrence)
        bases=([[1,0,0],[0,0,1],[0,-1,0]],[[1,0,0],[0,-1,0],[0,0,-1]])
        # The earlier wrong-sign trial is preserved separately with its native
        # Boolean failure. This run verifies the selected counter-rotating mesh.
        cases=[(0,0,'unphased_control'),(0,9,'assembled_phase')]
        cases += [(angle,9-angle,'coupled_minus_one') for angle in (3,6,9,12,15,18)]
        for input_phase,output_phase,case in cases:
            for occurrence,base,phase in zip(occurrences,bases,(input_phase,output_phase)):
                native.place_occurrence(occurrence,matrix(base,phase))
            if design.computeAll() is False:
                raise RuntimeError('Pair placement recompute failed')
            objects=adsk.core.ObjectCollection.create()
            for body in bodies:
                matches=root.allOccurrencesByComponent(body.parentComponent)
                if matches.count!=1:
                    raise RuntimeError('Ambiguous supplier body context')
                objects.add(body.createForAssemblyContext(matches.item(0)))
            request=design.createInterferenceInput(objects)
            request.areCoincidentFacesIncluded=False
            result=design.analyzeInterference(request)
            if result is None:
                raise RuntimeError('Native pair interference returned no result')
            overlaps=[item.interferenceBody.volume*1000 for item in result]
            report['collision_checks'].append({'input_phase_deg':input_phase,'output_phase_deg':output_phase,
                'case':case,'interference_count':len(overlaps),'volume_mm3':sum(overlaps)})
            (OUTPUT/'verification.json').write_text(json.dumps(report,indent=2))
        for occurrence,base,phase in zip(occurrences,bases,(0,9)):
            native.place_occurrence(occurrence,matrix(base,phase))
        design.computeAll()
        report['volumes_mm3']=[body.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume*1000 for body in bodies]
        report['independent_OCP_volume_mm3']=2332.532046634451
        report['native_OCP_volume_difference_fraction']=(report['volumes_mm3'][0]/report['independent_OCP_volume_mm3']-1)
        report['volume_equivalence_verified']=False
        if report['collision_checks'][0]['volume_mm3']<1:
            raise RuntimeError('The unphased control should produce a measurable clash')
        if any(row['interference_count'] for row in report['collision_checks'][1:]):
            raise RuntimeError('The selected tooth phase intersects in a sampled position')
        if not design.exportManager.execute(design.exportManager.createFusionArchiveExportOptions(str(OUTPUT/'KHK_native_pair.f3d'))):
            raise RuntimeError('Native pair export failed')
        app.activeViewport.fit()
        if not app.activeViewport.saveAsImageFile(str(OUTPUT/'KHK_native_pair.png'),1200,950):
            raise RuntimeError('Native pair preview failed')
        report.update(status='completed',load_capacity_validated=False,full_mesh_kinematics_validated=False)
        return report
    except Exception as exc:
        report.update(status='failed',error=str(exc))
        raise
    finally:
        if previous:
            report['previous_document_reactivated']=bool(previous.activate())
        (OUTPUT/'verification.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
