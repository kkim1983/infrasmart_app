import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings


class LocalStorage:
    def __init__(self, base_path: str = settings.STORAGE_LOCAL_PATH):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, file: UploadFile, folder: str = "") -> str:
        ext = Path(file.filename or "file").suffix
        filename = f"{uuid.uuid4()}{ext}"
        dest_dir = self.base_path / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        async with aiofiles.open(dest_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        return f"{folder}/{filename}" if folder else filename

    async def get_url(self, path: str) -> str:
        return f"{settings.BACKEND_URL}/files/{path}"

    async def delete(self, path: str) -> None:
        full_path = self.base_path / path
        if full_path.exists():
            full_path.unlink()


def get_storage() -> LocalStorage:
    return LocalStorage()
