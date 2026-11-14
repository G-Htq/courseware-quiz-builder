# -*- coding: utf-8 -*-
"""test_office_edge_cases.py - P0-1 Office 返回值契约与边界文件（v2.1 新增）。

背景（审计 V2-01）：v2.0 的早退分支返回三元组导致 5 类边界文件解包崩溃。
v2.1 契约：单文件失败必须 [失败]+明确原因，绝无 Traceback；
混合批次坏文件隔离，好文件照常入 manifest（error 字段记录原因）。
"""
import json
import unittest

from _common import EDGE, MAT, OUT, ensure_fixtures, extract

EDGE_FILES = [
    ("noslides.pptx", "幻灯片"),
    ("noxml.docx", "document"),
    ("emptybody.docx", "正文"),
    ("notext.pptx", "文本"),
    ("pptx_is_docx.pptx", "伪装"),
    ("pptx_is_text.pptx", "zip"),
]


class TestOfficeEdgeCases(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def _assert_clean_error(self, r):
        self.assertEqual(r.returncode, 1, f"应 exit 1:\n{r.stdout}\n{r.stderr}")
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertIn("[失败]", r.stdout)
        self.assertIn("成功 0/1", r.stdout)

    def test_edge_files_report_without_traceback(self):
        """6 类边界文件：明确 [失败]+原因，exit 1，无 Traceback。"""
        for fname, hint in EDGE_FILES:
            with self.subTest(fname=fname):
                r = extract([EDGE / fname])
                self._assert_clean_error(r)

    def test_edge_reasons_are_specific(self):
        """失败原因指向具体缺陷，而非笼统报错。"""
        cases = {
            "noslides.pptx": "未找到幻灯片内容",
            "noxml.docx": "document.xml",
            "pptx_is_docx.pptx": "伪装",
            "pptx_is_text.pptx": "zip 容器无法打开",
        }
        for fname, needle in cases.items():
            with self.subTest(fname=fname):
                r = extract([EDGE / fname])
                self.assertIn(needle, r.stdout)

    def test_mixed_batch_isolation(self):
        """坏文件（2 个）不破坏好文件（2 个）：manifest 各自记录 status 与 error。"""
        mp = OUT / "mixed_manifest.json"
        r = extract([EDGE / "noslides.pptx", MAT / "good.pptx",
                     EDGE / "noxml.docx", MAT / "good.docx"],
                    ["--manifest", str(mp)])
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertIn("成功 2/4", r.stdout)
        m = json.loads(mp.read_text(encoding="utf-8"))
        by_status = {}
        for s in m["sources"]:
            by_status.setdefault(s["status"], []).append(s)
        self.assertEqual(len(by_status.get("ok", [])), 2)
        self.assertEqual(len(by_status.get("failed", [])), 2)
        for s in by_status["ok"]:
            self.assertIsNone(s.get("error"))
            self.assertTrue(s["segments"])
        for s in by_status["failed"]:
            self.assertTrue(s.get("error"), "失败文件必须记录 error 原因")
        self.assertEqual(sorted(s["filename"] for s in by_status["ok"]),
                         sorted(["good.pptx", "good.docx"]))

    def test_all_bad_batch_still_writes_manifest(self):
        """全部失败：exit 1，manifest 仍生成且每个来源记录 error（诚实记录）。"""
        mp = OUT / "allbad_manifest.json"
        r = extract([EDGE / "noslides.pptx", EDGE / "pptx_is_text.pptx"],
                    ["--manifest", str(mp)])
        self.assertEqual(r.returncode, 1)
        m = json.loads(mp.read_text(encoding="utf-8"))
        self.assertEqual(len(m["sources"]), 2)
        self.assertTrue(all(s["status"] == "failed" and s["error"] for s in m["sources"]))

    def test_success_exit_code_zero(self):
        """全部成功：exit 0（契约回归）。"""
        r = extract([MAT / "good.pptx", MAT / "notes.md"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("成功 2/2", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
