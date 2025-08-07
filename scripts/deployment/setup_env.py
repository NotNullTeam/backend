#!/usr/bin/env python3
"""从模板生成本地 .env，并注入随机密钥。

使用方法:
    python scripts/setup_env.py [模板路径] [输出路径]

如果路径被省略，默认值为:
    模板路径 = backend/.env.example
    输出路径  = backend/.env

该脚本不会覆盖已有的输出路径。
"""
from __future__ import annotations

import secrets
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent
DEFAULT_TEMPLATE = BACKEND_DIR / ".env.example"
DEFAULT_OUTPUT = BACKEND_DIR / ".env"


def random_token(length: int = 64) -> str:
    """Return hexadecimal token with given number of characters (length must be even)."""
    return secrets.token_hex(length // 2)


def main(template: Path, output: Path) -> None:
    if output.exists():
        print(f"[setup_env] {output} already exists – nothing to do.")
        return

    if not template.exists():
        sys.exit(f"[setup_env] Template file not found: {template}")

    # Copy template first so we keep comments/order
    shutil.copy(template, output)

    # Read file and inject secrets
    lines: list[str] = output.read_text().splitlines()
    new_lines: list[str] = []
    for line in lines:
        if line.startswith("SECRET_KEY="):
            line = f"SECRET_KEY={random_token(64)}"
        elif line.startswith("JWT_SECRET_KEY="):
            line = f"JWT_SECRET_KEY={random_token(64)}"
        new_lines.append(line)

    output.write_text("\n".join(new_lines) + "\n")
    print(f"[setup_env] Generated {output} with fresh secrets.")


if __name__ == "__main__":
    tpl = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TEMPLATE
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    main(tpl, out)
