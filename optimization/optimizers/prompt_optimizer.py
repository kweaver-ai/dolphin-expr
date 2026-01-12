#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PromptOptimizer - Agent Prompt source optimizer

Core idea:
Directly optimize an agent's .dph source file and generate improved variants.

Differences from SimInjectOptimizer:
- SimInject: runtime injection, temporary effect, does not modify source code
- PromptOptimizer: design-time optimization, modifies source code for persistent improvement

Workflow:
1. Read the original .dph file
2. Generate improved variants via PromptModifierGenerator
3. Evaluate via TwoPhaseEvaluator (fast filtering, then accurate evaluation)
4. Gradually eliminate candidates via SuccessiveHalvingSelector
5. Return the best variant (optionally replace the original file)

Safety:
- Scope limiting: only modify the system section by default
- Answer redaction: forbid leaking test answers
- Auto backup: back up the original file before modification
- Format validation: ensure the generated .dph file is valid
"""
from pathlib import Path
from typing import Any
from datetime import datetime
import shutil

from optimization.engine import EvolutionOptimizationEngine
from optimization.generators.prompt_modifier_generator import (
    PromptModifierGenerator,
    PromptModificationConstraint
)
from optimization.evaluators.approximate_evaluator import ApproximateEvaluator
from optimization.evaluators.two_phase_evaluator import TwoPhaseEvaluator
from optimization.evaluators.semantic_judge_evaluator import SemanticJudgeEvaluator
from optimization.selectors.successive_halving_selector import SuccessiveHalvingSelector
from optimization.controllers.budget_controller import (
    BudgetController,
    EarlyStoppingController
)
from optimization.types import Budget, OptimizationResult


class PromptOptimizer(EvolutionOptimizationEngine):
    """
    Agent Prompt source optimizer.

    Based on the evolution optimization framework, it composes:
    - Generator: PromptModifierGenerator (generates prompt variants)
    - Evaluator: TwoPhaseEvaluator (two-phase evaluation to reduce cost)
    - Selector: SuccessiveHalvingSelector (successive elimination)
    - Controller: EarlyStoppingController (early stopping)
    """

    def __init__(
        self,
        llm_client: Any,
        semantic_judge: Any = None,
        target_section: str = 'system',
        initial_size: int = 5,
        use_two_phase: bool = True,
        patience: int = 2,
        min_improvement: float = 0.05
    ):
        """
        Args:
            llm_client: LLM client used to generate prompt variants.
            semantic_judge: SemanticJudge instance used for accurate evaluation.
            target_section: Target section to optimize ('system', 'tools', 'all').
            initial_size: Initial candidate count.
            use_two_phase: Whether to use two-phase evaluation for cost reduction.
            patience: Early-stopping patience.
            min_improvement: Minimum improvement threshold.
        """
        # Create components
        generator = PromptModifierGenerator(
            llm_client=llm_client,
            initial_size=initial_size,
            constraints=PromptModificationConstraint(
                target_section=target_section,
                max_length_ratio=1.3,
                preserve_sections=[],
                forbidden_patterns=[
                    r'答案是.*',
                    r'correct answer is.*',
                    r'expected.*result.*is.*',
                ]
            )
        )

        # Create evaluator
        if use_two_phase and semantic_judge:
            # Two-phase evaluation: fast filtering, then accurate evaluation
            phase1 = ApproximateEvaluator()
            phase2 = SemanticJudgeEvaluator(semantic_judge)
            evaluator = TwoPhaseEvaluator(phase1, phase2)
        elif semantic_judge:
            # Use accurate evaluation only
            evaluator = SemanticJudgeEvaluator(semantic_judge)
        else:
            # Use approximate evaluation only
            evaluator = ApproximateEvaluator()

        # Create selector
        selector = SuccessiveHalvingSelector()

        # Create controller
        controller = EarlyStoppingController(
            patience=patience,
            min_improvement=min_improvement
        )

        super().__init__(
            generator=generator,
            evaluator=evaluator,
            selector=selector,
            controller=controller
        )

        self.llm_client = llm_client
        self.semantic_judge = semantic_judge
        self.target_section = target_section

    @classmethod
    def create_default(
        cls,
        llm_client: Any,
        semantic_judge: Any = None,
        target_section: str = 'system',
        aggressive: bool = False
    ) -> 'PromptOptimizer':
        """
        Create a PromptOptimizer with a default configuration.

        Args:
            llm_client: LLM client.
            semantic_judge: Optional SemanticJudge instance.
            target_section: Target section to optimize.
            aggressive: Whether to use an aggressive optimization strategy.

        Returns:
            A configured PromptOptimizer.
        """
        if aggressive:
            # Aggressive strategy: more initial candidates and stricter elimination
            return cls(
                llm_client=llm_client,
                semantic_judge=semantic_judge,
                target_section=target_section,
                initial_size=10,
                use_two_phase=True,
                patience=1,
                min_improvement=0.1
            )
        else:
            # Conservative strategy: fewer candidates and more patience
            return cls(
                llm_client=llm_client,
                semantic_judge=semantic_judge,
                target_section=target_section,
                initial_size=5,
                use_two_phase=True,
                patience=3,
                min_improvement=0.05
            )

    def optimize_file(
        self,
        agent_path: str | Path,
        context: dict,
        budget: Budget,
        backup: bool = True,
        replace: bool = False
    ) -> OptimizationResult:
        """
        Optimize an agent file.

        Args:
            agent_path: Path to the agent file.
            context: Optimization context (failed_cases, knowledge, etc.).
            budget: Optimization budget.
            backup: Whether to back up the original file.
            replace: Whether to replace the original file with the best variant.

        Returns:
            Optimization result.
        """
        agent_path = Path(agent_path)

        if not agent_path.exists():
            raise FileNotFoundError(f"Agent 文件不存在: {agent_path}")

        # 1. Read original file
        original_content = agent_path.read_text(encoding='utf-8')

        # 2. Back up original file
        if backup:
            backup_path = self._backup_file(agent_path)
            print(f"✓ 已备份原文件: {backup_path}")

        # 3. Enrich context
        context['agent_path'] = str(agent_path)

        # 4. Run optimization
        print(f"开始优化 {agent_path.name} 的 {self.target_section} 部分...")
        result = self.optimize(
            target=original_content,
            context=context,
            budget=budget
        )

        # 5. Optionally replace the original file
        if replace and result.best_candidate:
            print(f"\n替换原文件...")
            agent_path.write_text(result.best_candidate.content, encoding='utf-8')
            print(f"✓ 已用最佳版本替换: {agent_path}")
            print(f"  最佳得分: {result.best_score:.2f}")
            print(f"  备份位置: {backup_path if backup else '(未备份)'}")

        return result

    def _backup_file(self, file_path: Path) -> Path:
        """Back up a file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = file_path.parent / '.backup'
        backup_dir.mkdir(exist_ok=True)

        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_name

        shutil.copy2(file_path, backup_path)
        return backup_path


