from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.model_client import AgentModelCallError, AgentModelClient, AgentModelConfigError, get_model_status
from app.agent.prompts import AGENT_SYSTEM_PROMPT, SIMPLE_REPLY_JSON_PROMPT
from app.agent.schemas import AgentModelStatusResponse, AgentModelTestRequest, AgentModelTestResponse, SimpleAgentReply
from app.core.security import CurrentUser, get_optional_current_user
from app.db.session import get_db
from app.schemas.agent import AgentChatRequest, AgentChatResponse
from app.services.agent_service import chat as chat_service

router = APIRouter()


@router.post("/chat", response_model=AgentChatResponse)
def chat(
    payload: AgentChatRequest,
    current_user: CurrentUser | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> AgentChatResponse:
    response = chat_service(db, payload, current_user)
    return AgentChatResponse(**response)


@router.get("/model-status", response_model=AgentModelStatusResponse)
def model_status() -> AgentModelStatusResponse:
    return AgentModelStatusResponse(**get_model_status())


@router.post("/model-test", response_model=AgentModelTestResponse)
def model_test(payload: AgentModelTestRequest) -> AgentModelTestResponse:
    try:
        client = AgentModelClient()
        if payload.json_mode:
            result = client.invoke_json(
                SIMPLE_REPLY_JSON_PROMPT.format(message=payload.message),
                SimpleAgentReply,
                model_role=payload.model_role,
            )
            return AgentModelTestResponse(
                model=result.model,
                model_role=result.model_role,
                content=result.content,
                parsed=SimpleAgentReply.model_validate(result.parsed),
                token_usage=result.token_usage,
                attempts=result.attempts,
                fallback_used=result.fallback_used,
            )

        result = client.invoke(
            [
                {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                {"role": "user", "content": payload.message},
            ],
            model_role=payload.model_role,
        )
        return AgentModelTestResponse(
            model=result.model,
            model_role=result.model_role,
            content=result.content,
            token_usage=result.token_usage,
        )
    except AgentModelConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AgentModelCallError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
