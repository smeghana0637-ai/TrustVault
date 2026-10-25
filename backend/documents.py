
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Document, AuditLog
from backend.main import current_user

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    content = await file.read(10 * 1024 * 1024 + 1)

    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB")

    stored_name = f"{uuid.uuid4().hex}.bin"
    file_path = UPLOAD_DIR / stored_name
    file_path.write_bytes(content)

    document = Document(
        filename=Path(file.filename).name,
        file_path=str(file_path),
        owner_id=user.id,
    )
    db.add(document)
    db.flush()

    db.add(AuditLog(
        user_id=user.id,
        document_id=document.id,
        action="UPLOAD",
    ))

    db.commit()
    db.refresh(document)

    return {
        "message": "Upload successful",
        "document_id": document.id,
        "filename": document.filename,
    }


@router.get("")
def list_my_documents(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    documents = (
        db.query(Document)
        .filter(Document.owner_id == user.id)
        .all()
    )

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "created_at": doc.created_at,
        }
        for doc in documents
    ]


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == user.id,
        )
        .first()
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(document.file_path)

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")

    db.add(AuditLog(
        user_id=user.id,
        document_id=document.id,
        action="DOWNLOAD",
    ))
    db.commit()

    return FileResponse(
        path=file_path,
        filename=document.filename,
        media_type="application/octet-stream",
    )
