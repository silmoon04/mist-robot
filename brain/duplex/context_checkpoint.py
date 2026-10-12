"""Opt-in, offline context checkpoints. No model or live runtime is called here.

A caller owns the model invocation: build a request from ``proposal_input``, pass its
JSON result to ``commit``, and use ``working_context`` for a later model request.
The append-only originals remain available independently of every checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Mapping

from .semantic_gate import validate_compaction


PROFILES = {"speech_coaching", "problem_solving", "ordinary_chat"}
PROFILE_INSTRUCTIONS = {
    "speech_coaching": (
        "Keep the speaker's goal, requested coaching, corrections and unfinished work. "
        "Never paraphrase fillers, hesitations, false starts or exact wording marked "
        "for coaching: cite their source IDs and leave those messages in raw form. "
        "Raw text is only the ASR-provided transcript; keep audio references and word "
        "timings when supplied. Capture should request filler_words=true upstream."
    ),
    "problem_solving": (
        "Keep constraints, changed facts, unsuccessful attempts, call receipts and "
        "unfinished goals with source IDs. State corrections and negations explicitly."
    ),
    "ordinary_chat": "Compact durable facts and preferences with source IDs.",
}
CRITICAL_MARKS = {"pin", "correction", "negation", "working_task"}


@dataclass(frozen=True)
class Message:
    id: str
    revision: int
    role: str
    text: str
    marks: frozenset[str] = frozenset()
    protected_segments: tuple[str, ...] = ()
    receipt_group: str | None = None
    audio_ref: str | None = None
    word_timings: tuple[tuple[str, float, float], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "revision": self.revision, "role": self.role,
                "text": self.text, "marks": sorted(self.marks),
                "protected_segments": list(self.protected_segments),
                "receipt_group": self.receipt_group, "audio_ref": self.audio_ref,
                "word_timings": [list(row) for row in self.word_timings]}


@dataclass(frozen=True)
class Snapshot:
    covered_through_revision: int
    task_revision: int
    checkpoint_generation: int
    profile: str
    messages: tuple[Message, ...]


@dataclass(frozen=True)
class Checkpoint:
    covered_through_revision: int
    task_revision: int
    summary: str
    facts: tuple[tuple[str, tuple[str, ...]], ...]
    source_ids: tuple[str, ...]
    raw_ids: tuple[str, ...]


class ContextLedger:
    """Synchronous state boundary suitable for an asynchronous summarizer caller."""

    def __init__(self, profile: str, stable_prefix: tuple[Mapping[str, str], ...] = ()):
        if profile not in PROFILES:
            raise ValueError(f"Unknown task profile: {profile}")
        self._profile = profile
        self.stable_prefix = tuple(dict(part) for part in stable_prefix)
        self._messages: list[Message] = []
        self._checkpoint: Checkpoint | None = None
        self._task_revision = 0
        self._generation = 0
        self._lock = RLock()

    @property
    def profile(self) -> str:
        with self._lock:
            return self._profile

    def set_profile(self, profile: str) -> None:
        """Change the task type and invalidate pending summarizer proposals."""
        if profile not in PROFILES:
            raise ValueError(f"Unknown task profile: {profile}")
        with self._lock:
            if profile != self._profile:
                self._profile = profile
                self._task_revision += 1
                self._checkpoint = None
                self._generation += 1

    def append(self, id: str, role: str, text: str, *, marks=(),
               protected_segments=(), receipt_group: str | None = None,
               task_change: bool = False, audio_ref: str | None = None,
               word_timings=()) -> Message:
        """Append an original. Corrections and task changes invalidate in-flight proposals."""
        marks = frozenset(marks)
        if not id or not isinstance(text, str) or not text:
            raise ValueError("Messages require a nonempty ID and text")
        if not marks <= CRITICAL_MARKS:
            raise ValueError("Unknown message mark")
        protected_segments = tuple(protected_segments)
        if any(not s or s not in text for s in protected_segments):
            raise ValueError("Protected segments must be exact substrings of the original")
        word_timings = tuple(tuple(row) for row in word_timings)
        if any(len(row) != 3 for row in word_timings):
            raise ValueError("Word timings require word, start, end")
        with self._lock:
            if any(message.id == id for message in self._messages):
                raise ValueError("Original message IDs must be unique")
            if task_change or marks.intersection({"correction", "negation", "working_task"}):
                self._task_revision += 1
                self._checkpoint = None
                self._generation += 1
            message = Message(id, len(self._messages) + 1, role, text, marks,
                              protected_segments, receipt_group, audio_ref, word_timings)
            self._messages.append(message)
            return message

    def originals(self) -> tuple[Message, ...]:
        with self._lock:
            return tuple(self._messages)

    def snapshot(self) -> Snapshot:
        with self._lock:
            return Snapshot(len(self._messages), self._task_revision, self._generation,
                            self._profile, tuple(self._messages))

    def should_checkpoint(self, *, estimated_context_tokens: int, token_budget: int,
                          idle_seconds: float, min_new_messages: int = 4,
                          idle_threshold_seconds: float = 30) -> bool:
        """Batch checkpoints on a token threshold or an idle boundary."""
        if token_budget <= 0 or min_new_messages <= 0:
            raise ValueError("Budgets and batch sizes must be positive")
        with self._lock:
            covered = self._checkpoint.covered_through_revision if self._checkpoint else 0
            pending = len(self._messages) - covered
            return pending >= min_new_messages and (
                estimated_context_tokens >= token_budget or
                idle_seconds >= idle_threshold_seconds)

    def proposal_input(self, snapshot: Snapshot) -> dict[str, Any]:
        """Explicit candidate contract; the model must return the stated JSON fields."""
        if snapshot.profile != self.profile:
            raise ValueError("Snapshot belongs to a different profile")
        return {
            "instruction": PROFILE_INSTRUCTIONS[snapshot.profile],
            "contract": {
                "covered_through_revision": snapshot.covered_through_revision,
                "task_revision": snapshot.task_revision,
                "summary": "short model-written context string",
                "facts": [{"text": "source-grounded fact", "source_ids": ["message ID"]}],
                "source_ids": ["all original IDs used by summary or facts"],
                "raw_ids": ["original IDs to retain verbatim"],
            },
            "messages": [m.as_dict() for m in snapshot.messages],
            "warning": (
                "This is a proposal, not a verified faithful summary. The caller must "
                "inspect semantic quality. Do not invent source IDs. If summary text "
                "conflicts with raw originals, the originals take precedence."
            ),
        }

    def commit(self, snapshot: Snapshot, candidate: Mapping[str, Any]) -> Checkpoint:
        """Validate and atomically swap the derived checkpoint, or leave it unchanged."""
        with self._lock:
            if snapshot.profile != self._profile or snapshot.task_revision != self._task_revision:
                raise ValueError("Stale task profile or correction")
            if snapshot.checkpoint_generation != self._generation:
                raise ValueError("A newer checkpoint already committed")
            if snapshot.covered_through_revision <= (
                self._checkpoint.covered_through_revision if self._checkpoint else 0
            ):
                raise ValueError("Checkpoint must advance coverage")
            if tuple(self._messages[:snapshot.covered_through_revision]) != snapshot.messages:
                raise ValueError("Snapshot originals changed")
            if candidate.get("covered_through_revision") != snapshot.covered_through_revision:
                raise ValueError("Candidate coverage differs from snapshot")
            if candidate.get("task_revision") != snapshot.task_revision:
                raise ValueError("Candidate task revision differs from snapshot")
            summary = candidate.get("summary")
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("Candidate needs a nonempty summary")
            by_id = {m.id: m for m in snapshot.messages}
            source_ids = _ids(candidate.get("source_ids"), by_id)
            raw_ids = _ids(candidate.get("raw_ids"), by_id)
            source_set, raw_set = set(source_ids), set(raw_ids)
            if not raw_set <= source_set:
                raise ValueError("Raw IDs must also be source IDs")
            mandatory = {m.id for m in snapshot.messages if m.marks or m.protected_segments}
            if snapshot.profile == "speech_coaching":
                mandatory.update(m.id for m in snapshot.messages if m.role == "user")
            groups: dict[str, set[str]] = {}
            for m in snapshot.messages:
                if m.receipt_group:
                    groups.setdefault(m.receipt_group, set()).add(m.id)
            mandatory.update(id for group in groups.values() for id in group)
            ordered_raw_records = validate_compaction(
                [m.as_dict() for m in snapshot.messages], list(raw_ids),
                pinned_ids=mandatory, groups=[list(group) for group in groups.values()])
            facts_value = candidate.get("facts")
            if not isinstance(facts_value, list):
                raise ValueError("Candidate facts must be a list")
            facts = []
            for fact in facts_value:
                if not isinstance(fact, Mapping) or not isinstance(fact.get("text"), str) or not fact["text"].strip():
                    raise ValueError("Every fact needs nonempty text")
                refs = _ids(fact.get("source_ids"), by_id)
                if not refs or not set(refs) <= source_set:
                    raise ValueError("Every fact needs cited candidate source IDs")
                facts.append((fact["text"], refs))
            # Preserve source order for deterministic rendering. This validates structure,
            # provenance and exact raw retention, not free-form semantic faithfulness.
            ordered_raw = tuple(m["id"] for m in ordered_raw_records)
            result = Checkpoint(snapshot.covered_through_revision,
                                snapshot.task_revision, summary, tuple(facts),
                                source_ids, ordered_raw)
            self._checkpoint = result
            self._generation += 1
            return result

    def working_context(self, *, recent_window: int = 8) -> dict[str, Any]:
        """Stable prefix, derived checkpoint, exact critical originals and untouched tail."""
        if recent_window < 0:
            raise ValueError("recent_window must be nonnegative")
        with self._lock:
            checkpoint = self._checkpoint
            if checkpoint is None:
                return {"stable_prefix": self.stable_prefix, "checkpoint": None,
                        "raw": [], "tail": [m.as_dict() for m in self._messages],
                        "recent_ids": [m.id for m in self._messages[-recent_window:]] if recent_window else []}
            covered = self._messages[:checkpoint.covered_through_revision]
            raw_set = set(checkpoint.raw_ids)
            raw = [m.as_dict() for m in covered if m.id in raw_set]
            tail = self._messages[checkpoint.covered_through_revision:]
            return {"stable_prefix": self.stable_prefix,
                    "checkpoint": {"summary": checkpoint.summary,
                                   "facts": [{"text": text, "source_ids": list(ids)} for text, ids in checkpoint.facts],
                                   "source_ids": list(checkpoint.source_ids),
                                   "covered_through_revision": checkpoint.covered_through_revision},
                    "raw": raw,
                    "recent_ids": [m.id for m in tail[-recent_window:]] if recent_window else [],
                    "tail": [m.as_dict() for m in tail]}


def _ids(value: Any, by_id: Mapping[str, Message]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(id, str) for id in value):
        raise ValueError("IDs must be a list of strings")
    if len(value) != len(set(value)) or any(id not in by_id for id in value):
        raise ValueError("Duplicate or unknown source ID")
    return tuple(value)
