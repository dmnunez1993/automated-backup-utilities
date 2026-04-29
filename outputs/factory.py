from typing import Dict, Any

from .dropbox import DropboxOutput
from .minio import MinioOutput
from .types import DROPBOX_OUTPUT_TYPE, MINIO_OUTPUT_TYPE


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

    raise NotImplementedError(f"Output of type '{output_type}' not implemented")
