from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse
from fastapi import Body

from app.models.agent import MethodosAgent


config_router = APIRouter(
    prefix='/config',
    tags="Configuration",
    responses={404: {"description": "Not found"}},
)

@config_router.post(
    '/',
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Agent configuration",
    description="Methodos agent configuration endpoint"
)
def agent_configuration(agent: MethodosAgent = Body(...)):
    """
    Returns a configuration for a Methodos agent.
    """
    if agent.fqdn == "localhost" or agent.fqdn == "localhost.localdomain":
        raise HTTPException(status_code=404, detail="FQDN cannot be localhost.")
    
    return JSONResponse(content=AgentConfiguration, status_code=200)
            