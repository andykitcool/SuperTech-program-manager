from abc import ABC, abstractmethod
from typing import Optional


class BaseStorageAdapter(ABC):
    """Abstract base class for cloud storage adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def upload_file(self, data: bytes, key: str, content_type: Optional[str] = None) -> str:
        """Upload file and return public URL."""
        pass

    @abstractmethod
    async def download_file(self, key: str) -> bytes:
        """Download file by key."""
        pass

    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """Delete file by key."""
        pass

    async def move_file(self, src_key: str, dest_key: str) -> bool:
        """Move/rename a file. Default: copy + delete. Override for native support."""
        data = await self.download_file(src_key)
        await self.upload_file(data, dest_key)
        await self.delete_file(src_key)
        return True

    @abstractmethod
    async def generate_url(self, key: str, expires: int = 3600) -> str:
        """Generate a signed URL for the file."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the storage connection is valid."""
        pass

    def generate_upload_token(self, key: str, expires: int = 3600) -> str:
        """Generate an upload token for client-side direct upload. Return '' if not supported."""
        return ""

    def build_url(self, key: str) -> str:
        """Build a public URL for a given storage key. Override in subclass if needed."""
        return ""

    def get_video_thumbnail_url(self, video_url: str) -> Optional[str]:
        """Generate a thumbnail/snapshot URL for a video. Return None if not supported."""
        return None
