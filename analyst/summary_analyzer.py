#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summary analyzer

Calls summary.dph to analyze analysis results under a given run directory, including:
- Reading analysis folder content under the run directory
- Calling summary.dph for aggregated analysis
- Writing analysis results to a file
"""

import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
import time

try:
    from .base_analyzer import BaseAnalyzer
except ImportError:
    from base_analyzer import BaseAnalyzer


class SummaryAnalyzer(BaseAnalyzer):
    """Summary analyzer."""

    def __init__(self, data_loader):
        """
        Initialize the summary analyzer.

        Args:
            data_loader: An ExperimentDataLoader instance.
        """
        # Initialize the parent class
        super().__init__(data_loader)

    def analyze_summary(self, run_name, knowledge_path=None):
        """
        Run summary analysis for the given run's analysis results.

        Args:
            run_name: Run name.
            knowledge_path: Path to a knowledge file or directory.

        Returns:
            Summary analysis result text (or None on failure).
        """
        print(f"🔍 开始进行Summary分析 - Run: {run_name}")

        # Build analysis folder path
        run_path = (
            self.root_dir / "env" / self.experiment_name / run_name
        )
        analysis_path = run_path / "analysis"

        if not analysis_path.exists():
            print(f"错误: analysis目录不存在: {analysis_path}")
            return None

        print(f"✅ 找到analysis目录: {analysis_path}")

        # Load domain knowledge
        knowledge_content = ""
        if knowledge_path:
            knowledge_content = self._load_knowledge(knowledge_path, run_name)
            if knowledge_content:
                print(f"✅ 成功加载业务知识 ({len(knowledge_content)} 字符)")
            else:
                print("⚠️ 业务知识加载失败")

        # Run summary analysis
        summary_result = self._run_summary_analysis(analysis_path, knowledge_content)
        if not summary_result:
            return None

        print("✅ Summary分析完成")

        # Write result file
        result_file = self._write_summary_result(run_name, summary_result)
        if result_file:
            print(f"✅ Summary结果已写入: {result_file}")

        return summary_result

    def _run_summary_analysis(self, folder_path, knowledge_content=""):
        """Call summary.dph to run analysis."""
        summary_log_file = None
        try:
            summary_file = Path(__file__).parent / "dolphins" / "summary.dph"
            if not summary_file.exists():
                print(f"错误: summary.dph文件不存在: {summary_file}")
                return None

            # Parse analysis file contents outside dolphin
            analysis_content = self._parse_analysis_files(folder_path)
            if not analysis_content:
                print(f"错误: 无法从分析目录提取内容: {folder_path}")
                return None

            print(f"✅ 成功提取 {len(analysis_content)} 字符的分析内容")

            # Build dolphin command (use analysis_content instead of folder_path)
            cmd_parts = [
                str(self.dolphin_cmd),
                "--folder",
                Path(__file__).parent / "dolphins",
                "--agent",
                "summary",
                "--analysis_content",
                analysis_content,
                "--busi_knowledge",
                knowledge_content,
                "--output-variables",
                "suggestions",
            ]

            # Create a temporary log file
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_log_file = self.reports_dir / f"summary_analysis_{ts}.log"

            print("🔧 执行Summary分析...")

            # Run analysis command
            with open(summary_log_file, "w", encoding="utf-8") as log_f:
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
                    print(f"Warning: Failed to run summary command: {e}")
                    return None

            # Wait for log file flush to complete
            time.sleep(0.1)

            if exit_code != 0:
                print(f"错误: Summary分析失败，退出码: {exit_code}")
                return None

            # Read analysis result
            try:
                with open(summary_log_file, "r", encoding="utf-8") as f:
                    log_content = f.read()

                # Extract analysis result
                extracted = self._extract_summary_result(log_content)
                if extracted:
                    # Successfully extracted: clean up the temporary file
                    try:
                        summary_log_file.unlink(missing_ok=True)
                    except:
                        pass
                    return extracted

                print("Warning: Failed to extract summary result from log")
                return "Summary分析完成，但无法提取分析结果。"

            except Exception as e:
                print(f"Warning: Failed to read summary log file: {e}")
                return None

        except Exception as e:
            print(f"错误: 执行Summary分析失败: {e}")
            return None
        finally:
            # Ensure the temporary log file is cleaned up
            if summary_log_file and summary_log_file.exists():
                try:
                    summary_log_file.unlink(missing_ok=True)
                except:
                    pass

    def _parse_analysis_files(self, folder_path):
        """
        Parse analysis content under the analysis folder.

        Args:
            folder_path: Analysis folder path.

        Returns:
            Parsed analysis content string.
        """
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists() or not folder_path.is_dir():
                print(f"错误: 分析目录不存在或不是目录: {folder_path}")
                return None

            analysis_contents = []
            analysis_files = []

            # Find all possible analysis result files
            for file_path in folder_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in [
                    ".txt",
                    ".log",
                    ".md",
                ]:
                    analysis_files.append(file_path)

            if not analysis_files:
                print(f"警告: 在 {folder_path} 中没有找到分析文件")
                return None

            print(f"🔍 找到 {len(analysis_files)} 个分析文件")

            # Parse analysis content from each file
            for file_path in sorted(analysis_files):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        file_content = f.read()

                    # Extract content between ===ANALYSIS_START=== and ===ANALYSIS_END===
                    extracted_content = self._extract_analysis_content(
                        file_content, file_path.name
                    )
                    if extracted_content:
                        analysis_contents.append(extracted_content)

                except Exception as e:
                    print(f"警告: 读取分析文件失败 {file_path}: {e}")
                    continue

            if not analysis_contents:
                print("警告: 没有找到有效的分析内容")
                return None

            # Merge all analysis contents
            combined_content = "\n\n" + "=" * 60 + "\n\n".join(analysis_contents)
            return combined_content

        except Exception as e:
            print(f"错误: 解析分析文件时出错: {e}")
            return None

    def _extract_analysis_content(self, file_content, file_name):
        """
        Extract content between ===ANALYSIS_START=== and ===ANALYSIS_END===.

        Args:
            file_content: File content.
            file_name: Filename (for logging).

        Returns:
            Extracted analysis content.
        """
        try:
            start_marker = "===ANALYSIS_START==="
            end_marker = "===ANALYSIS_END==="

            start_pos = file_content.find(start_marker)
            if start_pos == -1:
                print(f"警告: 在 {file_name} 中未找到开始标记 {start_marker}")
                return None

            end_pos = file_content.find(end_marker, start_pos)
            if end_pos == -1:
                print(f"警告: 在 {file_name} 中未找到结束标记 {end_marker}")
                return None

            # Extract content between markers
            content_start = start_pos + len(start_marker)
            extracted_content = file_content[content_start:end_pos].strip()

            if not extracted_content:
                print(f"警告: 在 {file_name} 中提取的分析内容为空")
                return None

            # Add a file marker
            formatted_content = f"=== From file: {file_name} ===\n{extracted_content}"
            print(f"✅ 从 {file_name} 提取了 {len(extracted_content)} 字符的分析内容")

            return formatted_content

        except Exception as e:
            print(f"错误: 从 {file_name} 提取分析内容时出错: {e}")
            return None

    def _extract_summary_result(self, log_content: str):
        """Extract summary result from DOLPHIN_VARIABLES_OUTPUT markers."""
        if not log_content:
            return None

        try:
            # Find variables output section
            start_marker = "=== DOLPHIN_VARIABLES_OUTPUT_START ==="
            end_marker = "=== DOLPHIN_VARIABLES_OUTPUT_END ==="

            start_pos = log_content.find(start_marker)
            if start_pos == -1:
                return None

            end_pos = log_content.find(end_marker, start_pos)
            if end_pos == -1:
                return None

            # Extract JSON content
            json_start = start_pos + len(start_marker)
            json_content = log_content[json_start:end_pos].strip()

            # Parse JSON
            variables = json.loads(json_content)

            # Extract suggestions
            suggestions = variables.get("suggestions", {}).get("answer")
            if isinstance(suggestions, str) and suggestions.strip():
                return suggestions.strip()
            return None

        except Exception as e:
            print(f"Warning: Failed to extract summary result from log: {e}")
            return None

    # _load_knowledge method moved to BaseAnalyzer

    def _write_summary_result(self, run_name, summary_result):
        """Write summary result to a file."""
        try:
            run_path = self._find_run_directory(run_name)
            if not run_path:
                print(f"Warning: 无法找到run目录以保存summary结果")
                return None

            summary_file = run_path / "summary_result.txt"

            # Write result
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write(f"Summary Analysis Result - {run_name}\n")
                f.write(
                    f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write("=" * 60 + "\n\n")
                f.write(summary_result)
                f.write("\n\n")

            return summary_file

        except Exception as e:
            print(f"错误: 写入summary结果文件失败: {e}")
            return None
