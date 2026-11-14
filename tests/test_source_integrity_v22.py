# -*- coding: utf-8 -*-
"""test_source_integrity_v22.py - P0-5 来源一致性与反伪造核验。

覆盖（任务书 5.1/5.2/5.3）：
  B-REF-CONFLICT：source_ref 伪造页码 → FAIL（verify exit 1 / strict build BLOCKED）
  canonical 引用：展示以材料真实定位为准（HTML/MD 产物断言）
  来源文件完整性：--source-root EXECUTED/PASS；篡改 → B-SOURCE-HASH FAIL；
                 文件不可达 → UNAVAILABLE + "仅验证清单内一致性"
  短证据：B-QUOTE-THIN（已定位但证据不足）；片段内多次出现 → B-QUOTE-UNIQUE
"""
import json
import shutil
import unittest
from pathlib import Path

from _common import MAT, OUT, QUIZD, TEMPLATE, ensure_fixtures, toolkit

MF = QUIZD / "manifest.json"


class TestRefIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def test_fake_ref_rejected_by_verify(self):
        """V22-C：source_ref 写"课件第999页"（真实第 1 页）→ FAIL + canonical 展示 + 矛盾细节。"""
        r = toolkit(["verify", str(QUIZD / "quiz_fake_ref.json"), "--manifest", str(MF)])
        self.assertEqual(r.returncode, 1)
        self.assertIn("出处矛盾", r.stdout)
        self.assertIn("第999页", r.stdout)   # 矛盾细节：伪造页号在人类可读输出中明示
        self.assertIn("第1页", r.stdout)
        self.assertIn("课件《good.pptx》第1页", r.stdout)   # canonical 引用展示

    def test_fake_ref_blocks_strict_build(self):
        r = toolkit(["build", str(QUIZD / "quiz_fake_ref.json"), "-o", str(OUT),
                     "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("B-REF-CONFLICT", r.stdout)
        rep = json.loads((OUT / "validation-report.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["release_status"], "BLOCKED")
        self.assertTrue(any(f["rule_id"] == "B-REF-CONFLICT" for f in rep["findings"]))

    def test_canonical_ref_in_products(self):
        """正常题库产物：HTML 注入 canonical_ref 且 MD 出处用真实定位。"""
        r = toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(OUT),
                     "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 0, r.stdout)
        html = (OUT / "刷题页-合成材料·证据链测试题库.html").read_text(encoding="utf-8")
        self.assertIn('"canonical_ref"', html)
        self.assertIn("课件《good.pptx》第1页", html)
        md = (OUT / "题库-合成材料·证据链测试题库.md").read_text(encoding="utf-8")
        self.assertIn("课件《good.pptx》第1页", md)

    def test_bad_source_and_segment_still_rejected(self):
        r1 = toolkit(["verify", str(QUIZD / "quiz_bad_source.json"), "--manifest", str(MF)])
        self.assertEqual(r1.returncode, 1)
        self.assertIn("来源不存在", r1.stdout)
        r2 = toolkit(["verify", str(QUIZD / "quiz_bad_segment.json"), "--manifest", str(MF)])
        self.assertEqual(r2.returncode, 1)
        self.assertIn("片段不存在", r2.stdout)


class TestSourceFileIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def test_hash_verified_when_source_root_given(self):
        """--source-root 指向真实材料目录 → 完整性 EXECUTED 且通过。"""
        r = toolkit(["verify", str(QUIZD / "quiz_ev.json"), "--manifest", str(MF),
                     "--report", str(OUT / "hash-ok-report.json"), "--source-root", str(MAT)])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("来源完整性", r.stdout)
        rep = json.loads((OUT / "hash-ok-report.json").read_text(encoding="utf-8"))
        it = next(c for c in rep["checks"] if c["id"] == "source_file_integrity")
        self.assertEqual(it["execution"], "EXECUTED")
        self.assertEqual(it["result"], "PASS")
        self.assertIn("哈希一致", it["detail"])

    def test_hash_mismatch_detected(self):
        """材料被替换（同名字节不同）→ B-SOURCE-HASH FAIL，verify exit 1。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tampered = Path(td)
            for name in ("good.pptx", "good.docx", "notes.md"):
                data = bytearray((MAT / name).read_bytes())
                data[-1] = data[-1] ^ 0xFF   # 篡改末字节
                (tampered / name).write_bytes(bytes(data))
            r = toolkit(["verify", str(QUIZD / "quiz_ev.json"), "--manifest", str(MF),
                         "--report", str(OUT / "hash-bad-report.json"),
                         "--source-root", str(tampered)])
            self.assertEqual(r.returncode, 1)
            self.assertIn("SHA-256 与 manifest 记录不符", r.stdout)
            rep = json.loads((OUT / "hash-bad-report.json").read_text(encoding="utf-8"))
            self.assertTrue(any(f["rule_id"] == "B-SOURCE-HASH" for f in rep["findings"]))
            it = next(c for c in rep["checks"] if c["id"] == "source_file_integrity")
            self.assertEqual(it["execution"], "EXECUTED")
            self.assertEqual(it["result"], "FAIL")

    def test_hash_unavailable_stated_honestly(self):
        """原始文件不可达 → UNAVAILABLE + 明示"仅验证清单内一致性"。"""
        r = toolkit(["verify", str(QUIZD / "quiz_ev.json"), "--manifest", str(MF),
                     "--report", str(OUT / "hash-na-report.json")])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("仅验证清单内一致性", r.stdout)
        rep = json.loads((OUT / "hash-na-report.json").read_text(encoding="utf-8"))
        it = next(c for c in rep["checks"] if c["id"] == "source_file_integrity")
        self.assertEqual(it["execution"], "UNAVAILABLE")
        self.assertIn("未重新确认原文件未变化", it["detail"])

    def test_tampered_material_blocks_strict_build(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tampered = Path(td)
            data = bytearray((MAT / "good.pptx").read_bytes())
            data[-1] = data[-1] ^ 0xFF
            (tampered / "good.pptx").write_bytes(bytes(data))
            for name in ("good.docx", "notes.md"):
                shutil.copyfile(MAT / name, tampered / name)
            r = toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(OUT),
                         "--manifest", str(MF), "--html-template", str(TEMPLATE),
                         "--mode", "strict", "--source-root", str(tampered)])
            self.assertEqual(r.returncode, 1)
            self.assertIn("B-SOURCE-HASH", r.stdout)
            self.assertIn("拒绝产出", r.stdout)
            rep = json.loads((OUT / "validation-report.json").read_text(encoding="utf-8"))
            self.assertEqual(rep["release_status"], "BLOCKED")
            it = next(c for c in rep["checks"] if c["id"] == "source_file_integrity")
            self.assertEqual(it["result"], "FAIL")


class TestQuoteQuality(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def test_thin_quote_flagged(self):
        """V22-D：1-2 字引用 → 定位通过但标注证据过短（WARN，不冒充完整证据）。"""
        r = toolkit(["verify", str(QUIZD / "quiz_short_quote.json"), "--manifest", str(MF)])
        self.assertEqual(r.returncode, 0, r.stdout)   # 定位本身通过
        self.assertIn("证据过短", r.stdout)
        self.assertIn("已定位但证据不足", r.stdout)
        self.assertIn("与完整语义证据验证区分", r.stdout)
        rp = OUT / "thin-report.json"
        r2 = toolkit(["verify", str(QUIZD / "quiz_short_quote.json"), "--manifest", str(MF),
                      "--report", str(rp)])
        rep = json.loads(rp.read_text(encoding="utf-8"))
        self.assertTrue(any(f["rule_id"] == "B-QUOTE-THIN" and f["severity"] == "WARN"
                            for f in rep["findings"]))

    def test_thin_quote_not_blocking_strict(self):
        """短证据是质量提醒（WARN），不阻断正式发布（语义层保持独立判断）。"""
        r = toolkit(["build", str(QUIZD / "quiz_short_quote.json"), "-o", str(OUT),
                     "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertIn("release=READY", r.stdout, r.stdout)

    def test_repeated_quote_flagged(self):
        """短引用在片段内多次出现 → B-QUOTE-UNIQUE（定位歧义提示）。"""
        r = toolkit(["verify", str(QUIZD / "quiz_repeat_quote.json"), "--manifest", str(MF),
                     "--report", str(OUT / "uniq-report.json")])
        rep = json.loads((OUT / "uniq-report.json").read_text(encoding="utf-8"))
        uniqs = [f for f in rep["findings"] if f["rule_id"] == "B-QUOTE-UNIQUE"]
        thins = [f for f in rep["findings"] if f["rule_id"] == "B-QUOTE-THIN"]
        self.assertTrue(len(thins) >= 2, "两题均为短引用")
        self.assertTrue(uniqs, "出现多次的短引用应触发 B-QUOTE-UNIQUE")

    def test_normal_quote_no_quality_findings(self):
        r = toolkit(["verify", str(QUIZD / "quiz_ev.json"), "--manifest", str(MF),
                     "--report", str(OUT / "normal-report.json")])
        rep = json.loads((OUT / "normal-report.json").read_text(encoding="utf-8"))
        for rid in ("B-QUOTE-THIN", "B-QUOTE-UNIQUE", "B-REF-CONFLICT", "B-SOURCE-HASH"):
            self.assertFalse(any(f["rule_id"] == rid for f in rep["findings"]),
                             f"正常题库不应触发 {rid}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
