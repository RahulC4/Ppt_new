# ADD THIS FUNCTION AT END OF azure_blob_utils.py
def download_source_ppt_from_blob(blob_name: str, local_path: str):
    """
    Download a source PPT from ppt-dataset container to local path.
    """
    try:
        blob_service = BlobServiceClient.from_connection_string(BLOB_CONN)
        container_client = blob_service.get_container_client(SOURCE_CONTAINER)
        with open(local_path, "wb") as fp:
            stream = container_client.download_blob(blob_name)
            stream.readinto(fp)
        logger.info(f"Downloaded PPT {blob_name} -> {local_path}")
        return local_path
    except Exception as e:
        logger.exception(f"Failed downloading {blob_name}: {e}")
        raise
