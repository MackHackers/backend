from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.db import es_client
from routes import auth, protected_example
from elasticService import document_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await document_service.create_index()
    except:
        raise "blaut"
    yield

    await es_client.close()

app = FastAPI(title="mcHackersApi", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(protected_example.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)