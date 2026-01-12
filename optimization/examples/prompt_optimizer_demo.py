#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PromptOptimizer usage examples.

Demonstrates how to use PromptOptimizer to optimize an agent's .dph file.
"""
import sys
from pathlib import Path

# Add repo root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimization import (
    PromptOptimizer,
    QuickPromptOptimizer,
    DeepPromptOptimizer,
    Budget
)


class MockLLMClient:
    """Mock LLM client (replace with a real one in production)."""

    def generate(self, prompt: str) -> str:
        """Generate an optimized prompt."""
        # In real usage, call an LLM API here
        return "优化后的 prompt 内容..."


class MockSemanticJudge:
    """Mock SemanticJudge (replace with a real one in production)."""

    def evaluate(self, analysis_content: str, expected: str, actual: str, knowledge: str = '') -> dict:
        """Return an evaluation result compatible with the SemanticJudge interface."""
        # Simple mock implementation
        if expected and expected.lower() in actual.lower():
            score = 1.0
        else:
            score = 0.5

        from optimization.types import SemanticJudgeDetail

        return {
            'score': score,
            'details': SemanticJudgeDetail(
                error_types=[],
                action_vector=['improve clarity'],
                candidate_injects=[],
                rationale='Mock evaluation',
                phase='exact'
            )
        }


def example_1_basic_usage():
    """Example 1: basic usage."""
    print("=" * 70)
    print("  示例 1: PromptOptimizer 基本使用")
    print("=" * 70)
    print()

    # 1. Create LLM client and SemanticJudge
    llm_client = MockLLMClient()
    semantic_judge = MockSemanticJudge()

    # 2. Create optimizer
    optimizer = PromptOptimizer.create_default(
        llm_client=llm_client,
        semantic_judge=semantic_judge,
        target_section='system'  # Optimize system section only
    )

    # 3. Prepare context
    context = {
        'agent_path': 'path/to/agent.dph',
        'failed_cases': [
            {'case_id': '001', 'error_type': 'logic_error'},
            {'case_id': '002', 'error_type': 'tool_misuse'}
        ],
        'knowledge': '业务规则：...',
        'error_types': ['logic_error', 'tool_misuse']
    }

    # 4. Set budget
    budget = Budget(max_iters=3, max_seconds=180)

    # 5. Optimize agent content
    target = """
system = \"\"\"
你是一个数据分析助手。
\"\"\"
"""

    print("优化原始内容...")
    result = optimizer.optimize(target, context, budget)

    # 6. Inspect results
    print(f"\n✓ 优化完成！")
    print(f"  最佳得分: {result.best_score:.2f}")
    if result.best_candidate:
        print(f"  优化后的内容:\n{result.best_candidate.content[:200]}...")
    print()


def example_2_optimize_file():
    """Example 2: optimize a file (with backup)."""
    print("=" * 70)
    print("  示例 2: 优化 Agent 文件（带备份）")
    print("=" * 70)
    print()

    llm_client = MockLLMClient()
    semantic_judge = MockSemanticJudge()

    # Create optimizer
    optimizer = PromptOptimizer.create_default(
        llm_client=llm_client,
        semantic_judge=semantic_judge
    )

    # NOTE: this uses a demo path; in real usage, provide a real file path
    print("⚠️  这是一个演示示例，使用的是模拟路径")
    print()

    # Example snippet (uncomment for real usage)
    print("使用示例代码：")
    print("""
    result = optimizer.optimize_file(
        agent_path='design/watsons_baseline/dolphins/my_agent.dph',
        context={
            'failed_cases': failed_cases,
            'knowledge': business_rules,
            'error_types': ['logic_error']
        },
        budget=Budget(max_iters=5, max_seconds=300),
        backup=True,      # Auto-backup original file to .backup/ directory
        replace=False     # Do not auto-replace (inspect result first)
    )

    if result.best_candidate:
        print(f"✓ 优化成功！最佳得分: {result.best_score:.2f}")

        # Inspect optimized content
        print("优化后的内容:")
        print(result.best_candidate.content)

        # If satisfied, replace manually
        # agent_path.write_text(result.best_candidate.content)
    """)
    print()


def example_3_quick_vs_deep():
    """Example 3: quick optimization vs deep optimization."""
    print("=" * 70)
    print("  示例 3: 快速优化 vs 深度优化")
    print("=" * 70)
    print()

    llm_client = MockLLMClient()
    semantic_judge = MockSemanticJudge()

    # Quick optimizer: fewer candidates, faster convergence
    quick_optimizer = QuickPromptOptimizer(
        llm_client=llm_client,
        semantic_judge=semantic_judge
    )

    # Deep optimizer: more candidates, best quality
    deep_optimizer = DeepPromptOptimizer(
        llm_client=llm_client,
        semantic_judge=semantic_judge
    )

    target = """
