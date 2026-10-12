"""Pure, bounded semantic decision gate for offline JEV-compatible experiments.

This module has no provider, audio, playback, or production-server dependency.
Semantic output can select an advisory route; local timing and acoustic state
remain authoritative for eligibility and immediate controls.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

INTENTS = {"wait", "yield", "take_turn", "keep_speaking", "listener_cue", "uncertain"}
ROUTES = {"speaker", "worker", "clarify", "wait"}


@dataclass(frozen=True)
class GateSnapshot:
    utterance_id: str
    revision: int
    captured_at: float
    transcript: str = ""
    epoch: int = 0
    assistant_speaking: bool = False
    user_floor_held: bool = False
    host_turn_ready: bool = False
    speech_active: bool = False
    pause_ms: int = 0
    quiet_requested: bool = False
    speaking_practice: bool = False


@dataclass(frozen=True)
class GateDecision:
    intent: str
    route: str
    eligible: bool
    reason: str
    expression: str | None = None
    sticky: bool = False
    utterance_id: str | None = None
    revision: int | None = None
    local_stop: bool = False


def validate_compaction(original: list[Mapping[str, Any]], selected_ids: list[str], *,
                        pinned_ids: set[str], groups: list[list[str]]) -> list[Mapping[str, Any]]:
    """Validate model-selected IDs; return original records in original order.

    Pinned records and every source/tool/receipt group are atomic. No model text
    is accepted, and malformed selections fail closed without mutating source.
    """
    by_id = {str(row["id"]): row for row in original}
    if len(by_id) != len(original) or any(i not in by_id for i in selected_ids):
        raise ValueError("unknown or duplicate source IDs")
    selected = set(selected_ids)
    if len(selected) != len(selected_ids):
        raise ValueError("duplicate selected IDs")
    if not pinned_ids <= selected:
        raise ValueError("pinned correction/task context omitted")
    for group in groups:
        overlap = selected.intersection(group)
        if overlap and overlap != set(group):
            raise ValueError("dependent tool/receipt group split")
    return [row for row in original if str(row["id"]) in selected]


def decide(snapshot: GateSnapshot, advisory: Mapping[str, Any] | None, *,
           now: float, current_utterance_id: str, current_revision: int,
           current_epoch: int, ttl_ms: int = 700,
           min_confidence: float = 0.65, current_trusted_local_stop: bool = False) -> GateDecision:
    """Apply current local controls and accept only a fresh structured hint."""
    if current_trusted_local_stop:
        return GateDecision("yield", "speaker", True, "local_explicit_stop", local_stop=True)
    if snapshot.epoch != current_epoch or snapshot.utterance_id != current_utterance_id \
            or snapshot.revision != current_revision:
        return GateDecision("uncertain", "clarify", False, "stale_revision")
    age_ms = (now - snapshot.captured_at) * 1000
    if age_ms < 0 or age_ms > ttl_ms:
        return GateDecision("uncertain", "clarify", False, "expired_snapshot")
    if advisory is None:
        return GateDecision("uncertain", "clarify", False, "no_advisory")
    intent = advisory.get("intent")
    route = advisory.get("route")
    confidence = advisory.get("confidence")
    if intent not in INTENTS or route not in ROUTES or not isinstance(confidence, (float, int)) \
            or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        return GateDecision("uncertain", "clarify", False, "malformed_advisory")
    if intent == "uncertain" or confidence < min_confidence:
        return GateDecision("uncertain", "clarify", False, "low_confidence")
    # Semantic hints nominate an action; local floor/audio state gates execution.
    if intent == "listener_cue":
        eligible = (not snapshot.quiet_requested and not snapshot.speaking_practice
                    and not snapshot.speech_active and not snapshot.assistant_speaking
                    and snapshot.user_floor_held and snapshot.pause_ms >= 450)
        if not eligible:
            return GateDecision("wait", "clarify", False, "local_listener_ineligible")
    elif intent == "keep_speaking":
        eligible = snapshot.assistant_speaking
    elif intent == "yield":
        # A fresh, confident semantic interruption may transfer an active
        # speaker's floor; requiring a prior floor-transfer flag would deadlock.
        eligible = snapshot.assistant_speaking or snapshot.user_floor_held
    elif intent == "take_turn":
        # Starting a normal reply requires the host's completed-turn signal.
        eligible = snapshot.host_turn_ready and not snapshot.speech_active
    else:
        eligible = False
    expression = advisory.get("expression")
    if expression is not None and (not isinstance(expression, str) or len(expression) > 48):
        expression = None
    sticky = bool(advisory.get("sticky", False)) and expression is not None
    return GateDecision(intent, route, eligible, "accepted", expression, sticky,
                        snapshot.utterance_id, snapshot.revision)