class QuickPromptOptimizer(PromptOptimizer):
    """
    Quick prompt optimizer.

    Useful for quickly validating optimization ideas, trading quality for speed.
    """

    def __init__(self, llm_client: Any, semantic_judge: Any = None):
        super().__init__(
            llm_client=llm_client,
            semantic_judge=semantic_judge,
            target_section='system',
            initial_size=3,      # Generate only 3 initial candidates
            use_two_phase=True,  # Use two-phase evaluation to save cost
            patience=1,          # Small patience for fast convergence
            min_improvement=0.1  # Higher improvement threshold
        )


class DeepPromptOptimizer(PromptOptimizer):
    """
    Deep prompt optimizer.

    Suitable for systematic optimization when best quality is desired.
    """

    def __init__(self, llm_client: Any, semantic_judge: Any):
        super().__init__(
            llm_client=llm_client,
            semantic_judge=semantic_judge,
            target_section='system',
            initial_size=10,     # More initial candidates
            use_two_phase=True,  # Use two-phase evaluation
            patience=5,          # Larger patience
            min_improvement=0.02 # Smaller improvement threshold (stricter convergence)
        )


def optimize_agent_file(
    agent_path: str | Path,
    llm_client: Any,
    semantic_judge: Any = None,
    failed_cases: list[dict] = None,
    knowledge: str = '',
    budget: Budget = None,
    target_section: str = 'system',
    backup: bool = True,
    replace: bool = False
) -> OptimizationResult:
    """
    Convenience helper to optimize an agent file.

    Args:
        agent_path: Path to the agent file.
        llm_client: LLM client.
        semantic_judge: SemanticJudge instance.
        failed_cases: Failed test cases.
        knowledge: Domain knowledge.
        budget: Optimization budget.
        target_section: Target section to optimize.
        backup: Whether to back up the original file.
        replace: Whether to replace the original file.

    Returns:
        Optimization result.
    """
    optimizer = PromptOptimizer.create_default(
        llm_client=llm_client,
        semantic_judge=semantic_judge,
        target_section=target_section
    )

    context = {
        'failed_cases': failed_cases or [],
        'knowledge': knowledge,
        'error_types': []  # Can be extracted from failed_cases
    }

    # Extract error types from failed_cases
    if failed_cases:
        error_types = set()
        for case in failed_cases:
            if 'error_type' in case:
                error_types.add(case['error_type'])
        context['error_types'] = list(error_types)

    budget = budget or Budget(max_iters=5, max_seconds=300)

    return optimizer.optimize_file(
        agent_path=agent_path,
        context=context,
        budget=budget,
        backup=backup,
        replace=replace
    )
