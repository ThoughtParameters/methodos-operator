from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse
from fastapi import Body

from app.models.agent import RegisterAgent

register_router = APIRouter(
  prefix='/register',
  tags=["Registration"],
  responses={404: {"description": "Not found"}},
)
@register_router.post(
  path='/',
  response_model=None,
  status_code=status.HTTP_200_OK,
  summary="Register agent",
  description="Register agent endpoint"
)
async def register_agent(agent: RegisterAgent = Body(...)):
  if agent.fqdn == "localhost" or agent.fqdn == "localhost.localdomain":
    raise HTTPException(status_code=404, detail="FQDN cannot be localhost.")
  
  # TODO: check if agent is already registered
  
  # TODO: Generate keypair for agent and save public/private key

  # TODO: Return registration data
  return JSONResponse(content={
    "message": "Agent registered successfully."
  },
  status_code=201)
  

