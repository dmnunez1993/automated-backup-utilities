import os
import tempfile
from unittest.mock import MagicMock, patch

from outputs.dropbox import DropboxOutput


def _make_output():
    return DropboxOutput(
        app_key="app_key",
        app_secret="app_secret",
        refresh_token="refresh_token",
        dest_folder="/backups",
    )


def test_store_small_file_calls_files_upload():
    output = _make_output()
    mock_client = MagicMock()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"backup content")
        tmp_path = f.name

    try:
        with patch.object(output, "_get_client", return_value=mock_client):
            output.store("backup.tar.gz", tmp_path)

        mock_client.files_upload.assert_called_once()
        call_args = mock_client.files_upload.call_args
        assert call_args[0][1] == "/backups/backup.tar.gz"
    finally:
        os.unlink(tmp_path)


def test_store_large_file_uses_upload_session():
    output = _make_output()
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.session_id = "session-abc"
    mock_client.files_upload_session_start.return_value = mock_session

    chunk_size = 150 * 1024 * 1024
    file_size = chunk_size + 100

    # tell() values: offset arg, while check #1, remaining calc, while check #2 (exit)
    tell_iter = iter([chunk_size, chunk_size, chunk_size, file_size])
    mock_file = MagicMock()
    mock_file.read.return_value = b"data"
    mock_file.tell.side_effect = lambda: next(tell_iter, file_size)
    mock_file.__enter__ = lambda s: s
    mock_file.__exit__ = MagicMock(return_value=False)

    with patch.object(output, "_get_client", return_value=mock_client), \
         patch("outputs.dropbox.dropbox"), \
         patch("outputs.dropbox.os.path.getsize", return_value=file_size), \
         patch("builtins.open", return_value=mock_file):
        output.store("big_backup.tar.gz", "/fake/big.tar.gz")

    mock_client.files_upload_session_start.assert_called_once()
    mock_client.files_upload_session_finish.assert_called_once()
    mock_client.files_upload.assert_not_called()


def test_store_dest_path_uses_dest_folder():
    output = _make_output()
    mock_client = MagicMock()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"data")
        tmp_path = f.name

    try:
        with patch.object(output, "_get_client", return_value=mock_client):
            output.store("myfile.tar.gz", tmp_path)

        call_args = mock_client.files_upload.call_args
        assert call_args[0][1] == "/backups/myfile.tar.gz"
    finally:
        os.unlink(tmp_path)


def test_list_files_returns_entry_names():
    output = _make_output()
    mock_client = MagicMock()
    entry1, entry2 = MagicMock(), MagicMock()
    entry1.name = "backup1.tar.gz"
    entry2.name = "backup2.tar.gz"
    mock_client.files_list_folder.return_value.entries = [entry1, entry2]

    with patch.object(output, "_get_client", return_value=mock_client):
        result = output.list_files()

    mock_client.files_list_folder.assert_called_once_with("/backups")
    assert result == ["backup1.tar.gz", "backup2.tar.gz"]


def test_remove_calls_files_delete_with_full_path():
    output = _make_output()
    mock_client = MagicMock()

    with patch.object(output, "_get_client", return_value=mock_client):
        output.remove("backup.tar.gz")

    mock_client.files_delete_v2.assert_called_once_with(
        "/backups/backup.tar.gz")


def test_dest_folder_trailing_slash_is_normalized():
    output = DropboxOutput(
        app_key="k",
        app_secret="s",
        refresh_token="t",
        dest_folder="/backups/",
    )
    mock_client = MagicMock()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"data")
        tmp_path = f.name

    try:
        with patch.object(output, "_get_client", return_value=mock_client):
            output.store("file.tar.gz", tmp_path)

        call_args = mock_client.files_upload.call_args
        assert call_args[0][1] == "/backups/file.tar.gz"
    finally:
        os.unlink(tmp_path)
