import asyncio
import json
from typing import Optional
from qcloud_cos import CosConfig, CosS3Client

from app.storage import BaseStorageAdapter


class TencentCOSAdapter(BaseStorageAdapter):

    def __init__(self, config: dict):
        self.secret_id = config.get("secret_id", "")
        self.secret_key = config.get("secret_key", "")
        self.bucket = config.get("bucket", "")
        self.region = config.get("region", "ap-guangzhou")
        self._client = None

    @property
    def provider_name(self) -> str:
        return "tencent"

    def _get_client(self) -> CosS3Client:
        if self._client is None:
            cos_config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
                Scheme="https",
            )
            self._client = CosS3Client(cos_config)
        return self._client

    def _get_url(self, key: str) -> str:
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"

    async def upload_file(self, data: bytes, key: str, content_type: Optional[str] = None) -> str:
        client = self._get_client()
        kwargs = {"Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        await asyncio.to_thread(
            client.put_object, Bucket=self.bucket, Key=key, **kwargs
        )
        return self._get_url(key)

    async def download_file(self, key: str) -> bytes:
        client = self._get_client()
        response = await asyncio.to_thread(
            client.get_object, Bucket=self.bucket, Key=key
        )
        return response["Body"].read()

    async def delete_file(self, key: str) -> bool:
        client = self._get_client()
        await asyncio.to_thread(
            client.delete_object, Bucket=self.bucket, Key=key
        )
        return True

    async def generate_url(self, key: str, expires: int = 3600) -> str:
        client = self._get_client()
        url = await asyncio.to_thread(
            client.get_presigned_url,
            Method="GET",
            Bucket=self.bucket,
            Key=key,
            Expires=expires,
        )
        return url

    async def test_connection(self) -> bool:
        try:
            client = self._get_client()
            await asyncio.to_thread(client.head_bucket, Bucket=self.bucket)
            return True
        except Exception:
            return False
