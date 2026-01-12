#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimInject Optimizer usage examples.

Demonstrates how to use the unified optimization framework for sim-inject optimization.
"""
import sys
from pathlib import Path

# Add experiments directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from optimization import (
    SimInjectOptimizer,
    Budget,
    get_registry,
)


def example_1_basic_usage():
    """Example 1: basic usage."""
    print("=" * 60)
    print("示例1: SimInjectOptimizer 基本使用")
    print("=" * 60)

    # NOTE: this is a demo; real usage requires a real SemanticJudge instance
    # from experiments.analyst.semantic_judge import SemanticJudge
    # semantic_judge = SemanticJudge(data_loader=your_data_loader)

    print("""
    # 1. Create optimizer
    optimizer = SimInjectOptimizer.create_default(
        semantic_judge=semantic_judge,
        inject_var='$injects'
    )

    # 2. Prepare context
    context = {
        'agent_path': '/path/to/agent.dph',
        'analysis_content': 'cross-run failure analysis...',
        'expected': 'expected answer',
        'actual': 'actual output',
        'knowledge': 'business knowledge'
    }

    # 3. Set budget
    budget = Budget(max_iters=5, max_seconds=300)

    # 4. Run optimization
    result = optimizer.optimize(
        target=None,
        context=context,
        budget=budget
    )

    # 5. Inspect results
    if result.best_candidate:
        print(f"最佳注入: {result.best_candidate.content}")
        print(f"最佳得分: {result.best_score}")
        print(f"优化轮数: {result.metrics['total_iterations']}")
    """)


def example_2_custom_configuration():
    """Example 2: custom configuration."""
    print("\n" + "=" * 60)
    print("示例2: 自定义优化器配置")
    print("=" * 60)

    print("""
    # Create an optimizer with custom parameters
    optimizer = SimInjectOptimizer(
        semantic_judge=semantic_judge,
        inject_var='$custom_injects',  # Custom variable name
        top_k=5,                        # Keep 5 candidates per round
        patience=3,                     # Early-stopping patience = 3
        min_improvement=0.02            # Minimum improvement threshold = 0.02
    )

    # Set a more detailed budget
    budget = Budget(
        max_iters=10,        # Up to 10 iterations
        max_seconds=600,     # Up to 10 minutes
        max_tokens=100000    # Token budget
    )

    result = optimizer.optimize(target=None, context=context, budget=budget)
    """)


def example_3_using_registry():
    """Example 3: using the component registry."""
    print("\n" + "=" * 60)
    print("示例3: 使用组件注册表")
    print("=" * 60)

    registry = get_registry()

    # List all available components
    components = registry.list_components()
    print("\n可用组件:")
    for comp_type, names in components.items():
        print(f"  {comp_type}: {', '.join(names)}")

    print("""
    # Create components via the registry
    generator = registry.create_generator('sim_inject', inject_var='$injects', initial_size=5)
    selector = registry.create_selector('topk', k=3)
    controller = registry.create_controller('early_stopping', patience=2)

    # Compose a custom optimizer
    from optimization import EvolutionOptimizationEngine, SemanticJudgeEvaluator

    custom_optimizer = EvolutionOptimizationEngine(
        generator=generator,
        evaluator=SemanticJudgeEvaluator(semantic_judge),
        selector=selector,
        controller=controller
    )
    """)


def example_4_result_analysis():
    """Example 4: result analysis."""
    print("\n" + "=" * 60)
    print("示例4: 优化结果分析")
    print("=" * 60)

    print("""
    # Analyze results after optimization
    result = optimizer.optimize(target=None, context=context, budget=budget)

    # 1. Best candidate info
    if result.best_candidate:
        print(f"最佳候选ID: {result.best_candidate.id}")
        print(f"父候选ID: {result.best_candidate.parent_id}")
        print(f"生成策略: {result.best_candidate.metadata.get('generation_strategy')}")
        print(f"内容:\\n{result.best_candidate.content}")

    # 2. Metrics
    print(f"\\n优化指标:")
    print(f"  总迭代次数: {result.metrics['total_iterations']}")
    print(f"  总Token消耗: {result.metrics['total_cost_tokens']}")
    print(f"  得分提升: {result.metrics['score_improvement']}")

    # 3. History
    print(f"\\n优化历史:")
    for hist in result.optimization_history:
        print(f"  轮次 {hist['iteration']}: "
              f"种群={hist['population_size']}, "
              f"最佳={hist['best_score']:.3f}, "
              f"平均={hist['avg_score']:.3f}")

    # 4. Components used
    print(f"\\n使用的组件:")
    for comp_type, comp_name in result.components_used.items():
        print(f"  {comp_type}: {comp_name}")
    """)


def example_5_execution_context():
    """Example 5: ExecutionContext overview."""
    print("\n" + "=" * 60)
    print("示例5: ExecutionContext 机制")
    print("=" * 60)

    print("""
    # SimInject uses an ExecutionContext in variable mode
    from optimization import ExecutionContextFactory

    exec_ctx = ExecutionContextFactory.create_for_sim_inject(
        base_path=Path('/path/to/agent.dph'),
        inject_var='$injects'
    )

    print(f"执行模式: {exec_ctx.mode}")           # 'variable'
    print(f"基础路径: {exec_ctx.base_path}")      # Path('/path/to/agent.dph')
    print(f"变量: {exec_ctx.variables}")          # {'$injects': ''}

    # Candidates automatically carry the execution context
    candidate = Candidate(
        content="请注意数据验证",
        execution_context=exec_ctx
    )

    # Evaluator will interpret ExecutionContext and execute accordingly.
    # For variable mode, it will build a command like:
    # dolphin run /path/to/agent.dph --vars '{"$injects": "Please pay attention to data validation"}'
    """)


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("SimInject Optimizer 使用示例集")
    print("=" * 60)

    example_1_basic_usage()
    example_2_custom_configuration()
    example_3_using_registry()
    example_4_result_analysis()
    example_5_execution_context()

    print("\n" + "=" * 60)
    print("示例演示完成！")
    print("=" * 60)
    print("\n提示: 这些是演示代码，实际使用时需要:")
    print("  1. 提供真实的 SemanticJudge 实例")
    print("  2. 准备实际的 agent.dph 文件和评估数据")
    print("  3. 配置适当的预算和优化参数")
    print("\n详细文档请参考: docs/optimization.md")


if __name__ == '__main__':
    main()
