#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SemanticJudge: produce "semantic gradient" diagnostics and candidate injects from cross-run failure analysis.

Implementation:
Reuse dolphin CLI and a dedicated agent (semantic_judge.dph). Inputs include analysis_content
(cross-run summary), a redacted version of expected, actual output, and optional domain knowledge.
Outputs a structured JSON containing score, error_types, action_vector, candidate_injects, rationale, etc.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime
import subprocess

from dolphin.core.common.constants import (
    DOLPHIN_VARIABLES_OUTPUT_START,
    DOLPHIN_VARIABLES_OUTPUT_END,
)


class SemanticJudge:
    def __init__(self, data_loader, simulation_logs_dir=None):
        """
        Args:
            data_loader: ExperimentAnalyzer instance (data context and dolphin entrypoint).
            simulation_logs_dir: Optional simulation_logs directory; if provided, it will be preferred.
        """
        self.data_loader = data_loader
        self.root_dir = data_loader.root_dir
        self.dolphin_cmd = data_loader.dolphin_cmd
        self.reports_dir = data_loader.reports_dir

        # Prefer simulation_logs_dir when provided; otherwise fall back to reports_dir.
        # This preserves backward compatibility while allowing better log organization.
        if simulation_logs_dir:
            # Ensure simulation_logs directory exists
            Path(simulation_logs_dir).mkdir(exist_ok=True)
            self.log_dir = simulation_logs_dir
            print(f"🔧 SemanticJudge日志将保存到: {simulation_logs_dir}")
        else:
            self.log_dir = self.reports_dir
            print(f"🔧 SemanticJudge日志将保存到: {self.reports_dir} (向后兼容模式)")

    @staticmethod
    def redact_expected(expected: str) -> str:
        """Redact expected output to avoid leaking exact entities/numbers.

        - Percentages -> [PCT]
        - Consecutive digits (>=2) -> [NUM]
        - Single letters/options (A/B/C, etc.) are kept but should not be cited as the final answer
        """
        if not expected:
            return ""
        s = str(expected)
        s = re.sub(r"\d+%", "[PCT]", s)
        s = re.sub(r"\d{2,}", "[NUM]", s)
        return s

    def evaluate(
        self, analysis_content: str, expected: str, actual: str, knowledge: str = ""
    ) -> dict | None:
        """
        Run SemanticJudge and return diagnostic JSON.

        Suggested fields:
          - score: 0~1
          - correct: bool
          - error_types: list[str]
          - missing_constraints: list[str]
          - action_vector: list[str]
          - candidate_injects: list[str]
          - rationale: str
        """
        judge_file = Path(__file__).parent / "dolphins" / "semantic_judge.dph"
        if not judge_file.exists():
            raise FileNotFoundError(f"semantic_judge.dph 不存在: {judge_file}")

        expected_redacted = self.redact_expected(expected)

        cmd_parts = [
            str(self.dolphin_cmd),
            "--folder",
            Path(__file__).parent / "dolphins",
            "--agent",
            "semantic_judge",
            "--analysis_content",
            analysis_content or "",
            "--expected_redacted",
            expected_redacted or "",
            "--actual_output",
            actual or "",
            "--busi_knowledge",
            knowledge or "",
            "--output-variables",
            "gradient",
        ]

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"semantic_judge_{ts}.log"

        with open(log_file, "w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd_parts,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=str(self.root_dir),
                text=True,
            )

        if result.returncode != 0:
            # Do not fallback; surface failure to caller
            return None

        # Parse DOLPHIN_VARIABLES_OUTPUT section from the log
        try:
            with open(log_file, "r", encoding="utf-8") as rf:
                output = rf.read()
            gradient_str = self._extract_var_from_log(output, var_name="gradient")
            if not gradient_str:
                return None
            gradient = json.loads(gradient_str)
            # Basic field defaults
            gradient.setdefault("score", 0.0)
            gradient.setdefault("correct", False)
            gradient.setdefault("error_types", [])
            gradient.setdefault("missing_constraints", [])
            gradient.setdefault("action_vector", [])
            gradient.setdefault("candidate_injects", [])
            gradient.setdefault("rationale", "")
            return gradient
        except Exception:
            return None

    def evaluate_enhanced(
        self, evaluate_context: dict, knowledge: str = ""
    ) -> dict | None:
        """
        Enhanced semantic evaluation that accepts a full evaluation context.
        """
        judge_file = Path(__file__).parent / "dolphins" / "semantic_judge.dph"
        if not judge_file.exists():
            raise FileNotFoundError(f"semantic_judge.dph 不存在: {judge_file}")

        # Extract key information
        analysis_content = evaluate_context.get("analysis_content", "")
        predicted_result = evaluate_context.get("predicted_result", "")
        benchmark_context = self._prepare_benchmark_context(evaluate_context)

        # Extract expected output information
        expected_info = evaluate_context.get("expected_info", {})
        expected_redacted = self.redact_expected(expected_info.get("raw_expected", ""))

        cmd_parts = [
            str(self.dolphin_cmd),
            "--folder",
            Path(__file__).parent / "dolphins",
            "--agent",
            "semantic_judge",
            "--analysis_content",
            analysis_content or "",
            "--benchmark_context",
            benchmark_context or "",
            "--expected_redacted",
            expected_redacted or "",
            "--expected_info",
            json.dumps(expected_info, ensure_ascii=False),
            "--actual_output",
            predicted_result or "",
            "--busi_knowledge",
            knowledge or "",
            "--output-variables",
            "gradient",
        ]

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"semantic_judge_enhanced_{ts}.log"

        with open(log_file, "w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd_parts,
                stdout=f,
                stderr=subprocess.STDOUT,
                cwd=str(self.root_dir),
                text=True,
            )

        if result.returncode != 0:
            return None

        # Parse DOLPHIN_VARIABLES_OUTPUT section from the log
        try:
            with open(log_file, "r", encoding="utf-8") as rf:
                output = rf.read()
            gradient_str = self._extract_var_from_log(output, var_name="gradient")
            if not gradient_str:
                return None
            gradient = json.loads(gradient_str)
            # Basic field defaults
            gradient.setdefault("score", 0.0)
            gradient.setdefault("correct", False)
            gradient.setdefault("error_types", [])
            gradient.setdefault("missing_constraints", [])
            gradient.setdefault("action_vector", [])
            gradient.setdefault("candidate_injects", [])
            gradient.setdefault("rationale", "")
            return gradient
        except Exception:
            return None

    def _prepare_benchmark_context(self, evaluate_context: dict) -> str:
        return json.dumps(
            evaluate_context.get("benchmark_item", {}), ensure_ascii=False
        )

    @staticmethod
    def _extract_var_from_log(log_content: str, var_name: str) -> str | None:
        start_marker = DOLPHIN_VARIABLES_OUTPUT_START
        end_marker = DOLPHIN_VARIABLES_OUTPUT_END
        s = log_content.find(start_marker)
        if s == -1:
            return None
        e = log_content.find(end_marker, s)
        if e == -1:
            return None
        json_content = log_content[s + len(start_marker) : e].strip()
        try:
            variables = json.loads(json_content)
        except Exception:
            return None
        val = variables.get(var_name)
        # If the variable is already a structured object (dict/list),
        # return its JSON string so the caller can json.loads it.
        if isinstance(val, (dict, list)):
            try:
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                return None
        if isinstance(val, str):
            return val
        return None
