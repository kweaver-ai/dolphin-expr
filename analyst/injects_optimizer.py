#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Inject content optimizer (semantic-driven only).

Core idea:
Generate inject content and control convergence based on SemanticJudge diagnostics
(score, error_types, action_vector, candidate_injects). The loss is defined as
semantic loss: loss = 1 - score.

Safety: do not leak answers into inject content.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import random

try:
    from .semantic_gradient import SemanticGradient
except ImportError:
    from semantic_gradient import SemanticGradient


class ErrorType(Enum):
    """Error type categories."""

    FIELD_ERROR = "field_error"  # Field usage error
    CALCULATION_ERROR = "calc_error"  # Calculation/logic error
    FORMAT_ERROR = "format_error"  # Output format error
    INCOMPLETE = "incomplete"  # Incomplete result
    MAGNITUDE_ERROR = "magnitude"  # Order-of-magnitude error
    LOGIC_ERROR = "logic_error"  # Reasoning/logic error
    TIMEOUT_ERROR = "timeout_error"  # Execution timeout
    UNKNOWN = "unknown"


@dataclass
class FailureRecord:
    """Failure record."""

    iteration: int
    inject_content: str
    actual_output: str
    error_type: ErrorType
    error_features: Dict
    loss: float


@dataclass
class OptimizationInfo:
    """Optimization info."""

    gradient: Dict
    learning_rate: float
    convergence_status: str
    loss: float
    momentum_strength: float


