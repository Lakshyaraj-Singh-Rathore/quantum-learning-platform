"""Smart Composer service layer orchestrating generation and simplification."""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.quantum.ir import CircuitIR
from app.quantum.smart_composer.generator import generate_circuit_from_task
from app.quantum.smart_composer.models import (
    GenerationResult,
    GenerationTaskSpec,
    OptimizationObjective,
    SimplificationResult,
    SimplificationStage,
    TransformationRule,
)
from app.quantum.smart_composer.rules import TRANSFORMATION_RULES
from app.quantum.smart_composer.simplifier import simplify_circuit

# In-memory job cache for long-running simplification tasks
JOB_STORE: dict[str, dict[str, Any]] = {}


def get_all_rules() -> list[TransformationRule]:
    return TRANSFORMATION_RULES


def generate(task_spec: GenerationTaskSpec) -> GenerationResult:
    return generate_circuit_from_task(task_spec)


def simplify(
    ir: CircuitIR,
    objective: OptimizationObjective = OptimizationObjective.MIN_GATES,
    job_id: str | None = None,
) -> SimplificationResult:
    jid = job_id or f"simp_{uuid.uuid4().hex[:10]}"
    JOB_STORE[jid] = {
        "status": SimplificationStage.ANALYZING.value,
        "progress": 20,
        "created_at": time.time(),
        "result": None,
    }

    result = simplify_circuit(ir, objective=objective, job_id=jid)

    JOB_STORE[jid]["status"] = SimplificationStage.COMPLETED.value
    JOB_STORE[jid]["progress"] = 100
    JOB_STORE[jid]["result"] = result.model_dump()

    return result


def get_job_status(job_id: str) -> dict[str, Any] | None:
    return JOB_STORE.get(job_id)
