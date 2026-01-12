#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PromptModifierGenerator - generate prompt variants via an LLM.

Core idea:
1. Read the original .dph file content
2. Generate improved versions based on SemanticJudge feedback
3. Improve system prompt, tool prompt, or structure in a targeted way
4. Test via the temp_file execution mode

Safety:
- Scope limiting: only modify the system section by default
- Answer redaction: forbid leaking test answers in prompts
- Format validation: ensure the generated output is a valid .dph file
"""
from pathlib import Path
from typing import Any
import json
import re
from dataclasses import dataclass

from optimization.types import Candidate, ExecutionContext, EvaluationResult
from optimization.protocols import Generator


@dataclass
class PromptModificationConstraint:
    """Constraints for prompt modification."""
    target_section: str = 'system'  # 'system', 'tools', 'all'
    max_length_ratio: float = 1.3  # Do not exceed 130% of the original length
    preserve_sections: list[str] = None  # Sections to preserve unchanged
    forbidden_patterns: list[str] = None  # Forbidden patterns (e.g., answer leakage)

    def __post_init__(self):
        if self.preserve_sections is None:
            self.preserve_sections = []
        if self.forbidden_patterns is None:
            # Default forbidden patterns that directly include answers
            self.forbidden_patterns = [
                r'答案是.*',
                r'correct answer is.*',
                r'expected.*result.*is.*',
            ]


class PromptModifierGenerator(Generator):
    """
    Generate prompt variants via an LLM.

    Workflow:
    1. initialize: generate initial prompt variants
    2. evolve: generate improved variants based on evaluation results
    """

    def __init__(
        self,
        llm_client: Any,  # LLM client (e.g., DolphinLanguage)
        initial_size: int = 3,
        constraints: PromptModificationConstraint = None
    ):
        self.llm_client = llm_client
        self.initial_size = initial_size
        self.constraints = constraints or PromptModificationConstraint()
        self._original_content: str | None = None
        self._original_length: int = 0

    def initialize(self, target: str, context: dict) -> list[Candidate]:
        """
        Generate initial prompt variants.

        Args:
            target: Original agent content (.dph file content).
            context: Context information:
                - agent_path: path to the agent file
                - failed_cases: failed test cases
                - knowledge: domain knowledge
                - error_types: error types (from SemanticJudge)

        Returns:
            Initial candidates (using temp_file execution mode).
        """
        self._original_content = target
        self._original_length = len(target)

        # Extract the section to optimize
        section_to_optimize = self._extract_section(target, self.constraints.target_section)

        # Analyze error types and generate targeted improvement directions
        error_types = context.get('error_types', [])
        improvement_directions = self._generate_improvement_directions(error_types, context)

        # Generate initial variants
        candidates = []
        for i, direction in enumerate(improvement_directions[:self.initial_size]):
            modified_content = self._generate_variant(
                original=target,
                section=section_to_optimize,
                direction=direction,
                context=context
            )

            # Validate modification
            if self._validate_modification(modified_content, context):
                # Create a temp-file execution context
                agent_path = Path(context.get('agent_path', 'agent.dph'))
                execution_context = ExecutionContext(
                    mode='temp_file',
                    base_path=agent_path.parent,
                    file_template=str(agent_path.name),
                    cleanup_policy='auto',
                    variables={}
                )

                candidates.append(Candidate(
                    content=modified_content,
                    execution_context=execution_context,
                    metadata={
                        'direction': direction,
                        'iteration': 0,
                        'modification_type': 'initial'
                    }
                ))

        return candidates

    def evolve(
        self,
        selected: list[Candidate],
        evaluations: list[EvaluationResult],
        context: dict
    ) -> list[Candidate]:
        """
        Evolve new prompt variants based on evaluation results.

        Strategy:
        1. Extract improvement patterns from the best candidate
        2. Incorporate SemanticJudge feedback
        3. Generate refined variants
        """
        if not selected:
            return []

        # Find the best candidate
        best_idx = max(range(len(evaluations)), key=lambda i: evaluations[i].score)
        best_candidate = selected[best_idx]
        best_eval = evaluations[best_idx]

        # Extract improvement patterns
        patterns = self._extract_improvement_patterns(best_candidate, best_eval)

        # If errors remain, generate targeted improvements
        if best_eval.detail and hasattr(best_eval.detail, 'error_types'):
            remaining_errors = best_eval.detail.error_types
            new_directions = self._generate_improvement_directions(remaining_errors, context)
        else:
            # Try further refinement
            new_directions = self._generate_refinement_directions(best_candidate, context)

        # Generate next-generation candidates
        new_candidates = []
        for direction in new_directions[:len(selected)]:
            modified_content = self._generate_variant(
                original=best_candidate.content,
                section=self._extract_section(
                    best_candidate.content,
                    self.constraints.target_section
                ),
                direction=direction,
                context=context,
                parent_patterns=patterns
            )

            if self._validate_modification(modified_content, context):
                agent_path = Path(context.get('agent_path', 'agent.dph'))
                execution_context = ExecutionContext(
                    mode='temp_file',
                    base_path=agent_path.parent,
                    file_template=str(agent_path.name),
                    cleanup_policy='auto'
                )

                new_candidates.append(Candidate(
                    content=modified_content,
                    execution_context=execution_context,
                    parent_id=best_candidate.id,
                    metadata={
                        'direction': direction,
                        'iteration': best_candidate.metadata.get('iteration', 0) + 1,
                        'modification_type': 'evolved',
                        'parent_score': best_eval.score
                    }
                ))

        return new_candidates

    def _extract_section(self, content: str, section: str) -> str:
        """Extract a specific section from .dph content."""
        if section == 'all':
            return content

        # Simplified .dph parsing (should be more robust in production)
        if section == 'system':
            # Extract system prompt
            match = re.search(r'system\s*=\s*"""(.*?)"""', content, re.DOTALL)
            if match:
                return match.group(1)
        elif section == 'tools':
            # Extract tools section
            match = re.search(r'tools\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if match:
                return match.group(1)

        return content

    def _generate_improvement_directions(
        self,
        error_types: list[str],
        context: dict
    ) -> list[str]:
        """Generate improvement directions from error types."""
        directions = []

        # Map error types to improvement directions
        error_to_direction = {
            'logic_error': '加强逻辑推理能力，明确步骤',
            'tool_misuse': '优化工具使用说明和示例',
            'missing_info': '补充必要的领域知识',
            'wrong_format': '强化输出格式约束',
            'insufficient_context': '改进上下文理解指导'
        }

        for error_type in error_types:
            if error_type in error_to_direction:
                directions.append(error_to_direction[error_type])

        # If no specific errors are provided, use generic improvement directions
        if not directions:
            directions = [
                '优化角色定义和任务描述',
                '增强约束条件和注意事项',
                '改进示例和说明'
            ]

        return directions

    def _generate_refinement_directions(
        self,
        candidate: Candidate,
        context: dict
    ) -> list[str]:
        """Generate further refinement directions."""
        return [
            '进一步精简和明确表达',
            '增强关键步骤的说明',
            '优化信息组织结构'
        ]

    def _generate_variant(
        self,
        original: str,
        section: str,
        direction: str,
        context: dict,
        parent_patterns: list[str] = None
    ) -> str:
        """
        Generate a prompt variant using an LLM.

        This uses the LLM to generate a new version based on the improvement direction.
        """
        # Build the LLM prompt
        modification_prompt = f"""你是一个 Agent Prompt 优化专家。

