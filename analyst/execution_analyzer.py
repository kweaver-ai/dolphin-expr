#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution analyzer

Analyzes an agent's execution process, including:
- Preprocessing experiment logs
- Fetching benchmark data
- Calling analysis.dph for execution analysis
- Comparing the agent trajectory with expected results
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
import time

from dolphin.core.common.constants import (
    DOLPHIN_VARIABLES_OUTPUT_START,
    DOLPHIN_VARIABLES_OUTPUT_END,
)

try:
    from .base_analyzer import BaseAnalyzer
except ImportError:
    from base_analyzer import BaseAnalyzer


class ExecutionAnalyzer(BaseAnalyzer):
    """Execution analyzer."""

    def __init__(self, data_loader):
        """
        Initialize the execution analyzer.

        Args:
            data_loader: An ExperimentDataLoader instance.
        """
        # Initialize the parent class
        super().__init__(data_loader)

    def analyze_execution(
        self, run_name, case_num, save_to_file=True, knowledge_path=None
    ):
        """
        Analyze the agent execution process for a single case.

        Args:
            run_name: Run name.
            case_num: Case number.
            save_to_file: Whether to save results to a file.
            knowledge_path: Path to a knowledge file or directory.

        Returns:
            Analysis result text (or None on failure).
        """
        print(f"🔍 开始分析智能体执行过程 - Run: {run_name}, Case: {case_num}")
        if knowledge_path:
            print(f"📚 加载业务知识: {knowledge_path}")

        # Preprocess experiment logs and write to a temporary file
        processed_log_path = self._preprocess_execution_log(run_name, case_num)
        if not processed_log_path:
            return None
        print(f"✅ 成功预处理执行日志")

        # Fetch benchmark data
        benchmark = self._get_benchmark_data(case_num)
        if not benchmark:
            return None
        print(f"✅ 成功获取benchmark数据 (question_id: {benchmark['question_id']})")

        # Load domain knowledge
        knowledge_content = ""
        if knowledge_path:
            print(f"🔍 正在加载业务知识: {knowledge_path}")
            knowledge_content = self._load_knowledge(knowledge_path, run_name)
            if knowledge_content:
                print(f"✅ 成功加载业务知识 ({len(knowledge_content)} 字符)")
            else:
                print("⚠️ 业务知识加载失败")

        # Run agent analysis
        print(f"🔧 调用 analysis.dph，知识内容长度: {len(knowledge_content)}")
        analysis_result = self._run_execution_analysis(
            processed_log_path, benchmark, knowledge_content
        )
        if not analysis_result:
            return None

        print("✅ 智能体执行分析完成")

        # Save analysis result to disk
        if save_to_file and analysis_result:
            self._save_analysis_result(run_name, case_num, analysis_result)

        # Clean up temporary files
        try:
            processed_log_path.unlink()
        except:
            pass

        return analysis_result

    def _preprocess_execution_log(self, run_name, case_num):
        """Preprocess execution logs and extract key execution signals."""
        # Use the new log file path format
        case_num_padded = f"{int(case_num):03d}"
        log_file = (
            self.root_dir
            / "env"
            / self.experiment_name
            / run_name
            / "console"
            / f"case_{case_num_padded}.log"
        )

        # If the new path doesn't exist, try the legacy log file path format
        if not log_file.exists():
            run_num = run_name.split("_")[-1].lstrip("0") or "0"
            case_num_clean = case_num.lstrip("0") or "0"
            log_file = (
                self.root_dir
                / "env"
                / self.experiment_name
                / run_name
                / "log"
                / f"experiment_run_{run_num}_case_{case_num_clean}.log"
            )

        if not log_file.exists():
            print(f"错误: 执行日志文件不存在: {log_file}")
            return None

        try:
            # Read the full execution log
            with open(log_file, "r", encoding="utf-8") as f:
                full_content = f.read()

            # Keep the main trajectory content before "Final result:"
            content = full_content
            final_result_pos = content.find("Final result:")
            if final_result_pos != -1:
                content = content[:final_result_pos]

            content = content.strip()

            # Extract key execution signals as META data
            meta_lines = []
            meta_lines.append("\n\n==== EXECUTION META (extracted) ====")

            # 1) Extract the agent's final answer
            try:
                ans_match = re.search(
                    r"Final result:\s*\{.*?'answer':\s*'(.*?)',\s*'think'",
                    full_content,
                    re.DOTALL,
                )
                if ans_match:
                    raw_answer = ans_match.group(1)
                    clean_answer = raw_answer.replace("\\n", "\n")
                    meta_lines.append("[agent_answer]\n" + clean_answer.strip())
            except Exception:
                pass

            # 2) Extract the final SQL query (if present)
            try:
                # Remove ANSI color codes
                ansi_escape = re.compile(r"\x1B(?:[@-Z\\\\-_]|\[[0-?]*[ -/]*[@-~])")
                no_ansi = ansi_escape.sub("", full_content)

                # Match the last SQL query
                sql_matches = list(
                    re.finditer(r'"sql"\s*:\s*"(.*?)"', no_ansi, re.DOTALL)
                )
                if sql_matches:
                    last_sql = sql_matches[-1].group(1)
                    last_sql = last_sql.replace("\\n", "\n")
                    meta_lines.append("[executed_sql]\n" + last_sql.strip())
            except Exception:
                pass

            # 3) Extract the tool call chain
            try:
                tool_calls = []
                tool_matches = re.finditer(r"🛠️\s*(\w+):", content)
                for match in tool_matches:
                    tool_calls.append(match.group(1))
                if tool_calls:
                    meta_lines.append("[tool_chain]\n" + " -> ".join(tool_calls))
            except Exception:
                pass

            # 4) Extract thinking content (if present)
            try:
                think_match = re.search(r"'think':\s*'(.*?)'", full_content, re.DOTALL)
                if think_match:
                    think_content = think_match.group(1).replace("\\n", "\n")
                    # Keep only the first 500 characters to avoid overly long output
                    if len(think_content) > 500:
                        think_content = think_content[:500] + "..."
                    meta_lines.append("[agent_thinking]\n" + think_content.strip())
            except Exception:
                pass

            # Merge main content and META data
            if meta_lines and len(meta_lines) > 1:
                content = content + "\n" + "\n".join(meta_lines)

            # Save to a temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", delete=False, suffix=".log"
            ) as tmp_file:
                tmp_file.write(content)
                return Path(tmp_file.name)

        except Exception as e:
            print(f"错误: 预处理执行日志失败: {e}")
            return None

    # _get_benchmark_data method moved to BaseAnalyzer

    def _run_execution_analysis(
        self, execution_log_path, benchmark, knowledge_content=""
    ):
        """Call analysis.dph to analyze the agent execution."""
        analysis_log_file = None
        try:
            analysis_file = Path(__file__).parent / "dolphins" / "analysis.dph"
            if not analysis_file.exists():
                print(f"错误: analysis.dph文件不存在: {analysis_file}")
                return None

            # Build dolphin command
            cmd_parts = [
                str(self.dolphin_cmd),
                "--folder",
                Path(__file__).parent / "dolphins",
                "--agent",
                "analysis",
                "--exp_log_path",
                str(execution_log_path),
                "--benchmark",
                json.dumps(benchmark, ensure_ascii=False),
                "--busi_knowledge",
                knowledge_content,
                "--output-variables",
                "analysis_result",
            ]

            # Create a temporary log file
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            analysis_log_file = self.reports_dir / f"execution_analysis_{ts}.log"

            print("🔧 执行智能体分析...")

            # Run analysis command
            with open(analysis_log_file, "w", encoding="utf-8") as log_f:
                try:
                    result = subprocess.run(
                        cmd_parts,
                        stdout=log_f,
                        stderr=subprocess.STDOUT,
                        cwd=str(self.root_dir),
                        timeout=500,
                    )
                    exit_code = result.returncode
                except Exception as e:
                    exit_code = 1
                    print(f"Warning: Failed to run analysis command: {e}")
                    return None

            # Wait for the log file flush to complete
            time.sleep(0.1)

            if exit_code != 0:
                print(f"错误: 智能体执行分析失败，退出码: {exit_code}")
                return None

            # Read analysis result
            try:
                with open(analysis_log_file, "r", encoding="utf-8") as f:
                    log_content = f.read()

                # Extract analysis result
                extracted = self._extract_analysis_result(log_content)
                if extracted:
                    # Successfully extracted: clean up the temporary file
                    try:
                        analysis_log_file.unlink(missing_ok=True)
                    except:
                        pass
                    return extracted

                print("Warning: Failed to extract analysis result from log")
                return "智能体执行分析完成，但无法提取分析结果。"

            except Exception as e:
                print(f"Warning: Failed to read analysis log file: {e}")
                return None

        except Exception as e:
            print(f"错误: 执行智能体分析失败: {e}")
            return None
        finally:
            # Ensure the temporary log file is cleaned up
            if analysis_log_file and analysis_log_file.exists():
                try:
                    analysis_log_file.unlink(missing_ok=True)
                except:
                    pass

    def _extract_analysis_result(self, log_content: str):
        """Extract the analysis result from DOLPHIN_VARIABLES_OUTPUT markers."""
        if not log_content:
            return None

        try:
            # Use base helper to extract the variables output section
            variables_section = self._extract_result_from_log(
                log_content,
                DOLPHIN_VARIABLES_OUTPUT_START,
                DOLPHIN_VARIABLES_OUTPUT_END,
            )
            if not variables_section:
                return None

            # Parse JSON
            variables = json.loads(variables_section)

            # Extract analysis result
            analysis_result = variables.get("analysis_result", {}).get("answer")
            if isinstance(analysis_result, str) and analysis_result.strip():
                return analysis_result.strip()
            return None

        except Exception as e:
            print(f"Warning: Failed to extract analysis result from log: {e}")
            return None

    # _load_knowledge method moved to BaseAnalyzer

    def _save_analysis_result(self, run_name, case_num, analysis_result):
        """Save analysis result to a file."""
        # Use base helper to locate the run directory
        run_dir = self._find_run_directory(run_name)
        if not run_dir:
            return

        # Create analysis directory
        analysis_dir = run_dir / "analysis"
        analysis_dir.mkdir(exist_ok=True)

        # Write analysis result
        case_num_padded = f"{int(case_num):03d}"
        result_file = analysis_dir / f"case_{case_num_padded}.txt"

        try:
            with open(result_file, "w", encoding="utf-8") as f:
                f.write(f"=== Analysis Result for Case {case_num_padded} ===\n")
                f.write(f"Run: {run_name}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("\n" + "=" * 60 + "\n\n")
                f.write("===ANALYSIS_START===\n")
                f.write(analysis_result)
                f.write("\n===ANALYSIS_END===\n")
            print(f"💾 分析结果已保存到: {result_file}")
        except Exception as e:
            print(f"Warning: 保存分析结果失败: {e}")

    def load_analysis_result(self, run_name, case_num):
        """Load a previously saved analysis result."""
        run_dir = self._find_run_directory(run_name)
        if not run_dir:
            return None

        # Locate analysis result file
        case_num_padded = f"{int(case_num):03d}"
        result_file = run_dir / "analysis" / f"case_{case_num_padded}.txt"

        if not result_file.exists():
            return None

        try:
            with open(result_file, "r", encoding="utf-8") as f:
                content = f.read()
                # First try to extract from ===ANALYSIS_START=== and ===ANALYSIS_END===
                start_marker = "===ANALYSIS_START==="
                end_marker = "===ANALYSIS_END==="
                start_pos = content.find(start_marker)
                if start_pos != -1:
                    end_pos = content.find(end_marker, start_pos)
                    if end_pos != -1:
                        # Extract content between markers
                        return content[start_pos + len(start_marker) : end_pos].strip()

                # Fall back to legacy format if markers are missing
                separator = "=" * 60 + "\n\n"
                if separator in content:
                    return content.split(separator, 1)[1]
                return content
        except Exception as e:
            print(f"Warning: 加载分析结果失败: {e}")
            return None
