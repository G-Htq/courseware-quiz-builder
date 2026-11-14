#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_zip.py - 构建 dist/courseware-quiz-builder-v2.2.zip（正斜杠条目，排除缓存）。"""
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parent / "skill-src" / "courseware-quiz-builder"
DIST = Path(__file__).resolve().parent / "dist"
DIST.mkdir(exist_ok=True)
OUT = DIST / "courseware-quiz-builder-v2.2.zip"

EXCLUDE_DIRS = {"__pycache__", ".temp"}
count = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(SRC.rglob("*")):
        if p.is_file():
            if any(part in EXCLUDE_DIRS for part in p.parts):
                continue
            rel = p.relative_to(SRC).as_posix()   # 强制正斜杠
            z.write(p, rel)
            count += 1
print(f"OK {OUT.name}: {count} files, {OUT.stat().st_size} bytes")
