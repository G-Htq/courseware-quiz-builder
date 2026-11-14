# -*- coding: utf-8 -*-
"""run_tests.py - 课件智练 v2.2 自动化测试套件（聚合入口）。

运行方式:
  python tests/run_tests.py          # 全部测试
  python tests/run_tests.py -v       # 详细输出（unittest 自带 -v 亦可）
  python tests/make_fixtures.py      # 单独重建材料夹具
  python tests/make_edge_fixtures.py # 单独重建 Office 边界夹具
  python tests/make_quiz_fixtures.py # 单独重建 v2.1/v2.2 题库夹具

分文件结构（按类别）:
  test_extract_text.py        文档解析 + 诚实降级（17）
  test_office_edge_cases.py   Office 边界与混合批次隔离（5）
  test_quiz_validation.py     层A 质检/图片魔数 + 层B 证据定位（13）
  test_build_gate.py          强制门禁矩阵与报告契约（12）
  test_path_security.py       图片路径安全（11）
  test_skill_structure.py     Skill 静态规范（6）
  test_schema_v22.py          P0-4 非法 JSON 全矩阵（16）
  test_source_integrity_v22.py P0-5 反伪造/哈希完整性/短证据（12）
  test_release_gate_v22.py    P0-3/P0-6 三态门禁/原子化/退出码（12）
  test_security_v22.py        输出注入/不可信资源/材料提示注入（9）
  合计以 unittest 实际收集的测试方法为准（v2.2 合计 113，运行输出为准绳）

浏览器 E2E（考试状态机/错题复练/导入导出/草稿横幅/移动端）按
e2e/E2E_CHECKLIST.md（v2.1 轮）与 e2e/E2E_CHECKLIST_V22.md（v2.2 轮）
由真实浏览器执行并留存截图，不在本套件范围。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from _common import ensure_fixtures  # noqa: E402

if __name__ == "__main__":
    ensure_fixtures()
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT), pattern="test_*.py", top_level_dir=str(ROOT))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    print(f"\n=== 汇总: {total - failed}/{total} 通过 ===")
    sys.exit(0 if result.wasSuccessful() else 1)
