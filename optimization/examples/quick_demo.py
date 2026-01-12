#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick demo: showcases the core workflow of the optimization framework.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from optimization import (
    EvolutionOptimizationEngine,
    Candidate,
    EvaluationResult,
    ExecutionContext,
    Budget,
    get_registry,
)


# === Mock components (demo only) ===

class SimpleGenerator:
    """A simple candidate generator (demo only)."""

    def initialize(self, target, context):
        """Generate 3 initial candidates."""
        print("\n[Generator] 生成初始候选...")
        candidates = []
        for i in range(3):
            content = f"候选方案 {i+1}: 优化建议_{i+1}"
            candidate = Candidate(
                content=content,
                execution_context=ExecutionContext(mode='variable')
            )
            candidates.append(candidate)
            print(f"  ✓ {content}")
        return candidates

    def evolve(self, selected, evaluations, context):
        """Generate an improved version from the best candidate."""
        if not selected:
            return []

        print("\n[Generator] 基于最佳候选生成改进版本...")
        best = selected[0]
        improved = Candidate(
            content=f"{best.content} + 改进",
            execution_context=ExecutionContext(mode='variable'),
            parent_id=best.id
        )
        print(f"  ✓ {improved.content}")
        return [improved]


class SimpleEvaluator:
    """A simple evaluator (demo only)."""

    def __init__(self):
        self.eval_count = 0

    def evaluate(self, candidate, context):
        """Evaluate a single candidate."""
        self.eval_count += 1
        # Mock scoring: increase the score on each evaluation
        score = 0.5 + (self.eval_count * 0.1)
        return EvaluationResult(score=min(score, 1.0), cost_tokens=100)

    def batch_evaluate(self, candidates, context):
        """Batch evaluate candidates."""
        print(f"\n[Evaluator] 评估 {len(candidates)} 个候选...")
        results = []
        for candidate in candidates:
            result = self.evaluate(candidate, context)
            print(f"  ✓ {candidate.content[:30]}... => 得分: {result.score:.2f}")
            results.append(result)
        return results


def demo_basic_flow():
    """Demo 1: basic optimization flow."""
    print("=" * 70)
    print("演示1: 基本优化流程")
    print("=" * 70)

    # Get registry
    registry = get_registry()

    # Create components
    generator = SimpleGenerator()
    evaluator = SimpleEvaluator()
    selector = registry.create_selector('topk', k=1)
    controller = registry.create_controller('budget')

    # Create optimization engine
    engine = EvolutionOptimizationEngine(
        generator=generator,
        evaluator=evaluator,
        selector=selector,
        controller=controller
    )

    # Run optimization
    print("\n开始优化...")
    budget = Budget(max_iters=3)
    result = engine.optimize(target=None, context={}, budget=budget)

    # Display results
    print("\n" + "=" * 70)
    print("优化结果:")
    print("=" * 70)
    print(f"最佳候选: {result.best_candidate.content if result.best_candidate else 'None'}")
    print(f"最佳得分: {result.best_score:.2f}")
    print(f"总迭代: {result.metrics['total_iterations']}")
    print(f"总Token消耗: {result.metrics['total_cost_tokens']}")
    print(f"得分提升: {result.metrics['score_improvement']:.2f}")

    print("\n优化历史:")
    for hist in result.optimization_history:
        print(f"  轮次 {hist['iteration']}: "
              f"种群={hist['population_size']}, "
              f"最佳得分={hist['best_score']:.2f}, "
              f"平均得分={hist['avg_score']:.2f}")

    print("\n使用的组件:")
    for comp_type, comp_name in result.components_used.items():
        print(f"  {comp_type}: {comp_name}")


def demo_early_stopping():
    """Demo 2: early stopping."""
    print("\n\n" + "=" * 70)
    print("演示2: 早停机制")
    print("=" * 70)

    registry = get_registry()

    # Use early-stopping controller
    engine = EvolutionOptimizationEngine(
        generator=SimpleGenerator(),
        evaluator=SimpleEvaluator(),
        selector=registry.create_selector('topk', k=1),
        controller=registry.create_controller('early_stopping', patience=2, min_improvement=0.5)
    )

    print("\n说明: 使用早停控制器（patience=2, min_improvement=0.5）")
    print("如果连续2轮得分提升 < 0.5，将提前终止优化\n")

    budget = Budget(max_iters=10)  # Max 10 iterations, may stop early due to early stopping
    result = engine.optimize(target=None, context={}, budget=budget)

    print(f"\n实际执行轮数: {result.metrics['total_iterations']} (最大预算: 10)")
    print(f"最终得分: {result.best_score:.2f}")


def demo_component_registry():
    """Demo 3: component registry."""
    print("\n\n" + "=" * 70)
    print("演示3: 组件注册表")
    print("=" * 70)

    registry = get_registry()
    components = registry.list_components()

    print("\n当前注册的组件:")
    for comp_type, names in components.items():
        print(f"\n{comp_type.upper()}:")
        for name in names:
            print(f"  - {name}")

    print("\n通过注册表创建组件:")
    selector = registry.create_selector('topk', k=5)
    print(f"  ✓ 创建了 TopKSelector(k=5): {type(selector).__name__}")

    controller = registry.create_controller('early_stopping', patience=3)
    print(f"  ✓ 创建了 EarlyStoppingController(patience=3): {type(controller).__name__}")


def main():
    """Run all demos."""
    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + "  Evolution-Based Optimization Framework - 快速演示".center(68) + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)

    demo_basic_flow()
    demo_early_stopping()
    demo_component_registry()

    print("\n\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)
    print("\n📖 更多信息:")
    print("  - 完整文档: docs/optimization.md")
    print("  - 实施总结: baks/optimization/IMPLEMENTATION_SUMMARY.md")
    print("  - 使用示例: optimization/examples/sim_inject_example.py")
    print("  - 运行测试: pytest tests/test_optimization.py -v")
    print("\n")


if __name__ == '__main__':
    main()
