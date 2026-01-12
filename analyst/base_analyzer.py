#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BaseAnalyzer: Base class for all analyzers

Provides shared data access and processing helpers:
- Benchmark data loading
- Knowledge file loading
- Result extraction
- Common initialization
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List


class BaseAnalyzer:
    """Base analyzer class."""

    def __init__(self, data_loader):
        """
        Initialize the base analyzer.

        Args:
            data_loader: An ExperimentDataLoader instance.
        """
        self.data_loader = data_loader
        self.experiment_path = data_loader.experiment_path
        self.experiment_name = data_loader.experiment_name
        self.root_dir = data_loader.root_dir
        self.dolphin_cmd = data_loader.dolphin_cmd
        self.reports_dir = data_loader.reports_dir

    def _get_benchmark_data(
        self,
        case_num: str,
        search_paths: Optional[List[Path]] = None,
        id_fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get benchmark data (generic implementation).

        Args:
            case_num: Case number.
            search_paths: Optional custom search paths (defaults to standard paths).
            id_fields: Optional list of ID field names used to match the case
                (defaults to ['test_id', 'id', 'question_id']).

        Returns:
            A benchmark dict, or None if not found.
        """
        # Default search paths
        if search_paths is None:
            case_num_padded = self._format_case_num(case_num)
            case_num_clean = case_num.lstrip("0") or "0"

            search_paths = [
                # Benchmark files under the experiment directory
                self.experiment_path / "benchmark" / f"test_{case_num_padded}.json",
                self.experiment_path / "benchmark" / f"test_{case_num_clean}.json",
                self.experiment_path / "tests" / f"test_{case_num_clean}.json",
                self.experiment_path / "tests" / f"case_{case_num_clean}.json",
                self.experiment_path / "benchmark.json",
                # Global benchmark directory
                self.root_dir / "benchmark" / "watsons" / "benchmark.json",
                self.root_dir / "benchmark" / "bird_dev" / "benchmark.json",
                # Benchmark directory relative to this file (convenient for different CWDs)
                Path(__file__).resolve().parent.parent
                / "benchmark"
                / "watsons"
                / "benchmark.json",
            ]

        # Default ID fields
        if id_fields is None:
            id_fields = ["test_id", "id", "question_id"]

        # Iterate over search paths
        for benchmark_file in search_paths:
            if not benchmark_file.exists():
                continue

            try:
                with open(benchmark_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle different data formats
                if isinstance(data, dict):
                    return data
                elif isinstance(data, list):
                    case_num_int = int(case_num.lstrip("0") or "0")
                    # Try matching by different ID fields
                    for item in data:
                        for id_field in id_fields:
                            if (
                                item.get(id_field) == case_num_int
                                or item.get(id_field) == case_num_int - 1
                            ):
                                return item
                    # If no matching item is found, continue to the next file
                    continue

            except Exception as e:
                print(f"读取benchmark文件失败 {benchmark_file}: {e}")
                continue

        print(f"错误: 未找到case {case_num}的benchmark数据")
        return None

    def _load_knowledge(
        self, knowledge_path: Optional[str], run_name: Optional[str] = None
    ) -> str:
        """
        Load domain knowledge.

        Args:
            knowledge_path: Path to a knowledge file or directory.
            run_name: Run name (used for relative path resolution).

        Returns:
            Knowledge content as a string.
        """
        if not knowledge_path:
            return ""

        # Path handling: for relative paths, prefer resolving within the experiment environment
        path = Path(knowledge_path)
        if not path.is_absolute():
            # If this is a relative path, try the following locations:
            possible_paths = []

            # 1) Run directory (if run_name is provided)
            if run_name:
                run_dir = self._find_run_directory(run_name)
                if run_dir:
                    run_path = run_dir / knowledge_path
                    if run_path.exists():
                        possible_paths.append(run_path)  # Highest priority

            # 2) Design directory (inferred from experiment name)
            design_base = (
                self.experiment_name.split("_")[0] if self.experiment_name else None
            )
            if design_base:
                design_path = (
                    self.root_dir
                    / "design"
                    / design_base
                    / knowledge_path
                )
                possible_paths.append(design_path)

            # 3) Experiment root, project root, and current working directory
            possible_paths.extend(
                [
                    self.experiment_path / knowledge_path,  # Experiment environment directory
                    self.root_dir / knowledge_path,  # Project root directory
                    Path.cwd() / knowledge_path,  # Current working directory
                ]
            )

            for test_path in possible_paths:
                if test_path.exists():
                    path = test_path
                    print(f"🔍 找到知识文件: {test_path}")
                    break
            else:
                print(f"警告: 找不到知识文件: {knowledge_path}")
                print(f"已尝试路径: {[str(p) for p in possible_paths]}")
                return ""

        try:
            if path.is_file():
                # Single file
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                print(f"✅ 成功加载知识文件: {path} ({len(content)} 字符)")
                return content
            elif path.is_dir():
                # Directory: merge all files
                all_content = []
                for file_path in path.rglob("*.md"):  # Only read Markdown files
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            file_content = f.read()
                            all_content.append(
                                f"=== {file_path.name} ===\n{file_content}\n"
                            )
                    except Exception as e:
                        print(f"警告: 读取文件 {file_path} 失败: {e}")

                combined_content = "\n".join(all_content)
                print(f"✅ 成功加载知识目录: {path} ({len(combined_content)} 字符)")
                return combined_content
            else:
                print(f"错误: 路径不存在: {path}")
                return ""
        except Exception as e:
            print(f"错误: 加载知识文件失败: {e}")
            return ""

    def _extract_result_from_log(
        self, log_content: str, start_marker: str, end_marker: str
    ) -> Optional[str]:
        """
        Extract a result from log content.

        Args:
            log_content: Log content.
            start_marker: Start marker.
            end_marker: End marker.

        Returns:
            Extracted result, or None if not found.
        """
        try:
            start_pos = log_content.find(start_marker)
            if start_pos == -1:
                return None

            end_pos = log_content.find(end_marker, start_pos)
            if end_pos == -1:
                return None

            # Extract content between markers
            content_start = start_pos + len(start_marker)
            extracted_content = log_content[content_start:end_pos].strip()

            return extracted_content if extracted_content else None

        except Exception as e:
            print(f"Warning: Failed to extract result from log: {e}")
            return None

    def _find_run_directory(self, run_name: str) -> Optional[Path]:
        """
        Find a run directory, supporting multiple naming formats.

        Args:
            run_name: Run name.

        Returns:
            Run directory path, or None if not found.
        """
        # Try different run directory naming formats
        possible_names = [
            run_name,  # Original name
            run_name.replace("run", "run_"),  # run001 -> run_001
            f"run_{run_name.replace('run', '').zfill(3)}",  # run1 -> run_001
            f"run_{run_name.replace('run_', '').zfill(3)}",  # run_1 -> run_001
        ]

        for name in possible_names:
            test_dir = self.experiment_path / name
            if test_dir.exists():
                return test_dir

        print(f"错误: 找不到run目录: {run_name}")
        print(f"已尝试: {', '.join(possible_names)}")
        return None

    def _format_case_num(self, case_num: str) -> str:
        """
        Format case number as a 3-digit, zero-padded string.

        Args:
            case_num: Case number as a string.

        Returns:
            Formatted case number (e.g., 001, 002, 123).
        """
        return f"{int(case_num):03d}"

    def _create_output_directory(self, subdir: str) -> Path:
        """
        Create an output directory.

        Args:
            subdir: Subdirectory name.

        Returns:
            The created directory path.
        """
        output_dir = self.experiment_path / subdir
        output_dir.mkdir(exist_ok=True, parents=True)
        return output_dir