system = \"\"\"
你是一个助手。
\"\"\"
"""

    context = {
        'agent_path': 'test.dph',
        'error_types': ['logic_error']
    }

    print("1. 快速优化（3 个初始候选，耐心值=1）")
    quick_budget = Budget(max_iters=3)
    quick_result = quick_optimizer.optimize(target, context, quick_budget)
    print(f"   得分: {quick_result.best_score:.2f}")
    print()

    print("2. 深度优化（10 个初始候选，耐心值=5）")
    deep_budget = Budget(max_iters=10)
    deep_result = deep_optimizer.optimize(target, context, deep_budget)
    print(f"   得分: {deep_result.best_score:.2f}")
    print()

    print("对比：")
    print(f"  快速优化 - 迭代: {len(quick_result.optimization_history)}, 得分: {quick_result.best_score:.2f}")
    print(f"  深度优化 - 迭代: {len(deep_result.optimization_history)}, 得分: {deep_result.best_score:.2f}")
    print()


def example_4_custom_configuration():
    """Example 4: custom configuration."""
    print("=" * 70)
    print("  示例 4: 自定义优化器配置")
    print("=" * 70)
    print()

    llm_client = MockLLMClient()
    semantic_judge = MockSemanticJudge()

    # Custom configuration
    optimizer = PromptOptimizer(
        llm_client=llm_client,
        semantic_judge=semantic_judge,
        target_section='system',     # Optimize system section only
        initial_size=5,              # 5 initial candidates
        use_two_phase=True,          # Use two-phase evaluation (cost optimization)
        patience=3,                  # Patience = 3
        min_improvement=0.05         # Minimum improvement = 5%
    )

    print("自定义配置：")
    print(f"  - 目标部分: system")
    print(f"  - 初始候选数: 5")
    print(f"  - 两阶段评估: 是（先快速筛选，再精确评估）")
    print(f"  - 早停耐心值: 3")
    print(f"  - 最小改进: 5%")
    print()

    # Example: optimize system prompt
    target = """
system = \"\"\"
你是一个数据分析助手。
请帮助用户分析数据并回答问题。
\"\"\"
"""

    context = {
        'agent_path': 'agent.dph',
        'failed_cases': [
            {'question': 'Q1', 'expected': 'A1', 'actual': 'Wrong'},
            {'question': 'Q2', 'expected': 'A2', 'actual': 'Wrong'}
        ],
        'knowledge': '分析规则：...',
        'error_types': ['logic_error', 'missing_info']
    }

    budget = Budget(max_iters=5, max_seconds=300)

    print("运行优化...")
    result = optimizer.optimize(target, context, budget)

    print(f"✓ 完成！最佳得分: {result.best_score:.2f}")
    print()


def main():
    """Main entry point."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║            PromptOptimizer 使用示例                              ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()

    # Run examples
    example_1_basic_usage()
    example_2_optimize_file()
    example_3_quick_vs_deep()
    example_4_custom_configuration()

    print("=" * 70)
    print("  更多信息")
    print("=" * 70)
    print()
    print("📖 完整文档:")
    print("  - docs/optimization.md")
    print("  - baks/optimization/OPTIMIZATION_METHODS.md")
    print("  - baks/optimization/PHASE2_IMPLEMENTATION_SUMMARY.md")
    print()
    print("💡 提示:")
    print("  - 快速优化：使用 QuickPromptOptimizer")
    print("  - 深度优化：使用 DeepPromptOptimizer")
    print("  - 成本优化：启用两阶段评估（use_two_phase=True）")
    print("  - 安全第一：始终先 backup=True, replace=False")
    print()


if __name__ == '__main__':
    main()
