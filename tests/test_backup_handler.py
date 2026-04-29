from unittest.mock import MagicMock, patch

from backup import BackupHandler


def _make_handler(name="mybackup", max_backups=3, outputs=None):
    mock_input = MagicMock()
    mock_outputs = outputs if outputs is not None else [MagicMock()]
    return BackupHandler(name, max_backups, mock_input,
                         mock_outputs), mock_input, mock_outputs


def test_backup_calls_store_with_filename_and_path():
    handler, mock_input, mock_outputs = _make_handler()
    mock_input.backup.return_value = "/tmp/dir/mybackup_2024-01-01_00:00:00.tar.gz"

    with patch("backup.os.remove"):
        handler.backup()

    mock_outputs[0].store.assert_called_once_with(
        "mybackup_2024-01-01_00:00:00.tar.gz",
        "/tmp/dir/mybackup_2024-01-01_00:00:00.tar.gz",
    )


def test_backup_removes_temp_file_after_upload():
    handler, mock_input, _ = _make_handler()
    mock_input.backup.return_value = "/tmp/dir/mybackup_file.tar.gz"

    with patch("backup.os.remove") as mock_remove:
        handler.backup()

    mock_remove.assert_called_once_with("/tmp/dir/mybackup_file.tar.gz")


def test_backup_stores_to_all_outputs():
    mock_out1 = MagicMock()
    mock_out2 = MagicMock()
    handler, mock_input, _ = _make_handler(outputs=[mock_out1, mock_out2])
    mock_input.backup.return_value = "/tmp/dir/mybackup_file.tar.gz"

    with patch("backup.os.remove"):
        handler.backup()

    mock_out1.store.assert_called_once()
    mock_out2.store.assert_called_once()


def test_clean_removes_oldest_files_over_limit():
    handler, _, mock_outputs = _make_handler(max_backups=2)
    mock_outputs[0].list_files.return_value = [
        "mybackup_2024-01-03.tar.gz",
        "mybackup_2024-01-01.tar.gz",
        "mybackup_2024-01-02.tar.gz",
        "other_backup_2024-01-01.tar.gz",    # different prefix, must be ignored
    ]

    handler.clean_previous_backups()

    mock_outputs[0].remove.assert_called_once_with("mybackup_2024-01-01.tar.gz")


def test_clean_keeps_all_files_when_under_limit():
    handler, _, mock_outputs = _make_handler(max_backups=5)
    mock_outputs[0].list_files.return_value = [
        "mybackup_2024-01-02.tar.gz",
        "mybackup_2024-01-01.tar.gz",
    ]

    handler.clean_previous_backups()

    mock_outputs[0].remove.assert_not_called()


def test_clean_enforces_limit_across_all_outputs():
    mock_out1 = MagicMock()
    mock_out2 = MagicMock()
    mock_out1.list_files.return_value = [
        "mybackup_c.tar.gz", "mybackup_b.tar.gz", "mybackup_a.tar.gz"
    ]
    mock_out2.list_files.return_value = [
        "mybackup_c.tar.gz", "mybackup_b.tar.gz", "mybackup_a.tar.gz"
    ]
    handler, _, _ = _make_handler(max_backups=2, outputs=[mock_out1, mock_out2])

    handler.clean_previous_backups()

    mock_out1.remove.assert_called_once_with("mybackup_a.tar.gz")
    mock_out2.remove.assert_called_once_with("mybackup_a.tar.gz")


def test_from_config_constructs_handler():
    config = {
        "name": "test_backup",
        "max_backups_stored": 2,
        "type": "local",
        "local": {
            "path": "/some/path"
        },
        "outputs": [{
            "type": "minio",
            "minio": {}
        }],
    }
    mock_input = MagicMock()
    mock_output = MagicMock()

    with patch("backup.input_factory", return_value=mock_input), \
         patch("backup.output_factory", return_value=mock_output):
        handler = BackupHandler.from_config(config)

    assert isinstance(handler, BackupHandler)
    assert handler._name == "test_backup"
    assert handler._max_backups_stored == 2
    assert handler._data_input is mock_input
    assert mock_output in handler._data_outputs
