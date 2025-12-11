# add to azure_blob_utils.py (append this function)
from azure.storage.blob import BlobServiceClient
from utils import get_env, logger
import os

def download_source_ppt_from_blob(blob_name: str, local_path: str):
    """
    Download a source PPT from SOURCE_CONTAINER to local_path.
    """
    try:
        blob_service = BlobServiceClient.from_connection_string(get_env("AZURE_BLOB_CONN", required=True))
        container_client = blob_service.get_container_client(SOURCE_CONTAINER)
        with open(local_path, "wb") as fp:
            stream = container_client.download_blob(blob_name)
            stream.readinto(fp)
        logger.info(f"Downloaded SOURCE PPT {blob_name} -> {local_path}")
        return local_path
    except Exception as e:
        logger.exception(f"Failed to download source ppt {blob_name}: {e}")
        raise
