from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse
from fastapi import Body

from app.models.agent import MethodosAgent

config_router = APIRouter(
    prefix='/config',
    tags=["Configuration"],
    responses={404: {"description": "Not found"}},
)

@config_router.post(
    path='/',
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Agent configuration",
    description="Methodos agent configuration endpoint"
)
async def agent_configuration(agent: MethodosAgent = Body(...)):
    """
    Returns a configuration for a Methodos agent.
    """
    if agent.fqdn == "localhost" or agent.fqdn == "localhost.localdomain":
        raise HTTPException(status_code=404, detail="FQDN cannot be localhost.")
    
    # TODO: check if agent is already registered

    # TODO: From agent type, return configuration
    if agent.type == "host":
        return JSONResponse(content=
            {
                "configuration": {
                    "books_url": "https://books.votra.io/",
                    "metrics_url": "https://metrics.votra.io/",
                    "logs_url": "https://logs.votra.io/",
                    "reporting_url": "https://reporting.votra.io/"
                },
                "serial_number": "0010000000000000",
                "environment": "dev",
                "version": "1.0.0",
            },  
            status_code=200,
        )
    
    elif agent.type == "docker":
        return JSONResponse(content=
            {
                "configuration": {
                    "books_url": "https://books.votra.io/",
                    "metrics_url": "https://metrics.votra.io/",
                    "logs_url": "https://logs.votra.io/",
                    "reporting_url": "https://reporting.votra.io/",
                },
                "serial_number": "0010000000000000",
                "environment": "dev",
                "version": "1.0.0",
            },
            status_code=200,
        )
            