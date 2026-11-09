import io
import json
from pathlib import Path
import subprocess
import tarfile
from unittest.mock import Mock

import pytest

from inputs.factory import input_factory
from inputs.kubernetes import KubernetesInput


def test_factory_passes_kubernetes_options():
    data_input = input_factory({
        "name": "volume_backup",
        "type": "kubernetes",
        "kubernetes": {
            "statefulset_name": "files",
            "path": "/data",
            "namespace": "production",
            "container": "app",
            "pod_ordinal": 2,
            "kubeconfig": "/config/kubeconfig",
            "context": "production",
            "timeout_seconds": 60,
        },
    })
    assert isinstance(data_input, KubernetesInput)
    assert data_input.get_name() == "volume_backup"
    assert data_input._statefulset_name == "files"
    assert data_input._path == "/data"
    assert data_input._namespace == "production"
    assert data_input._container == "app"
    assert data_input._pod_ordinal == 2
    assert data_input._kubeconfig == "/config/kubeconfig"
    assert data_input._context == "production"
    assert data_input._timeout_seconds == 60


@pytest.mark.parametrize("options,start,replicas,expected_pod", [
    ({}, 0, 1, "files-0"),
    ({}, 3, 2, "files-3"),
    ({"pod_ordinal": 4}, 3, 2, "files-4"),
])
def test_backup_streams_volume_data(monkeypatch, tmp_path, options, start,
                                   replicas, expected_pod):
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
        entry = tarfile.TarInfo("./example.txt")
        entry.size = 4
        archive.addfile(entry, io.BytesIO(b"data"))

    def run(command, **kwargs):
        if "get" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps({
                "spec": {"ordinals": {"start": start}, "replicas": replicas},
            }))
        kwargs["stdout"].write(archive_bytes.getvalue())
        return subprocess.CompletedProcess(command, 0)

    runner = Mock(side_effect=run)
    monkeypatch.setattr("inputs.kubernetes.subprocess.run", runner)
    monkeypatch.setattr("inputs.kubernetes.mkdtemp", lambda: str(tmp_path))
    # Spaces and shell metacharacters remain a single directory argument.
    path = "/data/files with spaces; $(example)"
    data_input = KubernetesInput("volume", "files", path,
                                 namespace="production", container="app",
                                 kubeconfig="/config/kubeconfig", context="cluster",
                                 timeout_seconds=60, **options)
    result = data_input.backup()

    base = ["kubectl", "--namespace=production",
            "--kubeconfig=/config/kubeconfig", "--context=cluster"]
    assert runner.call_args_list[0].args[0] == base + [
        "get", "statefulset/files", "-o", "json",
    ]
    assert runner.call_args_list[1].args[0] == base + [
        "exec", f"pod/{expected_pod}", "--container=app", "--",
        "tar", "czf", "-", "-C", path, ".",
    ]
    assert runner.call_args_list[1].kwargs["check"] is True
    assert runner.call_args_list[1].kwargs["timeout"] == 60
    assert Path(result).name.startswith("volume_")
    with tarfile.open(result) as archive:
        assert archive.extractfile("./example.txt").read() == b"data"


def test_backup_defaults(monkeypatch, tmp_path):
    runner = Mock(side_effect=[
        subprocess.CompletedProcess([], 0, '{"spec": {"replicas": 1}}'),
        subprocess.CompletedProcess([], 0),
    ])
    monkeypatch.setattr("inputs.kubernetes.subprocess.run", runner)
    monkeypatch.setattr("inputs.kubernetes.mkdtemp", lambda: str(tmp_path))
    data_input = input_factory({"name": "volume", "type": "kubernetes",
                               "kubernetes": {"statefulset_name": "files",
                                              "path": "/data"}})
    data_input.backup()
    assert runner.call_args.args[0] == [
        "kubectl", "--namespace=default", "exec", "pod/files-0", "--",
        "tar", "czf", "-", "-C", "/data", ".",
    ]


@pytest.mark.parametrize("error", [
    subprocess.CalledProcessError(1, ["kubectl"]),
    subprocess.TimeoutExpired(["kubectl"], 300),
])
def test_failed_exec_removes_partial_archive(monkeypatch, tmp_path, error):
    output_folder = tmp_path / "backup"
    output_folder.mkdir()

    def run(command, **kwargs):
        if "get" in command:
            return subprocess.CompletedProcess(command, 0, '{"spec": {"replicas": 1}}')
        kwargs["stdout"].write(b"incomplete archive")
        raise error

    monkeypatch.setattr("inputs.kubernetes.subprocess.run", run)
    monkeypatch.setattr("inputs.kubernetes.mkdtemp", lambda: str(output_folder))
    with pytest.raises(type(error)):
        KubernetesInput("volume", "files", "/data").backup()
    assert not output_folder.exists()


@pytest.mark.parametrize("replicas,ordinal", [(0, None), (2, 2)])
def test_unavailable_replica_does_not_exec(monkeypatch, replicas, ordinal):
    runner = Mock(return_value=subprocess.CompletedProcess(
        [], 0, json.dumps({"spec": {"replicas": replicas}})))
    monkeypatch.setattr("inputs.kubernetes.subprocess.run", runner)
    with pytest.raises(ValueError, match="replica range"):
        KubernetesInput("volume", "files", "/data", pod_ordinal=ordinal).backup()
    assert runner.call_count == 1


def test_discovery_failure_is_propagated(monkeypatch):
    runner = Mock(side_effect=subprocess.CalledProcessError(1, ["kubectl"]))
    monkeypatch.setattr("inputs.kubernetes.subprocess.run", runner)
    with pytest.raises(subprocess.CalledProcessError):
        KubernetesInput("volume", "files", "/data").backup()
    assert runner.call_count == 1


@pytest.mark.parametrize("options", [
    {"path": "relative/path"}, {"pod_ordinal": -1}, {"pod_ordinal": "0"},
    {"pod_ordinal": True}, {"timeout_seconds": 0}, {"timeout_seconds": True},
    {"statefulset_name": ""}, {"namespace": ""},
])
def test_invalid_options_are_rejected(options):
    config = {"name": "volume", "statefulset_name": "files", "path": "/data"}
    config.update(options)
    with pytest.raises(ValueError):
        KubernetesInput(**config)
