#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TwoPhaseEvaluator - two-phase evaluator

Core idea:
Cost optimization: first use fast approximate evaluation to filter, then use accurate
evaluation to validate.

Workflow:
1. Phase 1 (filtering): use ApproximateEvaluator to quickly evaluate all candidates
2. Filter: keep only promising candidates (based on a confidence threshold)
3. Phase 2 (validation): use an accurate evaluator (e.g., SemanticJudgeEvaluator)
4. Merge: keep accurate results; eliminated candidates keep their approximate results

Benefits:
- Significantly reduces evaluation cost (avoids expensive evaluation for all candidates)
- Preserves evaluation quality (fully evaluates promising candidates)
- Adaptive strategy (can adjust phase ratios based on budget)
"""
from typing import Any
from dataclasses import dataclass

from optimization.types import Candidate, EvaluationResult
from optimization.protocols import Evaluator
from optimization.evaluators.approximate_evaluator import ApproximateEvaluator


@dataclass
class TwoPhaseConfig:
    """Configuration for two-phase evaluation."""
    # Phase 1 (approximate evaluation)
    phase1_min_confidence: float = 0.3  # Minimum confidence
    phase1_max_candidates: int = 10     # Maximum number of candidates to keep

    # Phase 2 (accurate evaluation)
    phase2_enable: bool = True          # Whether to enable phase 2
    phase2_min_candidates: int = 1      # Minimum number of candidates to evaluate

    # Adaptive strategy
    adaptive: bool = True               # Whether to adaptively adjust
    cost_threshold: float = 100.0       # Cost threshold (be more conservative above this)


class TwoPhaseEvaluator(Evaluator):
    """
    Two-phase evaluator.

    Combines fast approximate evaluation and accurate evaluation to balance cost and quality.
    """

    def __init__(
        self,
        phase1_evaluator: ApproximateEvaluator,
        phase2_evaluator: Evaluator,
        config: TwoPhaseConfig = None
    ):
        """
        Args:
            phase1_evaluator: Phase 1 evaluator (fast approximate).
            phase2_evaluator: Phase 2 evaluator (accurate).
            config: Configuration.
        """
        self.phase1 = phase1_evaluator
        self.phase2 = phase2_evaluator
        self.config = config or TwoPhaseConfig()

        # Stats
        self.stats = {
            'phase1_count': 0,
            'phase2_count': 0,
            'filtered_count': 0,
            'total_cost': 0.0
        }

    def evaluate(self, candidate: Candidate, context: dict) -> EvaluationResult:
        """
        Two-phase evaluation for a single candidate.

        Note: for single-candidate evaluation, phase2 is typically used only when
        phase1 deems it promising.
        """
        # Phase 1: fast evaluation
        phase1_result = self.phase1.evaluate(candidate, context)
        self.stats['phase1_count'] += 1

        # If confidence is too low, return phase1 result directly
        if not phase1_result.metadata.get('is_promising', False):
            self.stats['filtered_count'] += 1
            return phase1_result

        # Phase 2: accurate evaluation
        phase2_result = self.phase2.evaluate(candidate, context)
        self.stats['phase2_count'] += 1

        # Merge metadata
        phase2_result.metadata['phase1_score'] = phase1_result.score
        phase2_result.metadata['phase1_confidence'] = phase1_result.metadata.get('is_promising', False)

        return phase2_result

    def batch_evaluate(
        self,
        candidates: list[Candidate],
        context: dict
    ) -> list[EvaluationResult]:
        """
        Batch evaluation (core of two-phase optimization).

        Workflow:
        1. Phase 1: fast evaluation for all candidates
        2. Filter: keep only promising candidates
        3. Phase 2: accurate evaluation for filtered candidates
        4. Merge results
        """
        if not candidates:
            return []

        # === Phase 1: fast evaluation ===
        print(f"  [TwoPhase] Phase 1: 快速评估 {len(candidates)} 个候选...")
        phase1_results = []
        for candidate in candidates:
            result = self.phase1.evaluate(candidate, context)
            phase1_results.append(result)
            self.stats['phase1_count'] += 1

        # Filter promising candidates
        promising_candidates = []
        promising_indices = []
        filtered_results = []

        for i, result in enumerate(phase1_results):
            if result.metadata.get('is_promising', False):
                promising_candidates.append(candidates[i])
                promising_indices.append(i)
            else:
                # Eliminated candidates keep their phase1 result
                filtered_results.append((i, result))
                self.stats['filtered_count'] += 1

        print(f"  [TwoPhase] 筛选后保留 {len(promising_candidates)} 个候选（淘汰 {len(filtered_results)} 个）")

        # If none passed the filter, return phase1 results
        if not promising_candidates:
            return phase1_results

        # Adaptive adjustment: further limit when too many candidates remain
        if self.config.adaptive and len(promising_candidates) > self.config.phase1_max_candidates:
            # Sort by phase1 score and keep top-k
            sorted_pairs = sorted(
                zip(promising_candidates, promising_indices,
                    [phase1_results[i] for i in promising_indices]),
                key=lambda x: x[2].score,
                reverse=True
            )
            promising_candidates = [x[0] for x in sorted_pairs[:self.config.phase1_max_candidates]]
            promising_indices = [x[1] for x in sorted_pairs[:self.config.phase1_max_candidates]]

            print(f"  [TwoPhase] 自适应限制为 {len(promising_candidates)} 个候选")

        # === Phase 2: accurate evaluation ===
        if self.config.phase2_enable:
            print(f"  [TwoPhase] Phase 2: 精确评估 {len(promising_candidates)} 个候选...")
            phase2_results_map = {}

            for i, candidate in enumerate(promising_candidates):
                original_idx = promising_indices[i]
                result = self.phase2.evaluate(candidate, context)

                # Record phase1 information
                result.metadata['phase1_score'] = phase1_results[original_idx].score
                result.metadata['evaluator'] = 'two_phase'

                phase2_results_map[original_idx] = result
                self.stats['phase2_count'] += 1

            # === Merge results ===
            final_results = []
            for i in range(len(candidates)):
                if i in phase2_results_map:
                    # Use phase2 result when present
                    final_results.append(phase2_results_map[i])
                else:
                    # Eliminated candidates use phase1 result
                    final_results.append(phase1_results[i])

            return final_results
        else:
            # Phase2 disabled: return phase1 results directly
            return phase1_results

    def get_stats(self) -> dict:
        """Get evaluation statistics."""
        total = self.stats['phase1_count']
        if total == 0:
            return self.stats

        return {
            **self.stats,
            'phase1_ratio': self.stats['phase1_count'] / total,
            'phase2_ratio': self.stats['phase2_count'] / total,
            'filter_ratio': self.stats['filtered_count'] / total,
            'cost_reduction': 1.0 - (self.stats['phase2_count'] / total)
        }

    def reset_stats(self):
        """Reset evaluation statistics."""
        self.stats = {
            'phase1_count': 0,
            'phase2_count': 0,
            'filtered_count': 0,
            'total_cost': 0.0
        }


class AdaptiveTwoPhaseEvaluator(TwoPhaseEvaluator):
    """
    Adaptive two-phase evaluator.

    Dynamically adjusts two-phase strategy based on budget and usage.
    """

    def __init__(
        self,
        phase1_evaluator: ApproximateEvaluator,
        phase2_evaluator: Evaluator,
        budget: 'Budget' = None,
        config: TwoPhaseConfig = None
    ):
        super().__init__(phase1_evaluator, phase2_evaluator, config)
        self.budget = budget
        self.iterations_completed = 0

    def batch_evaluate(
        self,
        candidates: list[Candidate],
        context: dict
    ) -> list[EvaluationResult]:
        """Adaptive batch evaluation."""
        # Estimate remaining budget
        if self.budget and self.budget.max_iters:
            remaining_ratio = 1.0 - (self.iterations_completed / self.budget.max_iters)

            # If budget is tight (remaining < 30%), use phase2 more conservatively
            if remaining_ratio < 0.3:
                original_max = self.config.phase1_max_candidates
                self.config.phase1_max_candidates = max(
                    self.config.phase2_min_candidates,
                    int(original_max * 0.5)  # Reduce by 50%
                )
                print(f"  [Adaptive] 预算紧张，phase2 限制调整为 {self.config.phase1_max_candidates}")

        # Run evaluation
        results = super().batch_evaluate(candidates, context)

        # Update iteration counter
        self.iterations_completed += 1

        return results


def create_default_two_phase_evaluator(
    phase1_evaluator: ApproximateEvaluator,
    phase2_evaluator: Evaluator,
    adaptive: bool = True
) -> TwoPhaseEvaluator:
    """Create a two-phase evaluator with default settings."""
    config = TwoPhaseConfig(
        phase1_min_confidence=0.3,
        phase1_max_candidates=10,
        phase2_enable=True,
        phase2_min_candidates=1,
        adaptive=adaptive,
        cost_threshold=100.0
    )

    return TwoPhaseEvaluator(
        phase1_evaluator=phase1_evaluator,
        phase2_evaluator=phase2_evaluator,
        config=config
    )
