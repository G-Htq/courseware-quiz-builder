# -*- coding: utf-8 -*-
"""test_quiz_validation.py - 层A 结构质检 + 图片安全 + 层B 证据定位核验。

v2.1 变更：原 test_real_png_passes 是漏洞用例（引用 ../materials/... 穿越
路径曾被放行，审计 V2-03），修复后改为「穿越拒绝」断言，并新增目录内
合法引用正例 quiz_img_ok.json。
"""
import unittest

from _common import OUT, QUIZD, ensure_fixtures, toolkit


class TestLayerAEvidenceAndImages(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def verify(self, quiz):
        return toolkit(["verify", str(QUIZD / quiz)])

    # ---- 层B 证据定位 ----

    def test_good_quiz_passes(self):
        r = self.verify("quiz_ev.json")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("定位通过（精确）×4", r.stdout)

    def test_bad_source_rejected(self):
        r = self.verify("quiz_bad_source.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("来源不存在", r.stdout)

    def test_bad_segment_rejected(self):
        r = self.verify("quiz_bad_segment.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("片段不存在", r.stdout)

    def test_bad_quote_rejected(self):
        r = self.verify("quiz_bad_quote.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("引用未定位", r.stdout)

    def test_bad_status_rejected(self):
        r = self.verify("quiz_bad_status.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("evidence_status", r.stdout)

    def test_partial_evidence_rejected(self):
        r = self.verify("quiz_bad_partial.json")
        self.assertEqual(r.returncode, 1)
        self.assertIn("缺少 source_quote", r.stdout)

    def test_no_manifest_skips_honestly(self):
        """未提供任何 manifest 时：明确说明跳过，不伪装已验证。"""
        import json
        data = json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))
        data.pop("manifest", None)
        quiz_alone = OUT / "quiz_alone.json"
        quiz_alone.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        r = toolkit(["verify", str(quiz_alone)])
        self.assertIn("跳过", r.stdout)
        self.assertIn("不构成", r.stdout)
        # 显式引用的 manifest 路径不存在 → 应明确报错（returncode 2）而非崩溃/静默跳过
        data["manifest"] = "manifest.json"
        quiz_ref = OUT / "quiz_ref.json"
        quiz_ref.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        r2 = toolkit(["verify", str(quiz_ref)])
        self.assertEqual(r2.returncode, 2)
        self.assertIn("无法读取 manifest", r2.stdout)
        self.assertNotIn("Traceback", r2.stdout + r2.stderr)

    # ---- 层A 图片安全 ----

    def test_fake_png_magic_rejected(self):
        """目录内伪 PNG（魔数不符）→ 拒绝（夹具由 make_quiz_fixtures.py 生成）。"""
        r = toolkit(["validate", str(QUIZD / "quiz_fake_png.json")])
        self.assertEqual(r.returncode, 1)
        self.assertIn("魔数校验失败", r.stdout)

    def test_parent_escape_rejected(self):
        """v2.1（V2-03）：../materials/... 穿越 → 路径越界拒绝。"""
        r = toolkit(["validate", str(QUIZD / "quiz_real_png.json")])
        self.assertEqual(r.returncode, 1)
        self.assertIn("路径越界", r.stdout)

    def test_in_tree_image_ok(self):
        """目录内 imgs/real.png 合法引用 → validate 通过。"""
        r = toolkit(["validate", str(QUIZD / "quiz_img_ok.json")])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_explain_answer_contradiction_rejected(self):
        """v2.1：解析结论（故选B）与 answer（A）矛盾 → 拒绝（rule_id 在 build 门禁/报告中验证）。"""
        r = toolkit(["validate", str(QUIZD / "quiz_contradict.json")])
        self.assertEqual(r.returncode, 1)
        self.assertIn("矛盾", r.stdout)

    def test_legacy_quiz_compatible(self):
        """旧格式（无证据字段）兼容：validate 通过但提示无法来源核验。"""
        r = toolkit(["validate", str(QUIZD / "quiz_legacy.json")])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("未携带证据链字段", r.stdout)

    def test_duplicate_and_bad_answer_still_caught(self):
        import json
        bad = json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))
        bad["title"] = "答案越界测试"
        bad["questions"][0]["answer"] = [9]
        from _common import write_quiz
        p = write_quiz("quiz_bad_range.json", bad)
        r = toolkit(["validate", str(p)])
        self.assertEqual(r.returncode, 1)
        self.assertIn("超出选项范围", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