class InjectsOptimizer:
    """
    Inject content optimizer inspired by gradient descent.
    """

    def __init__(
        self,
        learning_rate: float = 1.0,
        momentum: float = 0.9,
        patience: int = 3,
        min_learning_rate: float = 0.1,
    ):
        self.learning_rate = learning_rate
        self.initial_learning_rate = learning_rate
        self.momentum = momentum
        self.patience = patience
        self.min_learning_rate = min_learning_rate

        # State tracking
        self.velocity = {}
        self.failure_history: List[FailureRecord] = []
        self.loss_history: List[float] = []
        self.best_loss = float("inf")
        self.plateau_count = 0

        # Baseline tracking
        self.baseline_result = None
        self.baseline_loss = None

        # Semantic-driven context (optional)
        self._semantic_judge: Any | None = None
        self._semantic_analysis_content: str = ""
        self._semantic_knowledge: str = ""

    def optimize(
        self,
        actual: str,
        expected: str,
        knowledge_base: str,
        iteration: int,
        previous_inject: str = "",
    ) -> Tuple[str, OptimizationInfo]:
        """
        Main optimization entry.

        Returns:
            (optimized inject content, optimization info)
        """
        # Semantic-driven mode (must be enabled)
        if not (self._semantic_judge is not None):
            raise RuntimeError(
                "Semantic mode not enabled. Call enable_semantic(...) before optimize()."
            )

        judge_grad_raw = self._semantic_judge.evaluate(
            analysis_content=self._semantic_analysis_content or "",
            expected=expected or "",
            actual=actual or "",
            knowledge=self._semantic_knowledge or knowledge_base or "",
        )

        semantic_grad = SemanticGradient.from_judge_result(judge_grad_raw)
        gradient = self._build_semantic_gradient(semantic_grad, actual, expected)
        loss = semantic_grad.loss
        self.loss_history.append(loss)
        self._update_momentum(gradient)
        adaptive_lr = self._get_adaptive_learning_rate(iteration)
        new_inject = self._generate_inject_from_gradient(
            gradient, knowledge_base, iteration, adaptive_lr
        )
        self._audit_inject(new_inject, expected)
        self._record_failure(iteration, new_inject, actual, gradient, loss)
        opt_info = OptimizationInfo(
            gradient=gradient,
            learning_rate=adaptive_lr,
            convergence_status=self._check_convergence(),
            loss=loss,
            momentum_strength=self._get_momentum_strength(),
        )
        return new_inject, opt_info

    def enable_semantic(self, judge: Any, analysis_content: str, knowledge: str = ""):
        """Enable semantic-driven mode.

        Args:
            judge: SemanticJudge instance (must provide evaluate()).
            analysis_content: Cross-run summary analysis.
            knowledge: Domain knowledge text.
        """
        self._semantic_judge = judge
        self._semantic_analysis_content = analysis_content or ""
        self._semantic_knowledge = knowledge or ""

    def _build_semantic_gradient(
        self, semantic_grad: SemanticGradient, actual: str, expected: str
    ) -> Dict:
        """Map SemanticGradient to an internal gradient structure."""
        score = semantic_grad.score
        error_types = semantic_grad.error_types
        action_vector = semantic_grad.action_vector
        candidate_injects = semantic_grad.candidate_injects

        et = self._map_semantic_error_to_enum(
            error_types[0] if error_types else "unknown"
        )
        gradient = {
            "has_output": bool(actual and actual.strip()),
            "is_error": self._is_error_output(actual),
            "looks_complete": not (actual or "").endswith(("...", "省略")),
            "has_content": len(actual or "") > 20,
            "semantic_hint": (
                ("needs_refinement" if score < 0.6 else "ok") if actual else "no_output"
            ),
            "error_type": et,
            "magnitude": 1.0 - score,
            "action_vector": action_vector,
            "candidate_injects": candidate_injects,
            "score": score,
            "raw": semantic_grad.to_dict(),
        }

        if self.baseline_result is not None and self.baseline_loss is not None:
            current_loss = 1.0 - score
            baseline_loss = self.baseline_loss
            gradient["improved_from_baseline"] = current_loss < baseline_loss
            gradient["improvement_ratio"] = (
                (baseline_loss - current_loss) / baseline_loss
                if baseline_loss > 0
                else 0
            )
            gradient["baseline_comparison"] = {
                "improvement": gradient["improvement_ratio"],
                "baseline_loss": baseline_loss,
                "current_loss": current_loss,
                "is_better": current_loss < baseline_loss,
                "degradation_ratio": (
                    (current_loss - baseline_loss) / baseline_loss
                    if baseline_loss > 0
                    else 0
                ),
            }

        return gradient

    def _map_semantic_error_to_enum(self, err: str) -> ErrorType:
        """Map SemanticJudge error-type strings to internal enum values."""
        if not err:
            return ErrorType.UNKNOWN
        e = err.lower()
        if any(k in e for k in ["calc", "计算", "数值", "公式"]):
            return ErrorType.CALCULATION_ERROR
        if any(k in e for k in ["字段", "field", "列", "维度"]):
            return ErrorType.FIELD_ERROR
        if any(k in e for k in ["格式", "format", "输出格式"]):
            return ErrorType.FORMAT_ERROR
        if any(k in e for k in ["不完整", "缺失", "incomplete"]):
            return ErrorType.INCOMPLETE
        if any(k in e for k in ["数量级", "magnitude"]):
            return ErrorType.MAGNITUDE_ERROR
        if any(k in e for k in ["逻辑", "reasoning", "logic"]):
            return ErrorType.LOGIC_ERROR
        if any(k in e for k in ["超时", "timeout"]):
            return ErrorType.TIMEOUT_ERROR
        return ErrorType.UNKNOWN

    def set_baseline(self, baseline_result: str, baseline_loss: float):
        """Set baseline values for comparison."""
        self.baseline_result = baseline_result
        self.baseline_loss = baseline_loss
        print(f"📊 设置baseline: 损失={baseline_loss:.4f}")

    # Removed: surface-statistics loss function; use semantic loss (1 - score)
    # Removed: heuristic gradient calculation; unified to SemanticJudge-driven gradient

    def _is_error_output(self, output: str) -> bool:
        """Heuristically determine whether this is an error output."""
        if not output:
            return True
        lower_output = output.lower()
        return any(
            err in lower_output
            for err in ["error", "exception", "failed", "错误", "失败"]
        )

    def _count_stuck_iterations(self) -> int:
        """Count consecutive iterations stuck in the same error type."""
        if len(self.failure_history) < 2:
            return 0

        # Count consecutive identical errors
        current_error = self.failure_history[-1].error_type
        stuck_count = 0
        for record in reversed(self.failure_history):
            if record.error_type == current_error:
                stuck_count += 1
            else:
                break
        return stuck_count

    # Removed: _classify_error/_classify_error_simple and basic feature methods (not needed in semantic mode)
    # Removed: heuristic optimization directions (replaced by action_vector/candidate_injects)

    def _update_momentum(self, gradient: Dict):
        """Update momentum."""
        error_type_key = gradient["error_type"].value

        if "error_type" not in self.velocity:
            self.velocity["error_type"] = {}

        if error_type_key not in self.velocity["error_type"]:
            self.velocity["error_type"][error_type_key] = 0

        # Update momentum
        self.velocity["error_type"][error_type_key] = (
            self.momentum * self.velocity["error_type"][error_type_key]
            + (1 - self.momentum) * gradient["magnitude"]
        )

    def _generate_inject_from_gradient(
        self, gradient: Dict, knowledge_base: str, iteration: int, learning_rate: float
    ) -> str:
        """
        Inject generation: prefer semantic candidates/action vectors, otherwise fall back to hint composition.
        """
        # Prefer candidate injects
        cand = gradient.get("candidate_injects") or []
        if isinstance(cand, list) and cand:
            return cand[0]

        # Otherwise use action vectors
        actions = gradient.get("action_vector") or []
        if isinstance(actions, list) and actions:
            return "；".join(actions)

        inject_parts = []

        # Simple guidance based on semantic hints
        semantic_hint = gradient.get("semantic_hint", "needs_refinement")

        if semantic_hint == "no_output":
            inject_parts.append("请确保提供有效的输出结果")
        elif semantic_hint == "execution_error":
            inject_parts.append("请检查并修正执行过程中的错误")
        elif semantic_hint == "incomplete_response":
            inject_parts.append("请确保输出完整的分析结果")
        elif semantic_hint == "too_brief":
            inject_parts.append("请提供更详细的分析和说明")
        else:
            inject_parts.append("请仔细检查分析质量，确保准确性")

        # Adjust strategy based on failure count
        failure_count = gradient.get("failure_count", 0)
        if failure_count > 2:
            inject_parts.append("请尝试不同的分析方法")

        stuck_count = gradient.get("stuck_iterations", 0)
        if stuck_count > 1:
            inject_parts.append("请从新的角度重新思考问题")

        # Add knowledge base content (simplified)
        if knowledge_base and len(knowledge_base) > 50:
            # Use only the first 200 characters and let the LLM infer relevance
            knowledge_excerpt = knowledge_base[:200].strip()
            if knowledge_excerpt:
                inject_parts.append(f"参考要点：{knowledge_excerpt}")

        # Guidance based on baseline comparison
        if gradient.get("improved_from_baseline", False):
            improvement = gradient.get("improvement_ratio", 0)
            if improvement > 0.3:
                inject_parts.append("当前方向正确，继续优化")
            else:
                inject_parts.append("有所改进但仍需进一步优化")
        elif gradient.get("improvement_ratio", 0) < 0:
            inject_parts.append("当前方法可能有问题，请调整策略")

        # Combine all parts
        base_inject = (
            "；".join(inject_parts) if inject_parts else "请仔细分析并提供准确结果"
        )

        # Increase emphasis based on iteration count
        if iteration > 0:
            base_inject = f"第{iteration + 1}次提醒：{base_inject}"

        return base_inject

    # Removed: heuristic helpers such as knowledge extraction/history learning

    def _generate_baseline_guidance(self, baseline_comparison: Dict) -> str:
        """Generate guidance based on baseline comparison."""
        if not baseline_comparison:
            return ""

        guidance_parts = []

        # Provide generic guidance based on improvement/degradation magnitude
        if not baseline_comparison.get("is_better", False):
            degradation_ratio = baseline_comparison.get("degradation_ratio", 0)
            if degradation_ratio > 0.2:
                guidance_parts.append("当前方法可能导致结果退化，请调整策略")
            else:
                guidance_parts.append("改进有限，建议尝试不同的推理路径")
        else:
            guidance_parts.append("方向正确，建议继续沿此方向细化")

        # If improvement is small, suggest more aggressive strategy changes
        improvement = baseline_comparison.get("improvement", 0)
        if 0 < improvement < 0.1:  # Small improvement
            guidance_parts.append("需要更大的策略调整来实现突破")

        if guidance_parts:
            return f"基于baseline对比：{' '.join(guidance_parts)}"
        return ""

    # Removed: failure-mode and repeated-error heuristics (not needed in semantic mode)

    def _get_adaptive_learning_rate(self, iteration: int) -> float:
        """Adaptive learning rate."""
        # Base decay
        decay_rate = 0.9
        base_lr = self.initial_learning_rate * (decay_rate**iteration)

        # Adjust based on convergence status
        if self._check_convergence() == "stuck":
            base_lr *= 1.5  # Increase exploration
        elif self._check_convergence() == "oscillating":
            base_lr *= 0.5  # Reduce oscillation

        return max(base_lr, self.min_learning_rate)

    def _check_convergence(self) -> str:
        """Check convergence status."""
        if len(self.loss_history) < 3:
            return "initializing"

        recent_losses = self.loss_history[-3:]

        # Check whether we are stuck
        if len(self.failure_history) >= 2:
            recent_errors = [f.error_type for f in self.failure_history[-2:]]
            if recent_errors[0] == recent_errors[1]:
                return "stuck"

        # Check whether we are oscillating
        if len(recent_losses) >= 3:
            if (
                recent_losses[0] < recent_losses[1] > recent_losses[2]
                or recent_losses[0] > recent_losses[1] < recent_losses[2]
            ):
                return "oscillating"

        # Check whether we are improving
        if recent_losses[-1] < recent_losses[0]:
            return "improving"

        return "plateau"

    def should_early_stop(self) -> bool:
        """Check whether early stopping should trigger."""
        if len(self.loss_history) < self.patience:
            return False

        # Check whether there has been no improvement recently
        recent_losses = self.loss_history[-self.patience :]
        if max(recent_losses) - min(recent_losses) < 0.01:
            self.plateau_count += 1
            return self.plateau_count >= 2

        self.plateau_count = 0
        return False

    def random_exploration(self, knowledge_base: str) -> str:
        """Randomly explore a new strategy."""
        strategies = [
            "请从不同角度重新分析问题",
            "建议简化查询逻辑，分步骤执行",
            "请检查是否遗漏了关键的过滤条件",
            "尝试使用不同的数据聚合方式",
        ]

        base_strategy = random.choice(strategies)

        if knowledge_base and len(knowledge_base) > 100:
            # Randomly sample a portion of the knowledge base
            start_pos = random.randint(0, len(knowledge_base) - 100)
            knowledge_fragment = knowledge_base[start_pos : start_pos + 200]
            return f"{base_strategy}。参考知识：{knowledge_fragment}"

        return base_strategy

    def _record_failure(
        self,
        iteration: int,
        inject_content: str,
        actual_output: str,
        gradient: Dict,
        loss: float,
    ):
        """Record failure information."""
        record = FailureRecord(
            iteration=iteration,
            inject_content=inject_content,
            actual_output=actual_output[:500],  # Length cap
            error_type=gradient["error_type"],
            error_features=gradient.get("features", {}),
            loss=loss,
        )
        self.failure_history.append(record)

        # Keep only the most recent records
        if len(self.failure_history) > 10:
            self.failure_history = self.failure_history[-10:]

    def _audit_inject(self, inject_content: str, expected: str):
        """Audit inject content to ensure it does not contain the answer."""
        # Check direct answer keywords
        dangerous_patterns = [
            r"答案是",
            r"结果是.*\d",  # Only match cases where digits follow "结果是"
            r"应该是",
            r"正确答案",
            r"计算结果.*\d",  # Only match cases where digits follow "计算结果"
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, inject_content):
                raise ValueError(f"注入内容包含危险模式: {pattern}")

        # Extract key fragments from expected (avoid false positives for short terms)
        answer_fragments = []
        words = expected.split()
        for i in range(len(words)):
            for j in range(i + 2, min(i + 6, len(words) + 1)):  # 2-5 word fragments
                fragment = " ".join(words[i:j])
                if len(fragment) > 8:  # Only check longer fragments to reduce false positives
                    answer_fragments.append(fragment)

        for fragment in answer_fragments:
            if fragment.lower() in inject_content.lower():
                raise ValueError(f"注入内容可能泄露答案片段: {fragment[:20]}...")

        # Check concrete numbers (>=3 digits)
        expected_numbers = re.findall(r"\d{3,}", expected)
        inject_numbers = re.findall(r"\d{3,}", inject_content)

        for num in inject_numbers:
            if num in expected_numbers:
                raise ValueError(f"注入内容包含答案中的具体数值: {num}")

        # Check percentages
        expected_percentages = re.findall(r"\d+%", expected)
        inject_percentages = re.findall(r"\d+%", inject_content)

        for pct in inject_percentages:
            if pct in expected_percentages:
                raise ValueError(f"注入内容包含答案中的具体百分比: {pct}")

        return True

    # Removed: format-type detection (heuristics)
    # Removed: format/structure-related heuristics
    # Removed: structure/completeness/numeric-presence/magnitude heuristics

    def _analyze_previous_inject(self, previous_inject: str) -> Dict:
        """Analyze previous inject content."""
        if not previous_inject:
            return {}

        return {
            "length": len(previous_inject),
            "has_emphasis": any(
                word in previous_inject for word in ["重要", "注意", "关键"]
            ),
            "has_specific_guidance": len(
                re.findall(r"字段|表|计算|公式", previous_inject)
            )
            > 0,
            "iteration_mentioned": bool(re.search(r"第\d+次", previous_inject)),
        }

    def _combine_inject_components(self, components: List[str]) -> str:
        """Combine inject components."""
        if not components:
            return "请仔细分析问题并给出准确结果"

        # De-duplicate while preserving order
        unique_components = list(dict.fromkeys(components))  # Ordered de-dup
        return "；".join(unique_components)

    # Removed: heuristic baseline comparison (semantic mode handles this inside _build_semantic_gradient)

    def _get_momentum_strength(self) -> float:
        """Get current momentum strength."""
        if not self.velocity.get("error_type"):
            return 0.0

        return sum(self.velocity["error_type"].values()) / len(
            self.velocity["error_type"]
        )

    def get_optimization_summary(self) -> Dict:
        """Get an optimization summary."""
        if not self.failure_history:
            return {}

        error_types = [f.error_type.value for f in self.failure_history]
        error_counts = {et: error_types.count(et) for et in set(error_types)}

        return {
            "total_iterations": len(self.failure_history),
            "error_distribution": error_counts,
            "loss_trend": (
                self.loss_history[-5:]
                if len(self.loss_history) >= 5
                else self.loss_history
            ),
            "best_loss": self.best_loss,
            "final_convergence_status": self._check_convergence(),
            "momentum_info": self.velocity,
        }
