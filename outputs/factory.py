from typing import Dict, Any

from .dropbox import DropboxOutput
from .minio import MinioOutput
from .onedrive import OneDriveOutput
from .types import DROPBOX_OUTPUT_TYPE, MINIO_OUTPUT_TYPE, ONEDRIVE_OUTPUT_TYPE


def output_factory(config: Dict[str, Any]):
    output_type = config["type"]
    if output_type == MINIO_OUTPUT_TYPE:
        return MinioOutput(
            endpoint=config["minio"]["endpoint"],
            access_key=config["minio"]["access_key"],
            secret_key=config["minio"]["secret_key"],
            secure=config["minio"]["secure"],
            bucket_name=config["minio"]["bucket_name"],
        )

    if output_type == DROPBOX_OUTPUT_TYPE:
        return DropboxOutput(
            app_key=config["dropbox"]["app_key"],
            app_secret=config["dropbox"]["app_secret"],
            access_token=config["dropbox"]["access_token"],
            dest_folder=config["dropbox"]["dest_folder"],
        )

    if output_type == ONEDRIVE_OUTPUT_TYPE:
        return OneDriveOutput(
            client_id=config["onedrive"]["client_id"],
            client_secret=config["onedrive"]["client_secret"],
            tenant_id=config["onedrive"]["tenant_id"],
            refresh_token=config["onedrive"]["refresh_token"],
            dest_folder=config["onedrive"]["dest_folder"],
        )

    raise NotImplementedError(f"Output of type '{output_type}' not implemented")
