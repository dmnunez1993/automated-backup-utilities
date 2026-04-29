from unittest.mock import MagicMock, patch

from outputs.minio import MinioOutput


def _make_output():
    return MinioOutput(
        endpoint="localhost:9000",
        access_key="key",
        secret_key="secret",
        secure=False,
        bucket_name="test-bucket",
    )


def test_store_calls_fput_object_with_correct_args():
    output = _make_output()
    mock_client = MagicMock()

    with patch("outputs.minio.Minio", return_value=mock_client):
        output.store("backup.tar.gz", "/tmp/backup.tar.gz")

    mock_client.fput_object.assert_called_once_with(
        "test-bucket", "backup.tar.gz", "/tmp/backup.tar.gz", None
    )


def test_store_passes_content_type_when_provided():
    output = _make_output()
    mock_client = MagicMock()

    with patch("outputs.minio.Minio", return_value=mock_client):
        output.store("backup.tar.gz", "/tmp/backup.tar.gz", "application/gzip")

    mock_client.fput_object.assert_called_once_with(
        "test-bucket", "backup.tar.gz", "/tmp/backup.tar.gz", "application/gzip"
    )


def test_list_files_returns_object_names():
    output = _make_output()
    mock_client = MagicMock()
    obj1, obj2 = MagicMock(), MagicMock()
    obj1.object_name = "backup1.tar.gz"
    obj2.object_name = "backup2.tar.gz"
    mock_client.list_objects.return_value = [obj1, obj2]

    with patch("outputs.minio.Minio", return_value=mock_client):
        result = output.list_files()

    mock_client.list_objects.assert_called_once_with("test-bucket")
    assert result == ["backup1.tar.gz", "backup2.tar.gz"]


def test_remove_calls_remove_object():
    output = _make_output()
    mock_client = MagicMock()

    with patch("outputs.minio.Minio", return_value=mock_client):
        output.remove("backup.tar.gz")

    mock_client.remove_object.assert_called_once_with("test-bucket", "backup.tar.gz")
