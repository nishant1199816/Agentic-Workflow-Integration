"""
agents/s3_ingestor.py
---------------------
Tool 1: AWS S3 se data padhna.

Real use mein: boto3 se actual S3 bucket access hoga.
Demo/testing mein: local mock_data/ folder se padh lenge.

S3 kya hota hai?
  - Amazon ka cloud storage service
  - Files ko "objects" bolte hain, folders ko "buckets"
  - Jaise Google Drive, but for servers/code
"""

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from utils.logger import get_logger

logger = get_logger("s3_ingestor")


class S3Ingestor:
    """
    S3 se files ki list aur content padhta hai.
    Agar AWS credentials nahi hain toh automatically local mock mode use karta hai.
    """

    def __init__(self, bucket_name: str, mock_mode: bool = False):
        self.bucket_name = bucket_name
        self.mock_mode = mock_mode
        self.mock_dir = "mock_data"  # local folder for demo

        if not mock_mode:
            try:
                # boto3 automatically ~/.aws/credentials ya ENV vars se credentials lega
                self.s3_client = boto3.client("s3")
                logger.info(f"🪣 S3 client initialized for bucket: {bucket_name}")
            except NoCredentialsError:
                logger.warning("⚠️  No AWS credentials found. Switching to mock mode.")
                self.mock_mode = True
        else:
            logger.info("🧪 Running in MOCK mode (using local mock_data/ folder)")

    def list_files(self) -> list[str]:
        """
        Bucket mein saari files ki list return karta hai.

        Real S3 mein: paginator use karta hai (agar 1000+ files hain)
        Mock mode mein: local folder ke files return karta hai
        """
        if self.mock_mode:
            files = [f for f in os.listdir(self.mock_dir) if f.endswith((".txt", ".json"))]
            logger.info(f"📂 Found {len(files)} files in mock_data/: {files}")
            return files

        try:
            # S3 ek baar mein max 1000 objects return karta hai
            # Paginator use karte hain unlimited files ke liye
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket_name)

            all_keys = []
            for page in pages:
                for obj in page.get("Contents", []):
                    all_keys.append(obj["Key"])

            logger.info(f"📂 Found {len(all_keys)} files in S3 bucket '{self.bucket_name}'")
            return all_keys

        except ClientError as e:
            logger.error(f"❌ S3 list error: {e}")
            raise

    def read_file(self, file_key: str) -> str:
        """
        Ek specific file ka content string mein return karta hai.

        file_key: S3 mein file ka path (jaise "customers/rahul.txt")
        """
        if self.mock_mode:
            file_path = os.path.join(self.mock_dir, file_key)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.info(f"📄 Read mock file: {file_key} ({len(content)} chars)")
            return content

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            # Body ek stream hota hai, isliye .read().decode() karna padta hai
            content = response["Body"].read().decode("utf-8")
            logger.info(f"📄 Read S3 file: {file_key} ({len(content)} chars)")
            return content

        except ClientError as e:
            logger.error(f"❌ Failed to read '{file_key}' from S3: {e}")
            raise
