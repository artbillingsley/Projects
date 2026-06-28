# src/lib/platforms/s3.py
from __future__ import annotations

import structlog

log = structlog.get_logger()


def upload_for_presigned_url(
    s3_client,
    bucket: str,
    file_path: str,
    object_key: str,
    expires_in: int = 900,
) -> str:
    log.info("s3.upload", bucket=bucket, key=object_key)

    s3_client.upload_file(file_path, bucket, object_key)

    url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=expires_in,
    )

    log.info("s3.presigned_url_generated", expires_in=expires_in)
    return url
