from datetime import datetime, timezone
import logging
import os
import shutil
import subprocess
import tarfile
from tempfile import mkdtemp

from .base import BaseInput


class MySQLInput(BaseInput):

    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        database_name: str,
    ):
        super().__init__(name)
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._database_name = database_name
        self._logger = logging.getLogger("automated_backup_utilities")

    def backup(self) -> str:
        name = self.get_name()

        self._logger.info(
            "Backing up MySQL database with name: %s",
            self._database_name,
        )

        output_folder = mkdtemp()
        now = datetime.now(timezone.utc)
        now_str = now.strftime("%Y-%m-%d_%H:%M:%S")

        filename_sql = f"{name}_{now_str}.sql"
        output_path_sql = os.path.join(output_folder, filename_sql)
        filename_tar_gz = f"{name}_{now_str}.tar.gz"
        output_path_tar_gz = os.path.join(output_folder, filename_tar_gz)

        command = ["mysqldump", f"--host={self._host}", f"--port={self._port}",
                   f"--user={self._username}", "--", str(self._database_name)]
        password = str(self._password)
        try:
            with open(output_path_sql, "wb") as sql_dump:
                result = subprocess.run(command, stdout=sql_dump, stderr=subprocess.PIPE,
                                        env=dict(os.environ, MYSQL_PWD=password))

            if result.returncode != 0:
                error = result.stderr.decode(errors="replace").strip()
                if password:
                    error = error.replace(password, "[redacted]")
                raise RuntimeError(
                    f"mysqldump failed for {name} ({self._database_name}) "
                    f"with exit code {result.returncode}: {error or 'no error output'}"
                )
            if os.path.getsize(output_path_sql) == 0:
                raise RuntimeError(f"mysqldump produced an empty SQL dump for {name} ({self._database_name})")

            with tarfile.open(output_path_tar_gz, "w:gz") as archive:
                archive.add(output_path_sql, arcname=filename_sql)
            os.remove(output_path_sql)
        except BaseException:
            shutil.rmtree(output_folder, ignore_errors=True)
            raise

        self._logger.info(
            "Finished Backing up MySQL database: %s",
            self._database_name,
        )

        return output_path_tar_gz
