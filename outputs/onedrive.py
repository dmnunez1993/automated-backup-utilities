import logging
import os

import msal
import requests

from .base import BaseOutput

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPES = ["https://graph.microsoft.com/Files.ReadWrite"]
UPLOAD_SESSION_CHUNK_SIZE = 10 * 1024 * 1024    # 10 MB
SMALL_FILE_THRESHOLD = 4 * 1024 * 1024    # 4 MB


class OneDriveOutput(BaseOutput):

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        refresh_token: str,
        dest_folder: str,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._tenant_id = tenant_id
        self._refresh_token = refresh_token
        self._dest_folder = dest_folder.strip("/")
        self._logger = logging.getLogger("automated_backup_utilities")

    def _get_access_token(self) -> str:
        app = msal.ConfidentialClientApplication(
            self._client_id,
            authority=f"https://login.microsoftonline.com/{self._tenant_id}",
            client_credential=self._client_secret,
        )
        result = app.acquire_token_by_refresh_token(
            self._refresh_token,
            scopes=GRAPH_SCOPES,
        )
        if "access_token" not in result:
            error = result.get("error_description"
                              ) or result.get("error") or str(result)
            raise RuntimeError(
                f"Failed to acquire OneDrive access token: {error}"
            )
        return result["access_token"]

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    def store(
        self,
        name: str,
        file_path: str,
        content_type: str | None = None,
    ):
        self._logger.info("Uploading backup to OneDrive: %s", name)

        dest_path = f"{self._dest_folder}/{name}"
        file_size = os.path.getsize(file_path)
        headers = self._auth_headers()

        if file_size <= SMALL_FILE_THRESHOLD:
            self._upload_small(headers, dest_path, file_path)
        else:
            self._upload_large(headers, dest_path, file_path, file_size)

        self._logger.info("Finished uploading backup to OneDrive: %s", name)

    def _upload_small(self, headers: dict, dest_path: str, file_path: str):
        url = f"{GRAPH_BASE_URL}/me/drive/root:/{dest_path}:/content"
        with open(file_path, "rb") as f:
            resp = requests.put(url, headers=headers, data=f, timeout=3000)
        resp.raise_for_status()

    def _upload_large(
        self,
        headers: dict,
        dest_path: str,
        file_path: str,
        file_size: int
    ):
        session_url = f"{GRAPH_BASE_URL}/me/drive/root:/{dest_path}:/createUploadSession"
        session_resp = requests.post(
            session_url,
            headers=headers,
            json={"item": {
                "@microsoft.graph.conflictBehavior": "replace"
            }},
            timeout=3000,
        )
        session_resp.raise_for_status()
        upload_url = session_resp.json()["uploadUrl"]

        with open(file_path, "rb") as f:
            offset = 0
            while True:
                chunk = f.read(UPLOAD_SESSION_CHUNK_SIZE)
                if not chunk:
                    break
                chunk_len = len(chunk)
                end = offset + chunk_len - 1
                chunk_headers = {
                    "Content-Length": str(chunk_len),
                    "Content-Range": f"bytes {offset}-{end}/{file_size}",
                }
                resp = requests.put(
                    upload_url,
                    headers=chunk_headers,
                    data=chunk,
                    timeout=3000,
                )
                if resp.status_code not in (200, 201, 202):
                    resp.raise_for_status()
                offset += chunk_len

    def list_files(self) -> list:
        headers = self._auth_headers()
        url = f"{GRAPH_BASE_URL}/me/drive/root:/{self._dest_folder}:/children"
        resp = requests.get(url, headers=headers, timeout=3000)
        resp.raise_for_status()
        return [item["name"] for item in resp.json().get("value", [])]

    def remove(self, name: str):
        self._logger.info("Removing object from OneDrive: %s", name)
        headers = self._auth_headers()
        dest_path = f"{self._dest_folder}/{name}"

        # Resolve item ID then delete — avoids issues with special chars in path
        item_resp = requests.get(
            f"{GRAPH_BASE_URL}/me/drive/root:/{dest_path}",
            headers=headers,
            timeout=3000,
        )
        item_resp.raise_for_status()
        item_id = item_resp.json()["id"]

        delete_resp = requests.delete(
            f"{GRAPH_BASE_URL}/me/drive/items/{item_id}",
            headers=headers,
            timeout=3000,
        )
        delete_resp.raise_for_status()
        self._logger.info("Finished removing object from OneDrive: %s", name)
