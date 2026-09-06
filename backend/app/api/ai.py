"""AI endpoints: grounded chat and structured code generation. Login required."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import chat as chat_service
from app.ai.tools import ToolError, generate_code_cirq, generate_code_qiskit
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.ai import ChatIn, ChatOut, CodeGenIn, CodeGenOut

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatOut)
def chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatOut:
    result = chat_service.answer(
        db,
        user,
        message=payload.message,
        circuit_ir=payload.circuit_ir,
        job_id=payload.job_id,
        history=payload.history,
    )
    return ChatOut(**result)


@router.post("/generate_code", response_model=CodeGenOut)
def generate_code(
    payload: CodeGenIn,
    user: User = Depends(get_current_user),
) -> CodeGenOut:
    framework = payload.framework.lower().strip()
    if framework not in {"qiskit", "cirq"}:
        raise HTTPException(status_code=400, detail="framework must be 'qiskit' or 'cirq'")
    try:
        generator = generate_code_qiskit if framework == "qiskit" else generate_code_cirq
        result = generator(payload.circuit_ir, payload.shots)
    except ToolError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CodeGenOut(**result)
