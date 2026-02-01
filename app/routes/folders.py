from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional

from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/folders", tags=["folders"])


class FolderCreate(BaseModel):
    name: str
    parent_folder_id: Optional[int] = None


class FolderRename(BaseModel):
    name: str


@router.post("")
def create_folder(req: FolderCreate, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO folders (name, user_id, parent_folder_id) VALUES (?, ?, ?)",
            (req.name, user_id, req.parent_folder_id),
        )
        folder_id = cursor.lastrowid
        return {"id": folder_id, "name": req.name, "parent_folder_id": req.parent_folder_id}


@router.get("/{folder_id}")
def get_folder(folder_id: int, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, parent_folder_id FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Folder not found")
        # list subfolders
        cursor.execute("SELECT id, name FROM folders WHERE parent_folder_id = ? AND user_id = ?", (folder_id, user_id))
        subfolders = [dict(id=r["id"], name=r["name"]) for r in cursor.fetchall()]
        # list files
        cursor.execute("SELECT id, name, size, mime_type FROM files WHERE parent_folder_id = ? AND user_id = ?", (folder_id, user_id))
        files = [dict(id=r["id"], name=r["name"], size=r["size"], mime_type=r["mime_type"]) for r in cursor.fetchall()]
        return {"id": row["id"], "name": row["name"], "parent_folder_id": row["parent_folder_id"], "subfolders": subfolders, "files": files}


@router.patch("/{folder_id}")
def rename_folder(folder_id: int, req: FolderRename, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Folder not found")
        cursor.execute("UPDATE folders SET name = ? WHERE id = ?", (req.name, folder_id))
        return {"id": folder_id, "name": req.name}


@router.delete("/{folder_id}")
def delete_folder(folder_id: int, user=Depends(get_current_user)):
    user_id = user["id"]
    with get_db() as conn:
        cursor = conn.cursor()
        # Check ownership
        cursor.execute("SELECT id FROM folders WHERE id = ? AND user_id = ?", (folder_id, user_id))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Folder not found")
        # Recursive delete: delete subfolders and files
        def recursive_delete(fid):
            cursor.execute("SELECT id FROM folders WHERE parent_folder_id = ? AND user_id = ?", (fid, user_id))
            for r in cursor.fetchall():
                recursive_delete(r["id"])
            cursor.execute("DELETE FROM files WHERE parent_folder_id = ? AND user_id = ?", (fid, user_id))
            cursor.execute("DELETE FROM folders WHERE id = ? AND user_id = ?", (fid, user_id))

        recursive_delete(folder_id)
        return {"detail": "Folder and its contents deleted (recursive)"}
