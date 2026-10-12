"""Portable package checks use temporary toy archives, never release outputs."""
import importlib.util
from pathlib import Path
import zipfile
import pytest

path=Path(__file__).parents[1]/'scripts/package_simulation.py'
spec=importlib.util.spec_from_file_location('package_simulation',path)
package=importlib.util.module_from_spec(spec);spec.loader.exec_module(package)


def test_toy_package_roundtrip_and_no_overwrite(tmp_path,monkeypatch):
    repo=tmp_path/'repo';(repo/'locomotion').mkdir(parents=True)
    source=repo/'locomotion/minimal.py';source.write_text('value = 1\n')
    monkeypatch.setattr(package,'REPO',repo)
    monkeypatch.setattr(package,'source_hashes',lambda:{'locomotion/minimal.py':package.sha(source)})
    manifest=package.inventory();archive=tmp_path/'toy.zip'
    package.create_archive(archive,manifest)
    assert package.validate_archive(archive)['files']==1
    with pytest.raises(FileExistsError):package.create_archive(archive,manifest)
    source.write_text('value = 2\n')
    with pytest.raises(RuntimeError):package.create_archive(tmp_path/'changed.zip',manifest)
    assert not (tmp_path/'changed.zip').exists()


@pytest.mark.parametrize('name',['../escape','/escape','C:/escape','safe/../escape','safe\\escape','safe//escape'])
def test_unsafe_package_paths_rejected(name):
    with pytest.raises(ValueError):package.safe_relative(name)


def test_source_symlink_rejected(tmp_path,monkeypatch):
    repo=tmp_path/'repo';repo.mkdir();outside=tmp_path/'outside';outside.write_text('secret')
    (repo/'redirect').symlink_to(outside)
    monkeypatch.setattr(package,'REPO',repo)
    with pytest.raises(ValueError):package.source_file('redirect')


def test_archive_traversal_rejected_before_manifest_read(tmp_path):
    archive=tmp_path/'malformed.zip'
    with zipfile.ZipFile(archive,'w') as writer:writer.writestr('mist-robot/../escape','bad')
    with pytest.raises(ValueError):package.validate_archive(archive)
