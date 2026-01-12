#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SuccessiveHalvingSelector - successive elimination selector

Core idea:
Inspired by Hyperband and Successive Halving, it eliminates low-performing
candidates round by round. Each round keeps only the top fraction (e.g., half),
concentrating resources on the best candidates.

Benefits:
- Resource-efficient: avoids spending evaluation budget on weak candidates
- Exploration/exploitation balance: keeps diversity early and focuses later
- Adaptive: can be adjusted based on evaluation feedback

Use cases:
- Large candidate pools
- Expensive evaluations
- Multi-round iterative optimization
"""
from typing import Any
from dataclasses import dataclass
import math

from optimization.types import Candidate, EvaluationResult
from optimization.protocols import Selector


@dataclass
class SuccessiveHalvingConfig:
    """Configuration for successive halving."""
    halving_ratio: float = 0.5      # Fraction to keep each round (0.5 = keep half)
    min_candidates: int = 1         # Minimum number of candidates to keep
    max_rounds: int = 10            # Maximum number of halving rounds

    # Diversity protection
    diversity_boost: bool = True    # Whether to protect diversity
    diversity_ratio: float = 0.2    # Fraction reserved for diverse candidates


class SuccessiveHalvingSelector(Selector):
    """
    Successive elimination selector.

    Each call to select() reduces the candidate set and focuses on better ones.
    """

    def __init__(self, config: SuccessiveHalvingConfig = None):
        self.config = config or SuccessiveHalvingConfig()
        self.round = 0  # 当前轮次

    def select(
        self,
        candidates: list[Candidate],
        evaluations: list[EvaluationResult]
    ) -> list[Candidate]:
        """
        Select candidates to keep.

        Strategy:
        1. Sort by evaluation score
        2. Keep top (n * halving_ratio) candidates
        3. If diversity protection is enabled, keep extra diverse candidates
        """
        if not candidates:
            return []

        # Compute the target size for this round
        current_size = len(candidates)
        target_size = max(
            self.config.min_candidates,
            int(current_size * self.config.halving_ratio)
        )

        # Sort by score
        sorted_pairs = sorted(
            zip(candidates, evaluations),
            key=lambda x: x[1].score,
            reverse=True
        )

        # Select top-k
        selected = [pair[0] for pair in sorted_pairs[:target_size]]

        # Diversity protection: keep some diverse candidates if enabled
        if self.config.diversity_boost and current_size > target_size:
            diversity_count = max(1, int(target_size * self.config.diversity_ratio))
            diverse_candidates = self._select_diverse(
                candidates=candidates,
                evaluations=evaluations,
                already_selected=selected,
                count=diversity_count
            )
            selected.extend(diverse_candidates)

        # Cap the final size
        if len(selected) > target_size + int(target_size * self.config.diversity_ratio):
            selected = selected[:target_size + int(target_size * self.config.diversity_ratio)]

        self.round += 1
        print(f"  [SuccessiveHalving] Round {self.round}: {current_size} -> {len(selected)} 候选")

        return selected

    def _select_diverse(
        self,
        candidates: list[Candidate],
        evaluations: list[EvaluationResult],
        already_selected: list[Candidate],
        count: int
    ) -> list[Candidate]:
        """
        Select diverse candidates.

        Strategy:
        1. Exclude already selected candidates
        2. Compute candidate differences
        3. Prefer candidates that differ most from the selected set
        """
        # Build the candidate pool (excluding already selected)
        selected_ids = {c.id for c in already_selected}
        candidate_pool = [
            (c, e) for c, e in zip(candidates, evaluations)
            if c.id not in selected_ids
        ]

        if not candidate_pool:
            return []

        diverse = []

        # Simple approach: select candidates from different score ranges
        # Group candidates by score
        score_ranges = self._group_by_score([e.score for e in evaluations])

        for score_range in score_ranges:
            for c, e in candidate_pool:
                if e.score in score_range and len(diverse) < count:
                    # Check whether it differs from already selected candidates
                    if self._is_diverse(c, already_selected):
                        diverse.append(c)
                        break

            if len(diverse) >= count:
                break

        return diverse[:count]

    def _group_by_score(self, scores: list[float], num_groups: int = 3) -> list[tuple[float, float]]:
        """Group scores into ranges."""
        if not scores:
            return []

        min_score = min(scores)
        max_score = max(scores)
        range_size = (max_score - min_score) / num_groups

        groups = []
        for i in range(num_groups):
            start = min_score + i * range_size
            end = start + range_size
            groups.append((start, end))

        return groups

    def _is_diverse(self, candidate: Candidate, others: list[Candidate]) -> bool:
        """
        Determine whether a candidate differs from others.

        Simple heuristics: compare metadata or content differences.
        """
        # Check parent_id differences (different evolutionary path)
        candidate_parent = candidate.parent_id
        other_parents = {c.parent_id for c in others}

        if candidate_parent and candidate_parent not in other_parents:
            return True

        # Check direction differences in metadata
        candidate_direction = candidate.metadata.get('direction', '')
        other_directions = {c.metadata.get('direction', '') for c in others}

        if candidate_direction and candidate_direction not in other_directions:
            return True

        # Check content length difference (as a simple diversity signal)
        candidate_len = len(candidate.content)
        other_lens = [len(c.content) for c in others]
        avg_len = sum(other_lens) / len(other_lens) if other_lens else candidate_len

        if abs(candidate_len - avg_len) > avg_len * 0.2:  # Difference > 20%
            return True

        return False

    def reset(self):
        """Reset round counter."""
        self.round = 0


class AggressiveHalvingSelector(SuccessiveHalvingSelector):
    """
    Aggressive halving selector.

    Eliminates candidates faster, useful for very large candidate pools.
    """

    def __init__(self):
        config = SuccessiveHalvingConfig(
            halving_ratio=0.3,  # Keep only 30% each round
            min_candidates=1,
            max_rounds=10,
            diversity_boost=False  # No diversity protection; pure score-based
        )
        super().__init__(config)


class ConservativeHalvingSelector(SuccessiveHalvingSelector):
    """
    Conservative halving selector.

    Eliminates candidates more slowly, preserving more exploration.
    """

    def __init__(self):
        config = SuccessiveHalvingConfig(
            halving_ratio=0.7,  # Keep 70% each round
            min_candidates=2,
            max_rounds=15,
            diversity_boost=True,
            diversity_ratio=0.3  # Keep 30% diverse candidates
        )
        super().__init__(config)


class DynamicHalvingSelector(Selector):
    """
    Dynamic halving selector.

    Dynamically adjusts the elimination ratio based on candidate performance.
    If the quality variance is large, eliminate more; otherwise, keep more.
    """

    def __init__(self, base_ratio: float = 0.5, min_candidates: int = 1):
        self.base_ratio = base_ratio
        self.min_candidates = min_candidates
        self.round = 0

    def select(
        self,
        candidates: list[Candidate],
        evaluations: list[EvaluationResult]
    ) -> list[Candidate]:
        """Select candidates dynamically."""
        if not candidates:
            return []

        # Compute score variance to estimate quality spread
        scores = [e.score for e in evaluations]
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_dev = math.sqrt(variance)

        # Adjust keep ratio based on variance
        if std_dev > 0.2:
            # Large spread: be more aggressive
            ratio = self.base_ratio * 0.8
        elif std_dev < 0.05:
            # Small spread: keep more conservatively
            ratio = self.base_ratio * 1.2
        else:
            # Normal case
            ratio = self.base_ratio

        ratio = max(0.1, min(0.9, ratio))  # Clamp to [0.1, 0.9]

        # Compute target size
        target_size = max(self.min_candidates, int(len(candidates) * ratio))

        # Select top-k
        sorted_pairs = sorted(
            zip(candidates, evaluations),
            key=lambda x: x[1].score,
            reverse=True
        )
        selected = [pair[0] for pair in sorted_pairs[:target_size]]

        self.round += 1
        print(f"  [DynamicHalving] Round {self.round}: {len(candidates)} -> {len(selected)} "
              f"(ratio={ratio:.2f}, std={std_dev:.3f})")

        return selected

    def reset(self):
        """Reset round counter."""
        self.round = 0


def create_default_successive_halving_selector(
    aggressive: bool = False,
    diversity: bool = True
) -> Selector:
    """Create a successive halving selector with default settings."""
    if aggressive:
        return AggressiveHalvingSelector()

    config = SuccessiveHalvingConfig(
        halving_ratio=0.5,
        min_candidates=1,
        max_rounds=10,
        diversity_boost=diversity,
        diversity_ratio=0.2 if diversity else 0.0
    )

    return SuccessiveHalvingSelector(config)
