import logging
import os

import dropbox
from dropbox.files import WriteMode

from .base import BaseOutput


class DropboxOutput(BaseOutput):

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        access_token: str,
        dest_folder: str,
    ):
        self._app_key = app_key
        self._app_secret = app_secret
        self._access_token = access_token
        self._dest_folder = dest_folder.rstrip("/")
        self._logger = logging.getLogger("automated_backup_utilities")

    def _get_client(self):
        return dropbox.Dropbox(
            oauth2_access_token=self._access_token,
            app_key=self._app_key,
            app_secret=self._app_secret,
        )

    def store(
        self,
        name: str,
        file_path: str,
        content_type: str | None = None,
    ):
        self._logger.info("Uploading backup to Dropbox: %s", name)

        dest_path = f"{self._dest_folder}/{name}"
        client = self._get_client()

        file_size = os.path.getsize(file_path)
        chunk_size = 150 * 1024 * 1024    # 150 MB

        with open(file_path, "rb") as f:
            if file_size <= chunk_size:
                client.files_upload(
                    f.read(),
                    dest_path,
                    mode=WriteMode.overwrite,
                )
            else:
                session_start = client.files_upload_session_start(
                    f.read(chunk_size)
                )
                cursor = dropbox.files.UploadSessionCursor(
                    session_id=session_start.session_id,
                    offset=f.tell(),
                )
                commit = dropbox.files.CommitInfo(
                    path=dest_path,
                    mode=WriteMode.overwrite,
                )
                while f.tell() < file_size:
                    remaining = file_size - f.tell()
                    if remaining <= chunk_size:
                        client.files_upload_session_finish(
                            f.read(remaining),
                            cursor,
                            commit,
                        )
                    else:
                        client.files_upload_session_append_v2(
                            f.read(chunk_size),
                            cursor,
                        )
                        cursor.offset = f.tell()

        self._logger.info("Finished uploading backup to Dropbox: %s", name)

    def list_files(self) -> list:
        client = self._get_client()
        result = client.files_list_folder(self._dest_folder)
        return [entry.name for entry in result.entries]

    def remove(self, name: str):
        client = self._get_client()
        dest_path = f"{self._dest_folder}/{name}"
        self._logger.info("Removing object from Dropbox: %s", name)
        client.files_delete_v2(dest_path)
        self._logger.info("Finished removing object from Dropbox: %s", name)
