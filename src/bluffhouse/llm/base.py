"""The provider-agnostic LLM client surface.

bluffhouse never talks to a vendor SDK directly — agents see only LLMClient.
Provider quirks (parameter names, auth, thinking modes) live inside each
adapter, so putting a new model at the table means one new adapter class and
nothing else changes.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
import os
import re
import threading
import time

from pydantic import BaseModel


class LLMError(Exception):
    """A provider call failed after the SDK's own retries. Agents catch this
    and fall back to a safe action instead of crashing the game."""


class LLMRequest(BaseModel):
    system: str
    # [{"role": "user"|"assistant", "content": str}, ...] — first must be user
    messages: list[dict[str, str]]
    max_tokens: int = 8000


class LLMResponse(BaseModel):
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    # the provider's native chain-of-thought (e.g. Claude thinking blocks),
    # truncated by the adapter; None for providers that don't expose one
    thinking: str | None = None


class LLMCall(BaseModel):
    """One transcript line: everything about a single provider call, so any
    decision in a benchmark run can be audited after the fact. Token counts
    are the ground truth; dollar cost is a downstream concern (tokens ×
    whatever prices are true on the day of analysis)."""

    agent_id: str
    hand_no: int
    # increments once per decision (act() call); attempts within a decision
    # share it, which is what lets a replay match reasoning to actions
    decision_id: int
    phase: str = "action"  # "action" | "comm"
    attempt: int
    messages: list[dict[str, str]]
    response_text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    parse_error: str | None = None
    action: str | None = None
    thinking: str | None = None


class LLMClient(ABC):
    model: str

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Run one completion. Raises LLMError on unrecoverable provider
        failure (after the SDK's own retry policy)."""


_semaphores: dict[str, threading.Semaphore] = {}
_semaphores_lock = threading.Lock()


def _provider_env_name(provider: str) -> str:
    key = re.sub(r"[^A-Z0-9]+", "_", provider.upper()).strip("_")
    return f"BLUFFHOUSE_{key}_CONCURRENCY"


def _provider_limit(provider: str) -> int:
    raw = os.environ.get(
        _provider_env_name(provider),
        os.environ.get("BLUFFHOUSE_LLM_CONCURRENCY", "1"),
    )
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def _provider_interval(provider: str) -> float:
    key = re.sub(r"[^A-Z0-9]+", "_", provider.upper()).strip("_")
    raw = os.environ.get(
        f"BLUFFHOUSE_{key}_INTERVAL",
        os.environ.get("BLUFFHOUSE_LLM_INTERVAL", "0"),
    )
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.0


_pace_locks: dict[str, threading.Lock] = {}
_last_start: dict[str, float] = {}


@contextmanager
def provider_concurrency(provider: str, model: str | None = None) -> Iterator[None]:
    """Limit concurrent live calls per provider across parallel rotations,
    and optionally pace call starts (BLUFFHOUSE_<PROVIDER>_INTERVAL seconds
    between starts) to stay under free-tier requests-per-minute caps.
    Pacing is per (provider, model): free-tier RPM caps are per model, so
    two models behind one provider each get the full interval budget."""
    limit = _provider_limit(provider)
    key = f"{provider}:{limit}"
    pace_key = f"{provider}/{model or ''}"
    with _semaphores_lock:
        semaphore = _semaphores.setdefault(key, threading.Semaphore(limit))
        pace_lock = _pace_locks.setdefault(pace_key, threading.Lock())
    with semaphore:
        interval = _provider_interval(provider)
        if interval > 0:
            with pace_lock:
                now = time.monotonic()
                wait = _last_start.get(pace_key, -interval) + interval - now
                if wait > 0:
                    time.sleep(wait)
                _last_start[pace_key] = time.monotonic()
        yield
