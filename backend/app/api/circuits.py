"""Saved circuits / projects."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.circuit import SavedCircuit
from app.models.user import User
from app.quantum.ir import CircuitIR
from app.quantum.qasm3_codec import to_qasm3
from app.schemas.circuit import CircuitIn, CircuitOut

router = APIRouter(prefix="/circuits", tags=["circuits"])


@router.get("", response_model=list[CircuitOut])
def list_circuits(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CircuitOut]:
    rows = db.scalars(
        select(SavedCircuit)
        .where(SavedCircuit.user_id == user.id)
        .order_by(desc(SavedCircuit.updated_at))
    ).all()
    return [_out(r) for r in rows]


@router.post("", response_model=CircuitOut, status_code=201)
def save_circuit(
    payload: CircuitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CircuitOut:
    ir = _parse(payload.circuit_ir)
    existing = db.scalar(
        select(SavedCircuit).where(
            SavedCircuit.user_id == user.id, SavedCircuit.name == payload.name
        )
    )
    if existing is not None:
        existing.circuit_ir = ir.to_dict()
        existing.qasm3 = to_qasm3(ir)
        existing.is_dynamic = ir.is_dynamic()
        existing.description = payload.description
        db.commit()
        db.refresh(existing)
        return _out(existing)

    row = SavedCircuit(
        user_id=user.id,
        name=payload.name,
        description=payload.description,
        circuit_ir=ir.to_dict(),
        qasm3=to_qasm3(ir),
        is_dynamic=ir.is_dynamic(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.get("/{circuit_id}", response_model=CircuitOut)
def get_circuit(
    circuit_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CircuitOut:
    row = db.get(SavedCircuit, circuit_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Circuit not found")
    return _out(row)


@router.delete("/{circuit_id}", status_code=204)
def delete_circuit(
    circuit_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    row = db.get(SavedCircuit, circuit_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Circuit not found")
    db.delete(row)
    db.commit()


def _parse(data: dict[str, Any]) -> CircuitIR:
    try:
        return CircuitIR.from_dict(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Invalid circuit: {exc}") from exc


def _out(row: SavedCircuit) -> CircuitOut:
    return CircuitOut(
        id=row.id,
        name=row.name,
        description=row.description,
        circuit_ir=row.circuit_ir,
        qasm3=row.qasm3,
        is_dynamic=bool(row.is_dynamic),
    )
