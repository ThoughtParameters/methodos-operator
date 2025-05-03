from fastapi import FastAPI
from app.routes.config import config_router
from app.routes.register import register_router

import uvicorn

application = FastAPI()

application.include_router(config_router)
application.include_router(register_router)

if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", port=8000)