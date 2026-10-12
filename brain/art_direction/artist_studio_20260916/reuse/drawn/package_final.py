"""Package reviewed artwork and the viewer without changing their bytes."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
REUSE = ROOT.parent
BRAIN = ROOT.parents[3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    atlas = json.loads((ROOT / 'atlas.json').read_text(encoding='utf-8'))
    assert atlas.get('fps') == 15, 'The pack requires the reviewed 15 fps atlas'
    motion = json.loads((ROOT / 'motion_checks.json').read_text(encoding='utf-8'))
    assert motion['passed'], 'Motion checks must pass'
    assert motion['sourceSha256'] == sha((ROOT / 'preview.js').read_bytes()), 'Stale motion checks'
    assert motion['sharedRuntimeSha256'] == sha((REUSE / 'runtime/drawn_face_renderer.js').read_bytes()), 'Stale motion renderer checks'
    payload = {}

    def add(path, name):
        data = path.read_bytes()
        if name in payload:
            assert payload[name] == data, 'Conflicting archive path: ' + name
        payload[name] = data
        return data

    required = ['index.html', 'preview.js', 'preview.css', 'transitions.html', 'transitions.js',
                'transitions.css', 'atlas.json', 'atlas.js', 'validation.json', 'asset_notes.txt',
                'motion_checks.json', 'motion_checks.cjs', 'generated_eyes_v2.json',
                'generated_mouths_v2.json', 'blink_detail_v2_provenance.json',
                'identity_audit_initial.json', 'identity_audit.json', 'visual_quality_checks.json',
                'mouth_family_map_v4.json', 'reviewed_mouth_sources_v4.json', 'identity_after.json']
    for name in required:
        add(ROOT / name, 'drawn/' + name)
    optional = ['prompts.json', 'revised_prompts.json', 'generated_blinks.json',
                'generated_mouths.json', 'hook_prompt.txt', 'reviewed_eye_sources.json',
                'eye_v2_audit.json', 'mouth_v2_validation.json', 'mouth_v2_plan.json',
                'identity_audit.md', 'QUALITY_REVIEW.md', 'visual_quality_checks.py',
                'identity_audit.py', 'identity_after.json', 'identity_after.md',
                'check_mouth_v2.py', 'audit_eyes_v2.py']
    for name in optional:
        if (ROOT / name).exists():
            add(ROOT / name, 'drawn/' + name)
    for path in sorted(ROOT.iterdir()):
        lower = path.name.lower()
        is_consonant_record = 'mouth_consonants_v3' in lower and path.suffix in ('.json', '.md', '.py')
        is_final_review = any(version in lower for version in ('v3', 'v4')) and 'review' in lower and path.suffix in ('.json', '.md', '.txt')
        is_v4_record = 'v4' in lower and path.suffix in ('.json', '.md', '.txt', '.py') and any(
            word in lower for word in ('mouth', 'layout', 'plan', 'emotion', 'mapping'))
        if path.is_file() and (is_consonant_record or is_final_review or is_v4_record):
            destination = 'history/v4/' if is_final_review and 'v4' in lower else 'drawn/'
            add(path, destination + path.name)
    historical_reports = []
    for name in ['motion_checks_v4.json', 'identity_v4.json', 'identity_after_v4.json',
                 'v4_motion_checks.json', 'v4_identity_after.json', 'drawn_face_renderer_v4.js']:
        path = ROOT / name
        if path.exists():
            destination = 'history/v4/' + name
            add(path, destination)
            historical_reports.append(destination)
    v5_records = []
    for folder in [ROOT, BRAIN / 'harness', BRAIN / 'duplex']:
        for path in sorted(folder.iterdir()):
            lower = path.name.lower()
            if path.is_file() and 'v5' in lower and path.suffix.lower() in ('.json', '.md', '.txt', '.py', '.cjs') and any(
                    word in lower for word in ('blink', 'orientation', 'review', 'motion', 'identity')):
                destination = 'refinement_v5/' + path.relative_to(BRAIN).as_posix()
                add(path, destination)
                v5_records.append(destination)
    for doc_name in ['ANIMATION_REFINEMENT_20260922.md', 'FACE_CONTROL.md', 'EMOTION_MOUTHS_20260923.md', 'BLINK_ORIENTATION_20260923.md']:
        for path in sorted(BRAIN.rglob(doc_name)):
            add(path, 'documentation/' + path.relative_to(BRAIN).as_posix())
    # Shared sheets retain one archive path, even when several assets use them.
    sheet_paths = set()
    selected_crops = set()
    for asset in atlas['assets'].values():
        data = add(ROOT / asset['file'], 'drawn/' + asset['file'])
        assert sha(data) == asset['sha256'], 'Changed source sheet: ' + asset['file']
        sheet_paths.add(asset['file'])
        for frame in asset['frames']:
            frame_file = frame.get('file', asset['file'])
            expected_hash = frame.get('sha256', asset['sha256'] if frame_file == asset['file'] else None)
            assert expected_hash, 'Replacement frame needs a source hash: ' + frame_file
            frame_data = add(ROOT / frame_file, 'drawn/' + frame_file)
            assert sha(frame_data) == expected_hash, 'Changed frame source sheet: ' + frame_file
            sheet_paths.add(frame_file)
            selected_crops.add((Path(frame_file).as_posix(), frame['x'], frame['y'], frame['w'], frame['h']))
    for name in ['audit.js', 'runtime/app_data.js', 'runtime/face_runtime.js',
                 'runtime/drawn_face_renderer.js', 'runtime/playback.js',
                 'grid.html', 'grid.css', 'grid.js']:
        add(REUSE / name, name)
    for name in ['EXPRESSION_INTEGRATION.md', 'face_map.json', 'static/expression_policy.js',
                 'VOICE_SYNC_REVIEW_20260922.md', 'LIVE_SYNC_BLOCKER_20260922.json']:
        add(BRAIN / 'duplex' / name, 'integration/' + name)
    add(BRAIN / 'results/expression_probe_20260922_final/report.json', 'integration/luna_probe_report.json')
    for rel in ['results/luna_face_switching_20260922/REVIEW.md',
                'results/luna_face_switching_20260922/review.json',
                'results/expression_hold_transition_20260922.json',
                'harness/drawn_timing_checks.json', 'harness/DRAWN_TIMING_CONTRACT.txt',
                'harness/mouth_family_checks.json', 'harness/MOUTH_FAMILY_CONTRACT.txt']:
        add(BRAIN / rel, 'integration/' + Path(rel).name)
    for name in ['test_emotion_mouths_v4.py', 'test_mouth_families.cjs']:
        add(BRAIN / 'harness' / name, 'integration/tests/' + name)
    audio_files = sorted(p for p in (ROOT / 'audio').rglob('*') if p.suffix.lower() in ('.wav', '.json'))
    for path in audio_files:
        add(path, 'drawn/' + path.relative_to(ROOT).as_posix())
    samples = json.loads((ROOT / 'audio/samples.json').read_text(encoding='utf-8-sig'))
    for sample in samples:
        rel = sample['file'] if sample['file'].startswith('audio/') else 'audio/' + sample['file']
        assert 'drawn/' + rel in payload, 'Missing audio sample: ' + rel
        if sample.get('cues'):
            rel = sample['cues'] if sample['cues'].startswith('audio/') else 'audio/' + sample['cues']
            assert 'drawn/' + rel in payload, 'Missing audio cues: ' + rel
    renderer_report = BRAIN / 'harness/drawn_face_renderer_checks.json'
    assert renderer_report.exists(), 'Current renderer checks are required'
    report = json.loads(renderer_report.read_text(encoding='utf-8'))
    assert report['passed'], 'Renderer checks must pass'
    assert report['rendererSha256'] == sha(payload['runtime/drawn_face_renderer.js']), 'Stale renderer checks'
    add(renderer_report, 'drawn/reports/drawn_face_renderer_checks.json')
    blink_report_path = BRAIN / 'harness/blink_orientation_report.json'
    blink_checks = json.loads(blink_report_path.read_text(encoding='utf-8'))
    assert blink_checks['passed'], 'Blink orientation checks must pass'
    assert blink_checks['rendererSha256'] == sha(payload['runtime/drawn_face_renderer.js']), 'Stale blink orientation checks'
    add(blink_report_path, 'integration/blink_orientation_report.json')
    for blink_test in ['test_blink_orientation.cjs', 'blink_orientation_pixels.py', 'BLINK_ORIENTATION_STATUS.txt']:
        add(BRAIN / 'harness' / blink_test, 'integration/tests/' + blink_test)
    family_checks = json.loads(payload['integration/mouth_family_checks.json'])
    assert family_checks['passed'], 'Mouth-family checks must pass'
    assert family_checks['rendererSha256'] == sha(payload['runtime/drawn_face_renderer.js']), 'Stale mouth-family checks'
    assert family_checks.get('atlasMode') == 'published atlas', 'Mouth-family checks must use the published atlas'
    report_hashes = {'sourceSha256': sha(payload['drawn/preview.js']),
                     'sharedRuntimeSha256': sha(payload['runtime/drawn_face_renderer.js']),
                     'rendererSha256': sha(payload['runtime/drawn_face_renderer.js']),
                     'atlasSha256': sha(payload['drawn/atlas.json']),
                     'playbackSha256': sha(payload['runtime/playback.js'])}

    def check_available_hashes(value, label):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in report_hashes:
                    assert child == report_hashes[key], 'Stale report hash: ' + label + '/' + key
                else:
                    check_available_hashes(child, label + '/' + key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                check_available_hashes(child, label + '/' + str(index))

    for name, current_report in [('motion_checks.json', motion), ('mouth_family_checks.json', family_checks),
                                 ('drawn_face_renderer_checks.json', report), ('blink_orientation_report.json', blink_checks)]:
        check_available_hashes(current_report, name)
    identity = json.loads((ROOT / 'identity_after.json').read_text(encoding='utf-8'))
    assert identity['passed'], 'Identity checks must pass'
    identity_files = {'renderer': payload['runtime/drawn_face_renderer.js'],
                      'publishedRenderer': payload['runtime/drawn_face_renderer.js'],
                      'base': payload['runtime/face_runtime.js'],
                      'data': payload['runtime/app_data.js'], 'atlas': payload['drawn/atlas.json']}
    for name, data in identity_files.items():
        assert identity['hashes'].get(name) == sha(data), 'Stale identity checks: ' + name
    # Versioned v4 evidence stays immutable and does not validate the current renderer.
    legacy = {'purpose': 'Earlier source sheets; see sheet index for active shared files', 'assets': {}}
    digest_paths = {sha(data): name for name, data in payload.items() if name.endswith('.png')}
    prior_atlas_path = ROOT / 'v1_atlas.json'
    if prior_atlas_path.exists():
        prior = json.loads(prior_atlas_path.read_text(encoding='utf-8'))
        for key, asset in prior['assets'].items():
            data = (ROOT / asset['file']).read_bytes()
            assert sha(data) == asset['sha256'], 'Changed legacy sheet: ' + key
            target = digest_paths.get(asset['sha256'])
            if target is None:
                target = 'legacy/v1/sheets/' + Path(asset['file']).name
                payload[target] = data
                digest_paths[asset['sha256']] = target
            legacy['assets'][key] = {'archivePath': target, 'sha256': asset['sha256']}
        payload['legacy/v1/sheet_index.json'] = (json.dumps(legacy, indent=2) + '\n').encode('utf-8')
        for name in ['v1_atlas.json', 'v1_validation.json', 'v1_visual_quality_checks.json']:
            if (ROOT / name).exists():
                add(ROOT / name, 'legacy/v1/' + name)
    payload['index.html'] = b'<!doctype html>\n<meta charset="utf-8">\n<meta http-equiv="refresh" content="0;url=drawn/">\n<title>MIST motion viewer</title>\n<a href="drawn/">Open motion viewer</a>\n'
    frame_entry_count = sum(len(a['frames']) for a in atlas['assets'].values())
    unique_crop_count = len(selected_crops)
    readme = f'''MIST drawn animation pack

This pack includes the current 40-face viewer, expression transitions, saved voice
samples, the previous procedural preview, source sheets, and validation reports.

Extract the ZIP. Open a terminal in the extracted folder and run:
python -m http.server 8795
Then open http://127.0.0.1:8795/drawn/
Transitions: http://127.0.0.1:8795/drawn/transitions.html
Use a local HTTP server because the viewer fetches data and audio files.
Any static HTTP server works. The in-page download link belongs to the hosted studio;
the ZIP does not contain itself.

The active atlas has {len(atlas['assets'])} reusable motion assets and {frame_entry_count} animation entries.
Those entries select {unique_crop_count} distinct source crops across {len(sheet_paths)} source sheets.
Repeated pose aliases and shared drawings do not count as new artwork. A source crop
is identified by its sheet path and x, y, width and height, not by its pose name.
Six emotion families and a neutral shared base reuse rounded vowels, lip closures
and clean consonants. Five new families provide the seven requested poses plus a
release pose each: angry, sad, flat, worried and skeptical. The existing happy set stays.
The new ImageGen drawings are combined with exact
original MIST resting faces. This is a hybrid renderer, not 40 independently drawn
face animations. Original mode and the previous grid use the original vector artwork.
The current atlas targets 15 fps. FV and TH use the shared clean v3 consonant
drawings. Happy and neutral LNT poses also use v3; each of the five new emotion
families has its own v4 LNT drawing. Other poses use reviewed v2 and v4 sheets. Rejected consonant
positions remain visible in those source sheets but are not selected by the atlas.
Per-frame file, sha256 and sourceScale metadata are preserved for replacement cels.
PNG bytes are unchanged. Background removal and sprite registration happen at display time.
Shared source sheets are packaged once. Earlier sheets are retained under legacy/v1;
its sheet_index.json identifies any files shared with the active atlas.

The {len(samples)} saved recordings demonstrate audio timing. Their alignment metadata is in
drawn/audio/samples.json. Energy-only playback is not phoneme-aligned lip-sync.
Fresh aligned voice samples could not be verified because a failed provider payment
blocked generation. This pack makes no new API calls and contains no API credentials.

drawn/validation.json checks source integrity and populated cells.
drawn/motion_checks.json checks grid transforms, bounds and blink timing.
To repeat those motion checks with Node.js: node drawn/motion_checks.cjs
Identity, visual-quality and renderer reports are included with their own limits.
integration/mouth_family_checks.json records the current family-routing checks.
The test sources in integration/tests preserve their original repository paths;
run them from the full source workspace, not directly from this viewer pack.
Earlier reports are retained as comparisons; they do not certify the current viewer.
Archived v4 reports and reviews are under history/v4. They retain the hashes of that
earlier renderer and are not required to match the current blink-orientation fix.
Available v5 refinement reports and review notes are under refinement_v5.
The unversioned motion, identity, renderer and mouth-family checks are the current
packaging requirements; their renderer and atlas hashes are checked before building.
These checks do not establish subjective animation quality or fresh live lip-sync.
package_manifest.json lists SHA-256 hashes for every payload file.
'''
    (ROOT / 'package_readme.txt').write_text(readme, encoding='utf-8')
    payload['README.txt'] = readme.encode('utf-8')
    manifest = {'purpose': 'Hybrid MIST motion viewer, source artwork, transitions and saved audio',
                'assets': len(atlas['assets']), 'animationEntries': frame_entry_count,
                'uniqueSelectedSourceCrops': unique_crop_count,
                'sourceCropIdentity': ['file', 'x', 'y', 'w', 'h'],
                'fps': atlas['fps'],
                'uniqueActiveSheets': len(sheet_paths), 'savedAudioSamples': len(samples),
                'freshAlignedVoiceVerified': False, 'freshVoiceBlocker': 'provider payment_required',
                'previewSha256': motion['sourceSha256'], 'motionChecksPassed': True,
                'rendererChecksPassed': True, 'identityChecksPassed': True, 'mouthFamilyChecksPassed': True,
                'currentReports': ['drawn/motion_checks.json', 'drawn/identity_after.json',
                                   'drawn/reports/drawn_face_renderer_checks.json', 'integration/mouth_family_checks.json'],
                'historicalReports': historical_reports,
                'v5RefinementRecords': v5_records,
                'sourcePngBytesPreserved': True,
                'files': {name: {'bytes': len(data), 'sha256': sha(data)} for name, data in sorted(payload.items())}}
    text = json.dumps(manifest, indent=2) + '\n'
    (ROOT / 'package_manifest.json').write_text(text, encoding='utf-8')
    payload['package_manifest.json'] = text.encode('utf-8')
    output = ROOT / 'MIST_drawn_animation_pack.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(payload)
        for name, data in payload.items():
            assert archive.read(name) == data
    print(json.dumps({'archiveBytes': output.stat().st_size, 'archiveSha256': sha(output.read_bytes()),
                      'entries': len(payload), 'viewer': 'drawn/index.html',
                      'animationEntries': frame_entry_count, 'uniqueSelectedSourceCrops': unique_crop_count,
                      'uniqueActiveSheets': len(sheet_paths), 'savedAudioSamples': len(samples)}))


if __name__ == '__main__':
    main()
