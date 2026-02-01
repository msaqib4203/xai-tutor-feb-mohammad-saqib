from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import base64
import mimetypes

from app.auth import get_current_user
from app.database import get_db
import sqlite3

router = APIRouter(prefix="/files", tags=["files"])


class FileUpload(BaseModel):
    name: str
    content: str  # base64 encoded
    parent_folder_id: Optional[int] = None


class FileRename(BaseModel):
    name: str


@router.post("")
def upload_file(req: FileUpload, user=Depends(get_current_user)):
    user_id = user["id"]
    try:
        decoded = base64.b64decode(req.content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 content")
    size = len(decoded)
    mime_type, _ = mimetypes.guess_type(req.name)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO files (name, content, size, mime_type, user_id, parent_folder_id) VALUES (?, ?, ?, ?, ?, ?)",
            (req.name, sqlite3.Binary(decoded), size, mime_type, user_id, req.parent_folder_id),
        )
        file_id = cursor.lastrowid
        return {"id": file_id, "name": req.name, "size": size, "mime_type": mime_type}


@router.get("/{file_id}")
def get_file_metadata(file_id: int, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, size, mime_type FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="File not found")
        return {"id": row["id"], "name": row["name"], "size": row["size"], "mime_type": row["mime_type"]}


@router.get("/{file_id}/download")
def download_file(file_id: int, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, content, mime_type FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="File not found")
        content_b64 = base64.b64encode(row["content"]).decode("utf-8")
        return {"name": row["name"], "mime_type": row["mime_type"], "content": content_b64}


@router.patch("/{file_id}")
def rename_file(file_id: int, req: FileRename, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="File not found")
        cursor.execute("UPDATE files SET name = ? WHERE id = ?", (req.name, file_id))
        return {"id": file_id, "name": req.name}


@router.delete("/{file_id}")
def delete_file(file_id: int, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="File not found")
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        return {"detail": "File deleted"}


@router.post("/{file_id}/move")
def move_file(file_id: int, parent_folder_id: Optional[int] = None, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM files WHERE id = ? AND user_id = ?", (file_id, user_id))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="File not found")
        # if parent_folder_id is provided, ensure it belongs to the user
        if parent_folder_id is not None:
            cursor.execute("SELECT id FROM folders WHERE id = ? AND user_id = ?", (parent_folder_id, user_id))
            if cursor.fetchone() is None:
                raise HTTPException(status_code=400, detail="Destination folder not found")
        cursor.execute("UPDATE files SET parent_folder_id = ? WHERE id = ?", (parent_folder_id, file_id))
        return {"id": file_id, "parent_folder_id": parent_folder_id}
