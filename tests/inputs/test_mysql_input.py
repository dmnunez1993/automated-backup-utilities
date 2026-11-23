import os
from pathlib import Path
import tarfile
from unittest.mock import Mock, patch

import pytest

from app import _execute_backup
from backup import BackupHandler
from inputs.mysql import MySQLInput


@pytest.fixture
def mysql(tmp_path, monkeypatch):
    output_folder = tmp_path / "backup"
    output_folder.mkdir()
    monkeypatch.setattr("inputs.mysql.mkdtemp", lambda: str(output_folder))
    monkeypatch.setenv("PATH", str(tmp_path), prepend=os.pathsep)
    source = MySQLInput("daily", "localhost", 3306, "backup", 'test-$"password', "demo")
    return source, tmp_path / "mysqldump", output_folder


def write_mysqldump(executable, script):
    executable.write_text("#!/bin/sh\n" + script)
    executable.chmod(0o700)


def test_successful_dump_is_archived(mysql):
    source, executable, output_folder = mysql
    write_mysqldump(executable, "printf 'SELECT 1;\\n'\nprintf 'warning\\n' >&2\n")

    archive = Path(source.backup())

    assert list(output_folder.iterdir()) == [archive]
    with tarfile.open(archive) as backup:
        assert backup.getnames() == [archive.name.removesuffix(".tar.gz") + ".sql"]
        assert backup.extractfile(backup.getmembers()[0]).read() == b"SELECT 1;\n"


@pytest.mark.parametrize(("script", "message"), [
    ('printf "partial SQL\\n"\nprintf "Access denied: %s\\n" "$MYSQL_PWD" >&2\nexit 2\n',
     "with exit code 2: Access denied: [redacted]"),
    ("exit 0\n", "produced an empty SQL dump"),
])
def test_failed_dump_is_logged_without_upload_or_retention(mysql, caplog, script, message):
    source, executable, output_folder = mysql
    write_mysqldump(executable, script)
    output = Mock()
    handler = BackupHandler("daily", 3, source, [output])

    with patch.object(BackupHandler, "from_config", return_value=handler):
        _execute_backup({})

    assert message in caplog.text
    assert 'test-$"password' not in caplog.text
    assert not output_folder.exists()
    output.store.assert_not_called()
    output.list_files.assert_not_called()
