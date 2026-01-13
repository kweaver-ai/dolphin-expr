from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def resolve_path(p: str | None) -> Path | None:
    if not p:
        return None
    return Path(os.path.expandvars(os.path.expanduser(p))).resolve()


def ensure_dolphin_importable(*, dolphin_src: str | None = None) -> None:
    """
    Ensure `dolphin` is importable (the `src` directory of the main dolphin repo).

    Priority:
    1) Explicit argument `dolphin_src`
    2) Environment variable `DOLPHIN_SRC` (points to `dolphin/src`)
    3) Environment variable `DOLPHIN_REPO` (points to dolphin repo root; `/src` will be appended)
    """
    src = resolve_path(dolphin_src) or resolve_path(os.environ.get("DOLPHIN_SRC"))
    if not src:
        repo = resolve_path(os.environ.get("DOLPHIN_REPO"))
        if repo:
            src = repo / "src"

    if src and src.exists():
        src_str = str(src)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)

    try:
        import dolphin  # noqa: F401

        return
    except Exception:
        pass

    try:
        import dolphin  # noqa: F401

        return
    except Exception as e:
        raise ImportError(
            "无法导入 `dolphin`。请先安装/配置主 dolphin 仓库：\n"
            "- 方式1：设置环境变量 `DOLPHIN_SRC=/path/to/dolphin/src`\n"
            "- 方式2：设置环境变量 `DOLPHIN_REPO=/path/to/dolphin`（会自动使用 /src）\n"
            "- 方式3：在你的环境中安装 dolphin（可编辑安装）\n"
        ) from e


def find_dolphin_cli(*, repo_root: Path | None = None) -> str:
    """
    Find the dolphin CLI executable.

    Priority:
    1) Environment variable `DOLPHIN_BIN`
    2) (Optional) `repo_root/.venv/bin/dolphin`
    3) `dolphin` on `PATH`
    4) (Optional) `repo_root/bin/dolphin`
    """
    p = resolve_path(os.environ.get("DOLPHIN_BIN"))
    if p and p.exists():
        return str(p)

    if repo_root:
        venv_bin = (repo_root / ".venv" / "bin" / "dolphin").resolve()
        if venv_bin.exists():
            return str(venv_bin)

    which = shutil.which("dolphin")
    if which:
        return which

    if repo_root:
        local = (repo_root / "bin" / "dolphin").resolve()
        if local.exists():
            return str(local)

    raise FileNotFoundError(
        "找不到 dolphin CLI。请将 `dolphin` 加入 PATH，或设置 `DOLPHIN_BIN=/path/to/dolphin`。"
    )
