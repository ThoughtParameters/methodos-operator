import os

from fastapi import FastAPI
from app.routes.config import config_router
from app.routes.register import register_router
from app.routes.books import books_router

from sqlmodel import Session, select

from app import TMP_DIR, BOOKS_DIR, INDEX_FILE, create_dirs, load_index, save_index
from app.database import init_db, engine

import uvicorn
import pytz

application = FastAPI(
    title="Methodos Operator Server",
    description="Methodos Operator Server API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Team Methodos",
        "url": "https://www.thoughtparameters.com",
        "email": "jason.miller@thoughtparameters.com",      
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

application.include_router(config_router)
application.include_router(register_router)
application.include_router(books_router)

@application.on_event("startup")
async def on_startup():
    start_time = datetime.datetime.now()
    print("Starting Methodos Operator...")
    print(f"Books will be stored in: {os.path.abspath(BOOKS_DIR)}")
    print(f"Index file: {os.path.abspath(INDEX_FILE)}")

    print("Initializing database...")
    init_db()
    print("Creating directories if they don't exist...")
    create_dirs()
    print(f"Loading Book index from file ({os.path.abspath(INDEX_FILE)}...")
    await load_index()
    print("Startup complete.")

@application.on_event("shutdown")
async def on_shutdown():
    print("Shutdown complete.")

if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", port=8000)