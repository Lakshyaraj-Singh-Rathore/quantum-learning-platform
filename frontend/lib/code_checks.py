"""Shim: the Code Lab's static checks now live in the API.

The checker moved to ``app.services.code_checks`` so the new React UI can call
it through ``POST /codelab/check`` instead of duplicating the rules in
TypeScript. This module keeps importing them from there, so the Streamlit page
(which is frozen until the P8 cutover) is untouched and still runs the exact
same code -- there is one implementation, not two.
"""

from __future__ import annotations

from app.services.code_checks import (  # noqa: F401
    BLOCKED_IMPORTS,
    QASM_GATES,
    Finding,
    annotate,
    check,
    check_python,
    check_qasm3,
)

__all__ = [
    "BLOCKED_IMPORTS",
    "QASM_GATES",
    "check",
    "check_python",
    "check_qasm3",
    "annotate",
    "Finding",
]
