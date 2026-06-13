from __future__ import annotations

import time
from typing import Callable

from backend.app.schemas import RuntimeFailure, RuntimeStageState, _utc_now_iso


class RuntimeCancelled(RuntimeError):
    """Raised when a persisted run has been marked for cancellation."""


class RuntimeTimeout(RuntimeError):
    """Raised when a run or stage exceeds its configured time budget."""


class RuntimeContext:
    """Small helper for long-running pipeline state.

    The context is intentionally synchronous and callback-based so it can be
    used by the existing FastAPI background-task code without starting extra
    daemons. It publishes heartbeat/stage metadata at each stage boundary and
    checks cancellation/timeout budgets between provider calls.
    """

    def __init__(
        self,
        *,
        flow: str,
        run_id: str,
        run_timeout_ms: int | None = None,
        stage_timeout_ms: int | None = None,
        cancel_check: Callable[[], bool] | None = None,
        on_update: Callable[[RuntimeStageState], None] | None = None,
    ) -> None:
        self.flow = flow
        self.run_id = run_id
        self.run_timeout_ms = _positive_or_none(run_timeout_ms)
        self.stage_timeout_ms = _positive_or_none(stage_timeout_ms)
        self.cancel_check = cancel_check
        self.on_update = on_update
        self._run_started = time.monotonic()
        self._stage_started = self._run_started
        self._current_stage = "queued"
        self._provider = ""
        self._query = ""
        self._subtask = ""
        self._attempt: int | None = None
        self.warning_count = 0
        self.partial_artifact_count = 0

    def begin_stage(
        self,
        current_stage: str,
        *,
        provider: str = "",
        query: str = "",
        subtask: str = "",
        attempt: int | None = None,
        timeout_ms: int | None = None,
        partial_artifact_count: int | None = None,
        warning_count: int | None = None,
    ) -> RuntimeStageState:
        self.checkpoint(partial_artifact_count=partial_artifact_count, warning_count=warning_count)
        self._stage_started = time.monotonic()
        self._current_stage = current_stage
        self._provider = provider
        self._query = query
        self._subtask = subtask
        self._attempt = attempt
        return self._publish(timeout_ms=timeout_ms)

    def checkpoint(
        self,
        *,
        partial_artifact_count: int | None = None,
        warning_count: int | None = None,
    ) -> RuntimeStageState:
        if partial_artifact_count is not None:
            self.partial_artifact_count = max(0, partial_artifact_count)
        if warning_count is not None:
            self.warning_count = max(0, warning_count)
        self._raise_if_cancelled()
        self._raise_if_timed_out()
        return self._publish()

    def complete_stage(
        self,
        *,
        partial_artifact_count: int | None = None,
        warning_count: int | None = None,
    ) -> RuntimeStageState:
        return self.checkpoint(
            partial_artifact_count=partial_artifact_count,
            warning_count=warning_count,
        )

    def failure(
        self,
        *,
        stage: str | None = None,
        reason: str,
        message: str,
        provider: str = "",
        retryable: bool = True,
        repair_suggestion: str = "",
    ) -> RuntimeFailure:
        state = self._state()
        return RuntimeFailure(
            flow=self.flow,
            stage=stage or state.current_stage,
            provider=provider or state.provider,
            reason=reason,
            message=message,
            retryable=retryable,
            elapsed_ms=state.elapsed_ms,
            repair_suggestion=repair_suggestion,
            partial_artifact_count=state.partial_artifact_count,
            created_at=_utc_now_iso(),
        )

    def cancelled_failure(self) -> RuntimeFailure:
        return self.failure(
            reason="cancelled",
            message="Run was cancelled by request; partial artifacts were preserved for retry.",
            retryable=True,
            repair_suggestion="Review partial stage_results, then retry the run when ready.",
        )

    def timeout_failure(self, message: str | None = None) -> RuntimeFailure:
        return self.failure(
            reason="timeout",
            message=message or "Run exceeded its configured time budget.",
            retryable=True,
            repair_suggestion="Retry with a larger timeout or reduce provider/query scope.",
        )

    def _raise_if_cancelled(self) -> None:
        if self.cancel_check and self.cancel_check():
            raise RuntimeCancelled(f"{self.flow} run {self.run_id} cancelled")

    def _raise_if_timed_out(self) -> None:
        elapsed_ms = int((time.monotonic() - self._run_started) * 1000)
        if self.run_timeout_ms and elapsed_ms > self.run_timeout_ms:
            raise RuntimeTimeout(f"{self.flow} run timed out after {elapsed_ms}ms")
        stage_elapsed_ms = int((time.monotonic() - self._stage_started) * 1000)
        if self.stage_timeout_ms and stage_elapsed_ms > self.stage_timeout_ms:
            raise RuntimeTimeout(
                f"{self.flow} stage {self._current_stage} timed out after {stage_elapsed_ms}ms"
            )

    def _publish(self, *, timeout_ms: int | None = None) -> RuntimeStageState:
        state = self._state(timeout_ms=timeout_ms)
        if self.on_update:
            self.on_update(state)
        return state

    def _state(self, *, timeout_ms: int | None = None) -> RuntimeStageState:
        elapsed_ms = int((time.monotonic() - self._run_started) * 1000)
        return RuntimeStageState(
            current_stage=self._current_stage,
            provider=self._provider,
            query=self._query,
            subtask=self._subtask,
            elapsed_ms=elapsed_ms,
            warning_count=self.warning_count,
            partial_artifact_count=self.partial_artifact_count,
            timeout_ms=timeout_ms if timeout_ms is not None else self.stage_timeout_ms,
            attempt=self._attempt,
            heartbeat_at=_utc_now_iso(),
        )


def _positive_or_none(value: int | None) -> int | None:
    if value is None:
        return None
    value = int(value)
    return value if value > 0 else None
