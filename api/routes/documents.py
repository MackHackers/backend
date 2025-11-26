from fastapi import APIRouter, Depends, HTTPException, status
from schemas.documents import DocumentBase, DocumentOut, SearchQuery, SearchResponse
from core.security import get_current_user, require_role
from crud.documents import create_document, get_document, list_documents
from services.elasticService import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/create", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_doc(payload: DocumentBase, user = Depends(get_current_user), allowed = Depends(require_role("manager"))):
    creator = user["username"]
    doc = create_document(payload.model_dump(), creator)
    elastic_doc = await document_service.create_document(payload)
    print(elastic_doc)
    return doc



@router.get("/search")
async def simple_search(q: str, limit: int = 10, offset: int = 0, user = Depends(get_current_user), allowed = Depends(require_role("viewer"))):
    try:
        search_query = SearchQuery(query=q, size=limit, from_=offset)
        res = await document_service.search_documents(search_query)
        print(res)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e}",
        )
    
@router.get("/all")
async def list_docs(user = Depends(get_current_user), allowed = Depends(require_role("viewer"))):
    print("Listing documents for user:", user["username"])
    return list_documents()

@router.get("/", response_model=DocumentOut)
async def read_doc(doc_id: str, user = Depends(get_current_user), allowed = Depends(require_role("viewer"))):
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc