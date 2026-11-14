# -*- coding: utf-8 -*-
"""_common.py - 课件智练 v2.1/v2.2 测试套件共享工具：路径常量、子进程运行、夹具准备。

全部材料为合成测试文件（make_fixtures.py / make_edge_fixtures.py /
make_quiz_fixtures.py 生成），不含真实用户数据。
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # 课件智练v2/tests
WS = ROOT.parent                                # 课件智练v2
SKILL = Path(r"C:\Users\10579\.config\TeleAgent\users\v1_public_2119403696093126656\skills\courseware-quiz-builder")
STAGE = WS / "skill-src" / "courseware-quiz-builder"   # 开发事实源（暂存副本）
EXTRACT = STAGE / "scripts" / "extract_text.py"
TOOLKIT = STAGE / "scripts" / "quiz_toolkit.py"
TEMPLATE = STAGE / "assets" / "quiz-template.html"

MAT = ROOT / "materials"
QUIZD = ROOT / "quiz"
EDGE = ROOT / "edge"
OUT = ROOT / "e2e-auto"                          # build 输出（E2E 服务器目录）

PY = sys.executable

_prepared = False


def run(cmd, **kw):
    return subprocess.run([PY] + [str(c) for c in cmd], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", **kw)


def extract(files, extra=()):
    return run([EXTRACT] + list(files) + list(extra))


def toolkit(cmd_args):
    return run([TOOLKIT] + list(cmd_args))


def prepare_manifest():
    """重新生成合成材料与 source_manifest.json（幂等）。"""
    run([ROOT / "make_fixtures.py"])
    OUT.mkdir(exist_ok=True)
    r = extract([MAT / "good.pptx", MAT / "good.docx", MAT / "notes.md"],
                ["--out", str(QUIZD / "extracted.txt"),
                 "--manifest", str(QUIZD / "manifest.json"),
                 "--images", str(ROOT / "imgs-auto")])
    assert r.returncode == 0, f"manifest 提取失败: {r.stdout} {r.stderr}"


def ensure_fixtures():
    """一次性准备全部夹具（材料/manifest/边界文件/v2.1 题库夹具）。"""
    global _prepared
    if _prepared:
        return
    prepare_manifest()
    run([ROOT / "make_edge_fixtures.py"])
    run([ROOT / "make_quiz_fixtures.py"])
    _prepared = True


def write_quiz(name, data):
    """写题库夹具到 quiz/ 目录并返回路径。"""
    p = QUIZD / name
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return p
