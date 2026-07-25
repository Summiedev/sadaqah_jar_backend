"""File storage provider interface for Mizan.

Future domains may upload avatars, family covers, attachments, and documents.
This module defines the provider contract. Cloud integration is not implemented yet.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class StoredFile:
    key: str
    url: str
    content_type: str
    size: int


class StorageProvider(ABC):
    @abstractmethod
    def upload(self, key: str, data: BinaryIO, content_type: str) -> StoredFile:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_url(self, key: str) -> str:
        raise NotImplementedError


class NullStorageProvider(StorageProvider):
    def upload(self, key: str, data: BinaryIO, content_type: str) -> StoredFile:
        raise NotImplementedError("Storage provider not configured")

    def delete(self, key: str) -> None:
        pass

    def get_url(self, key: str) -> str:
        return ""


storage_provider: StorageProvider = NullStorageProvider()
