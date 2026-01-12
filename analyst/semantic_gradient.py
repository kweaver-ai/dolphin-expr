#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SemanticGradient: A wrapper for semantic gradient data access that normalizes
different result data structures.
"""

from typing import List, Any, Optional, Dict
from dataclasses import dataclass


@dataclass
class SemanticGradient:
    """
    A wrapper for semantic gradient data that normalizes complex nested results
    returned by SemanticJudge.

    SemanticJudge may return one of the following formats:
    1. Flat: {'score': 0.8, 'candidate_injects': [...], ...}
    2. Nested: {'output_var_value': {'score': 0.8, 'candidate_injects': [...]}, 'score': 0.0, ...}
    """

    _raw_data: Dict[str, Any]
    _score: float
    _correct: bool
    _error_types: List[str]
    _missing_constraints: List[str]
    _action_vector: List[str]
    _candidate_injects: List[str]
    _rationale: str

    @classmethod
    def from_judge_result(cls, judge_result: Dict[str, Any]) -> "SemanticGradient":
        """
        Create a SemanticGradient instance from a raw SemanticJudge result.

        Args:
            judge_result: Raw dict returned by SemanticJudge.

        Returns:
            A SemanticGradient instance.

        Raises:
            ValueError: If the input data format is invalid.
        """
        if not isinstance(judge_result, dict):
            raise ValueError(
                f"judge_result必须是字典类型，实际类型: {type(judge_result)}"
            )

        # Prefer output_var_value and fall back to root-level fields
        output_var_value = judge_result.get("output_var_value", {})

        def _get_field(field_name: str, default_value: Any = None) -> Any:
            """Prefer output_var_value and fall back to root-level fields."""
            if isinstance(output_var_value, dict) and field_name in output_var_value:
                return output_var_value[field_name]
            return judge_result.get(field_name, default_value)

        # Extract and validate fields
        score = _get_field("score", 0.0)
        if not isinstance(score, (int, float)):
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0.0

        correct = _get_field("correct", False)
        if not isinstance(correct, bool):
            correct = bool(correct)

        error_types = _get_field("error_types", [])
        if not isinstance(error_types, list):
            error_types = []
        error_types = [str(et) for et in error_types if et]

        missing_constraints = _get_field("missing_constraints", [])
        if not isinstance(missing_constraints, list):
            missing_constraints = []
        missing_constraints = [str(mc) for mc in missing_constraints if mc]

        action_vector = _get_field("action_vector", [])
        if not isinstance(action_vector, list):
            action_vector = []
        action_vector = [str(av) for av in action_vector if av]

        candidate_injects = _get_field("candidate_injects", [])
        if not isinstance(candidate_injects, list):
            candidate_injects = []
        candidate_injects = [str(ci) for ci in candidate_injects if ci]

        rationale = _get_field("rationale", "")
        if not isinstance(rationale, str):
            rationale = str(rationale) if rationale else ""

        return cls(
            _raw_data=judge_result,
            _score=score,
            _correct=correct,
            _error_types=error_types,
            _missing_constraints=missing_constraints,
            _action_vector=action_vector,
            _candidate_injects=candidate_injects,
            _rationale=rationale,
        )

    @property
    def score(self) -> float:
        """Semantic score (0.0-1.0)."""
        return self._score

    @property
    def correct(self) -> bool:
        """Whether the output is semantically correct."""
        return self._correct

    @property
    def error_types(self) -> List[str]:
        """List of error types."""
        return self._error_types.copy()

    @property
    def missing_constraints(self) -> List[str]:
        """List of missing constraints."""
        return self._missing_constraints.copy()

    @property
    def action_vector(self) -> List[str]:
        """List of actions (action vector)."""
        return self._action_vector.copy()

    @property
    def candidate_injects(self) -> List[str]:
        """List of candidate inject strings."""
        return self._candidate_injects.copy()

    @property
    def rationale(self) -> str:
        """Rationale text."""
        return self._rationale

    @property
    def loss(self) -> float:
        """Semantic loss (1.0 - score)."""
        return 1.0 - self._score

    @property
    def has_candidate_injects(self) -> bool:
        """Whether candidate injects are available."""
        return len(self._candidate_injects) > 0

    @property
    def has_action_vector(self) -> bool:
        """Whether an action vector is available."""
        return len(self._action_vector) > 0

    @property
    def primary_error_type(self) -> Optional[str]:
        """Primary error type (the first one)."""
        return self._error_types[0] if self._error_types else None

    def get_best_inject_candidate(self) -> Optional[str]:
        """Get the best inject candidate (the first candidate inject)."""
        return self._candidate_injects[0] if self._candidate_injects else None

    def get_action_summary(self) -> str:
        """Get an action summary (joined by semicolons)."""
        return "；".join(self._action_vector) if self._action_vector else ""

    def is_valid_for_optimization(self) -> bool:
        """Whether this gradient is usable for optimization."""
        return self.has_candidate_injects or self.has_action_vector

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dict (for serialization)."""
        return {
            "score": self._score,
            "correct": self._correct,
            "error_types": self._error_types,
            "missing_constraints": self._missing_constraints,
            "action_vector": self._action_vector,
            "candidate_injects": self._candidate_injects,
            "rationale": self._rationale,
            "loss": self.loss,
            "has_candidate_injects": self.has_candidate_injects,
            "has_action_vector": self.has_action_vector,
        }

    def __str__(self) -> str:
        """String representation."""
        return (
            f"SemanticGradient(score={self._score:.3f}, "
            f"correct={self._correct}, "
            f"candidates={len(self._candidate_injects)}, "
            f"actions={len(self._action_vector)})"
        )

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"SemanticGradient("
            f"score={self._score}, "
            f"correct={self._correct}, "
            f"error_types={self._error_types}, "
            f"candidate_injects={len(self._candidate_injects)}, "
            f"action_vector={len(self._action_vector)})"
        )