当前任务：根据以下改进方向，优化 Agent 的 prompt。

原始内容：
```
{section}
```

改进方向：{direction}

业务知识：
{context.get('knowledge', '(无)')}

要求：
1. 保持原有功能不变
2. 针对性地应用改进方向
3. 确保表达清晰、简洁
4. 不要泄露测试答案
5. 长度不超过原内容的 130%

请直接输出优化后的内容，不要包含其他说明。
"""

        # Call LLM generation (requires a real LLM client)
        # For demo purposes, return a mock variant
        modified_section = self._mock_llm_generate(modification_prompt, direction, section)

        # Replace the corresponding section in the original content
        if self.constraints.target_section == 'system':
            modified_content = re.sub(
                r'system\s*=\s*""".*?"""',
                f'system = """{modified_section}"""',
                original,
                flags=re.DOTALL
            )
        else:
            modified_content = original.replace(section, modified_section)

        return modified_content

    def _mock_llm_generate(self, prompt: str, direction: str, section: str) -> str:
        """
        Mock LLM generation (should call a real LLM in production).

        TODO: Replace with a real LLM call.
        """
        # Simple mock: return the original content as-is
        # In real usage, this would call an LLM API to generate optimized content
        return section.strip()

    def _extract_improvement_patterns(
        self,
        candidate: Candidate,
        evaluation: EvaluationResult
    ) -> list[str]:
        """Extract improvement patterns from the best candidate."""
        patterns = []

        # Extract patterns based on metadata and content
        if candidate.metadata.get('direction'):
            patterns.append(candidate.metadata['direction'])

        # Extract keywords from action_vector if available
        if evaluation.detail and hasattr(evaluation.detail, 'action_vector'):
            action_vector = evaluation.detail.action_vector
            if action_vector:
                patterns.extend(action_vector[:3])  # Take first 3 suggestions

        return patterns

    def _validate_modification(self, content: str, context: dict) -> bool:
        """
        Validate a modification.

        Checks:
        1. Length limits
        2. Forbidden patterns
        3. Basic structure
        """
        # 1. Check length
        if len(content) > self._original_length * self.constraints.max_length_ratio:
            return False

        # 2. Check forbidden patterns (prevent answer leakage)
        expected_answer = context.get('expected', '')
        if expected_answer and expected_answer.lower() in content.lower():
            # If the modified content includes the answer, reject it
            return False

        for pattern in self.constraints.forbidden_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False

        # 3. Basic structure check (.dph should contain required structure)
        # Relaxed: accept if it contains system/def/triple-quoted strings
        has_structure = (
            'system' in content or
            'def ' in content or
            '"""' in content  # At least a triple-quoted string
        )

        if not has_structure:
            return False

        return True


def create_default_prompt_modifier(
    llm_client: Any,
    target_section: str = 'system',
    initial_size: int = 3
) -> PromptModifierGenerator:
    """Create a PromptModifierGenerator with default settings."""
    constraints = PromptModificationConstraint(
        target_section=target_section,
        max_length_ratio=1.3,
        preserve_sections=[],
        forbidden_patterns=[
            r'答案是.*',
            r'correct answer is.*',
            r'expected.*result.*is.*',
        ]
    )

    return PromptModifierGenerator(
        llm_client=llm_client,
        initial_size=initial_size,
        constraints=constraints
    )
