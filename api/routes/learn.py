from fastapi import APIRouter, Depends, HTTPException, status
from schemas.documents import DocumentBase, DocumentOut
from core.security import get_current_user, require_role
from crud.learn import create_document, get_document, list_documents, update_document, delete_document
from services.elasticService import document_service

router = APIRouter(prefix="/learn", tags=["learn"])


@router.post("/create", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_doc(payload: DocumentBase, user = Depends(get_current_user), allowed = Depends(require_role("manager"))):
    creator = user["username"]
    doc = create_document(payload.model_dump(), creator)
    return doc

    
@router.get("/all")
async def list_docs(user = Depends(get_current_user), allowed = Depends(require_role("viewer"))):
    print("Listing documents for user:", user["username"])
    return list_documents()


@router.put("/update", response_model=DocumentOut)
async def read_doc(payload: DocumentBase, user = Depends(get_current_user), allowed = Depends(require_role("manager"))):
    doc = update_document(payload)
    if not doc:
        raise HTTPException(status_code=405, detail="Document not found")
    return doc

@router.get("/", response_model=DocumentOut)
async def read_doc(doc_id: str, user = Depends(get_current_user), allowed = Depends(require_role("viewer"))):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/", response_model=DocumentOut)
async def delete_doc(doc_id: str, user = Depends(get_current_user), allowed = Depends(require_role("manager"))):
    doc = delete_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
