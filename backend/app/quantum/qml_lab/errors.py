"""Exception hierarchy for the QML Lab engine.

The engine is a pure library: it raises these and never imports FastAPI or
Celery. The API layer (Phase 2) maps them onto HTTP status codes, and the
worker maps them onto terminal experiment states.
"""

from __future__ import annotations


class QmlLabError(Exception):
    """Base class for every error raised by the QML Lab engine."""


class QmlConfigError(QmlLabError):
    """The experiment configuration is structurally invalid."""


class QmlLimitExceededError(QmlConfigError):
    """A configured value exceeds a resource limit.

    Separate from :class:`QmlConfigError` because the API answers it with the
    limit table rather than a generic validation message, and because the
    worker re-checks limits at execution time and needs to tell the two cases
    apart in its logs.
    """

    def __init__(self, violations: list[str]) -> None:
        self.violations = list(violations)
        super().__init__("; ".join(self.violations) if self.violations else "resource limit exceeded")


class QmlDatasetError(QmlLabError):
    """A dataset cannot be built as requested.

    Raised rather than silently clamping. A dataset that quietly returns fewer
    samples than asked for caps achievable accuracy and makes the model look
    bad for a reason unrelated to the model.
    """


class QmlPersistenceError(QmlLabError):
    """A model artifact cannot be written or read back."""


class QmlCancelledError(QmlLabError):
    """Internal signal that a cancellation was requested mid-training.

    This must never escape :func:`app.quantum.qml_lab.trainer.train`, which
    catches it and returns a ``cancelled`` outcome carrying partial history.
    Cancellation is an expected outcome, not a failure.
    """
