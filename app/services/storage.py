"""S3-compatible object storage service.

Supports MinIO, AWS S3, and any S3-compatible backend.
Configuration is read from environment variables.
"""

import os
import logging
from typing import BinaryIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Create and return an S3 client from environment configuration."""
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL", ""),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY", ""),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY", ""),
        region_name=os.getenv("S3_REGION", "us-east-1"),
        use_ssl=os.getenv("S3_USE_SSL", "false").lower() == "true",
    )


def _get_bucket() -> str:
    bucket = os.getenv("S3_BUCKET", "")
    if not bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="S3_BUCKET is not configured",
        )
    return bucket


def upload_file(
    bucket: str,
    key: str,
    data: BinaryIO,
    content_type: str,
    max_size_bytes: int = 25 * 1024 * 1024,
) -> str:
    """Upload a file to S3-compatible storage.

    Returns the object key (not a full URL).
    """
    s3 = _get_s3_client()
    bucket = bucket or _get_bucket()

    content = data.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of {max_size_bytes // (1024 * 1024)} MB",
        )

    try:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
    except ClientError as exc:
        logger.warning("S3 upload failed for key %s: %s", key, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload file",
        ) from exc
    except BotoCoreError as exc:
        logger.warning("S3 client upload error for key %s: %s", key, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage service unavailable",
        ) from exc

    return key


def delete_file(bucket: str, key: str) -> None:
    """Delete a file from S3-compatible storage."""
    s3 = _get_s3_client()
    bucket = bucket or _get_bucket()

    try:
        s3.delete_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "NoSuchKey":
            logger.warning("S3 delete failed for key %s: %s", key, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to delete file",
            ) from exc
    except BotoCoreError as exc:
        logger.warning("S3 client delete error for key %s: %s", key, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage service unavailable",
        ) from exc


def get_presigned_url(bucket: str, key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading a file."""
    s3 = _get_s3_client()
    bucket = bucket or _get_bucket()

    try:
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except (ClientError, BotoCoreError) as exc:
        logger.warning("S3 presign failed for key %s: %s", key, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate download URL",
        ) from exc


def file_exists(bucket: str, key: str) -> bool:
    """Check if a file exists in S3-compatible storage."""
    s3 = _get_s3_client()
    bucket = bucket or _get_bucket()

    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in ("NoSuchKey", "404"):
            return False
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage service unavailable",
        ) from exc
    except BotoCoreError as exc:
        logger.warning("S3 client head error for key %s: %s", key, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage service unavailable",
        ) from exc
