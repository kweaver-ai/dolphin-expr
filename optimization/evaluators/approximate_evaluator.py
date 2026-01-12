#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ApproximateEvaluator - Fast approximate evaluator

Core idea:
Before running the full SemanticJudge evaluation, use faster heuristics for an initial
screening. This can significantly reduce evaluation cost and only run accurate
evaluation for promising candidates.

Fast evaluation strategies:
1. Rule-based checks (format, length, etc.)
2. Simplified semantic matching (keywords, similarity)
3. Matching from prior experience (knowledge base)
4. Lightweight LLM calls (if available)
"""
from typing import Any
from dataclasses import dataclass
import re
from difflib import SequenceMatcher

from optimization.types import Candidate, EvaluationResult, SemanticJudgeDetail
from optimization.protocols import EvaluatorBase


@dataclass
class ApproximateConfig:
    """Configuration for approximate evaluation."""
    # Weights used by the fast evaluation stage
    format_weight: float = 0.3      # Format matching weight
    keyword_weight: float = 0.3     # Keyword matching weight
    similarity_weight: float = 0.4   # Similarity weight

    # Thresholds
    min_confidence: float = 0.3      # Minimum confidence (below this will be dropped)
    max_candidates: int = 10         # Maximum number of candidates to keep

    # Keyword extraction
    extract_keywords: bool = True


class ApproximateEvaluator(EvaluatorBase):
    """
    Fast approximate evaluator.

    Used as the first stage of TwoPhaseEvaluator to quickly filter candidates.
    """

    def __init__(self, config: ApproximateConfig = None):
        self.config = config or ApproximateConfig()
        self._expected_keywords: set[str] = set()
        self._format_patterns: list[str] = []

    def evaluate(self, candidate: Candidate, context: dict) -> EvaluationResult:
        """
        Quickly evaluate a single candidate.

        Dimensions:
        1. Format match
        2. Keyword coverage
        3. Similarity to expected output
        """
        # Extract context
        expected = context.get('expected', '')
        question = context.get('question', '')
        knowledge = context.get('knowledge', '')

        # On the first evaluation, extract keywords and format patterns
        if self.config.extract_keywords and not self._expected_keywords:
            self._extract_expected_info(expected, question, knowledge)

        # Fast evaluation
        format_score = self._evaluate_format(candidate.content)
        keyword_score = self._evaluate_keywords(candidate.content)
        similarity_score = self._evaluate_similarity(candidate.content, expected)

        # Compute weighted total score
        total_score = (
            format_score * self.config.format_weight +
            keyword_score * self.config.keyword_weight +
            similarity_score * self.config.similarity_weight
        )

        # Mark as low-confidence when the score is too low
        if total_score < self.config.min_confidence:
            is_promising = False
        else:
            is_promising = True

        # Build evaluation result
        details = SemanticJudgeDetail(
            error_types=['approximate_low_confidence'] if not is_promising else [],
            action_vector=[
                f'format_score: {format_score:.2f}',
                f'keyword_score: {keyword_score:.2f}',
                f'similarity_score: {similarity_score:.2f}'
            ],
            candidate_injects=[],
            rationale=f'Fast evaluation - confidence: {"high" if is_promising else "low"}',
            phase='approx'
        )

        return EvaluationResult(
            score=total_score,
            detail={'is_promising': is_promising, 'semantic_detail': details},
            cost_tokens=10,  # Approx evaluation is cheap
            metadata={
                'evaluator': 'approximate',
                'is_promising': is_promising,
                'format_score': format_score,
                'keyword_score': keyword_score,
                'similarity_score': similarity_score
            }
        )

    def _extract_expected_info(self, expected: str, question: str, knowledge: str):
        """Extract key signals from expected output and question."""
        # Extract keywords
        text = f"{expected} {question}"
        # Simple keyword extraction (remove common stop-words)
        stop_words = {'的', '了', '和', '是', '在', '有', '与', '等', '如', '为',
                     'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at'}

        words = re.findall(r'\w+', text.lower())
        self._expected_keywords = {w for w in words if w not in stop_words and len(w) > 1}

        # Extract possible format patterns (e.g., numbers, option letters, etc.)
        # Check whether it looks like a multiple-choice format (A/B/C/D)
        if re.search(r'\b[A-D]\b', expected):
            self._format_patterns.append(r'\b[A-D]\b')

        # Check whether it contains numeric values
        if re.search(r'\d+\.?\d*', expected):
            self._format_patterns.append(r'\d+\.?\d*')

        # Check whether it looks like a list format
        if re.search(r'[，,]', expected):
            self._format_patterns.append(r'[，,]')

    def _evaluate_format(self, content: str) -> float:
        """
        Evaluate format matching.

        Checks whether the output matches expected format patterns.
        """
        if not self._format_patterns:
            return 0.5  # No specific format requirement: return a neutral score

        matches = 0
        for pattern in self._format_patterns:
            if re.search(pattern, content):
                matches += 1

        return matches / len(self._format_patterns)

    def _evaluate_keywords(self, content: str) -> float:
        """
        Evaluate keyword coverage.

        Checks how many expected keywords are present in the output.
        """
        if not self._expected_keywords:
            return 0.5  # No keywords: return a neutral score

        content_words = set(re.findall(r'\w+', content.lower()))
        matched = self._expected_keywords & content_words
        coverage = len(matched) / len(self._expected_keywords)

        return coverage

    def _evaluate_similarity(self, content: str, expected: str) -> float:
        """
        Evaluate similarity to expected output.

        Uses a simple string similarity algorithm.
        """
        if not expected:
            return 0.5  # No expected output: return a neutral score

        # Compute similarity using SequenceMatcher
        similarity = SequenceMatcher(None, content.lower(), expected.lower()).ratio()

        return similarity

    def filter_promising(
        self,
        candidates: list[Candidate],
        evaluations: list[EvaluationResult]
    ) -> tuple[list[Candidate], list[EvaluationResult]]:
        """
        Filter promising candidates.

        Used in the first stage of two-phase evaluation to keep only candidates
        worth a more accurate evaluation.
        """
        promising = []
        promising_evals = []

        # Sort by score
        sorted_pairs = sorted(
            zip(candidates, evaluations),
            key=lambda x: x[1].score,
            reverse=True
        )

        # Keep only high-confidence candidates, capped at the configured maximum
        for candidate, evaluation in sorted_pairs[:self.config.max_candidates]:
            if evaluation.metadata.get('is_promising', False):
                promising.append(candidate)
                promising_evals.append(evaluation)

        return promising, promising_evals


class RuleBasedApproximateEvaluator(ApproximateEvaluator):
    """
    Rule-based fast evaluator.

    Useful when explicit rules exist (e.g., format checks, required field validation).
    """

    def __init__(self, rules: list[dict] = None, config: ApproximateConfig = None):
        """
        Args:
            rules: 评估规则列表，每个规则包含：
                - name: 规则名称
                - pattern: 正则表达式模式
                - weight: 权重
                - required: 是否必需
        """
        super().__init__(config)
        self.rules = rules or []

    def evaluate(self, candidate: Candidate, context: dict) -> EvaluationResult:
        """Quickly evaluate a candidate using rules."""
        if not self.rules:
            # No rules provided: fall back to the parent approximate evaluation
            return super().evaluate(candidate, context)

        content = candidate.content
        total_score = 0.0
        total_weight = 0.0
        failed_required = []

        for rule in self.rules:
            name = rule.get('name', 'unnamed')
            pattern = rule.get('pattern', '')
            weight = rule.get('weight', 1.0)
            required = rule.get('required', False)

            if re.search(pattern, content):
                # Rule matched
                total_score += weight
            else:
                # Rule not matched
                if required:
                    failed_required.append(name)

            total_weight += weight

        # If any required rule is not satisfied, force a low score
        if failed_required:
            normalized_score = 0.1
            error_types = [f'missing_required_{rule}' for rule in failed_required]
        else:
            normalized_score = total_score / total_weight if total_weight > 0 else 0.5
            error_types = []

        details = SemanticJudgeDetail(
            error_types=error_types,
            action_vector=[f'规则评估: {normalized_score:.2f}'],
            candidate_injects=[],
            rationale=f'基于规则的快速评估，未满足必需规则: {failed_required}' if failed_required else '规则评估通过',
            phase='approx'
        )

        return EvaluationResult(
            score=normalized_score,
            detail={'semantic_detail': details},
            cost_tokens=5,
            metadata={
                'evaluator': 'rule_based_approximate',
                'is_promising': normalized_score >= self.config.min_confidence,
                'failed_required': failed_required
            }
        )


def create_default_approximate_evaluator(
    min_confidence: float = 0.3,
    max_candidates: int = 10
) -> ApproximateEvaluator:
    """Create an approximate evaluator with a default configuration."""
    config = ApproximateConfig(
        format_weight=0.3,
        keyword_weight=0.3,
        similarity_weight=0.4,
        min_confidence=min_confidence,
        max_candidates=max_candidates,
        extract_keywords=True
    )
    return ApproximateEvaluator(config)