def aggregate_gradients(
    gradients: List[SemanticGradient], top_n: int = 1, history: List[str] = None
) -> Optional[str]:
    """
    Aggregate multiple semantic gradients and generate inject content, optionally
    using history to avoid repetition.

    Args:
        gradients: List of SemanticGradient instances.
        top_n: Return the top-N most voted inject candidates (default: 1).
        history: List of previous inject strings used to avoid repetition.

    Returns:
        Aggregated inject content, or None if it cannot be produced.
    """
    if not gradients:
        return None

    history = history or []

    # Vote for best inject candidates, using history to avoid repetition
    votes: Dict[str, float] = {}  # Use float for weighted voting

    for grad in gradients:
        # Weight votes by gradient score
        weight = max(0.1, 1.0 - grad.score)  # Lower score => higher weight

        for candidate in grad.candidate_injects:
            if not candidate.strip():
                continue

            # History penalty: reduce weight if it repeats historical injects
            history_penalty = 1.0
            for hist in history:
                if candidate == hist:
                    history_penalty = 0.1  # Exact match: heavy penalty
                elif _similarity(candidate, hist) > 0.8:
                    history_penalty = 0.3  # High similarity: penalty
                elif _similarity(candidate, hist) > 0.5:
                    history_penalty = 0.7  # Medium similarity: small penalty

            final_weight = weight * history_penalty
            votes[candidate] = votes.get(candidate, 0) + final_weight

    if votes:
        # Filter out very low-weight candidates (avoid near-duplicates)
        filtered_votes = {k: v for k, v in votes.items() if v > 0.05}

        if filtered_votes:
            # Sort by weight and take top_n
            sorted_candidates = sorted(
                filtered_votes.items(), key=lambda x: x[1], reverse=True
            )
            selected_candidates = sorted_candidates[:top_n]
            selected_texts = [candidate for candidate, _ in selected_candidates]

            if top_n == 1:
                return selected_texts[0] if selected_texts else None
            else:
                # Return multiple candidates joined by semicolons
                return "；".join(selected_texts)

    # Fallback: aggregate action vectors, also de-duplicating with history
    all_actions = []
    seen_actions = set()

    # Prefer actions from higher-loss (lower-score) gradients
    sorted_grads = sorted(gradients, key=lambda g: g.score)  # Lower score first

    for grad in sorted_grads:
        for action in grad.action_vector:
            if not action.strip() or action in seen_actions:
                continue

            # Check novelty against history
            is_novel = True
            for hist in history:
                if action in hist or _similarity(action, hist) > 0.6:
                    is_novel = False
                    break

            if is_novel:
                all_actions.append(action)
                seen_actions.add(action)
                if len(all_actions) >= 6:  # Cap at 6 actions
                    break

        if len(all_actions) >= 6:
            break

    if all_actions:
        return "；".join(all_actions)

    return None


def _similarity(text1: str, text2: str) -> float:
    """
    Compute similarity between two texts.

    Args:
        text1, text2: Texts to compare.

    Returns:
        Similarity score (0.0-1.0).
    """
    if not text1 or not text2:
        return 0.0

    # Simple word-level similarity
    text1, text2 = text1.strip(), text2.strip()
    if text1 == text2:
        return 1.0

    # Use set intersection/union to compute similarity
    words1 = set(text1.split())
    words2 = set(text2.split())

    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0
