import pytest

from outputs.factory import output_factory
from outputs.minio import MinioOutput
from outputs.dropbox import DropboxOutput


def test_minio_type_returns_minio_output():
    config = {
        "type": "minio",
        "minio": {
            "endpoint": "localhost:9000",
            "access_key": "key",
            "secret_key": "secret",
            "secure": False,
            "bucket_name": "backups",
        },
    }
    assert isinstance(output_factory(config), MinioOutput)


def test_dropbox_type_returns_dropbox_output():
    config = {
        "type": "dropbox",
        "dropbox": {
            "app_key": "key",
            "app_secret": "secret",
            "refresh_token": "token",
            "dest_folder": "/backups",
        },
    }
    assert isinstance(output_factory(config), DropboxOutput)


def test_unknown_type_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        output_factory({"type": "sftp"})
