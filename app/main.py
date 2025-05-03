from fastapi import FastAPI

import uvicorn

application = FastAPI()

@application.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    uvicorn.run(application, host="0.0.0.0", port=8000)