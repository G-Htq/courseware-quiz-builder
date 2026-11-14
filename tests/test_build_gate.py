# -*- coding: utf-8 -*-
"""test_build_gate.py - v2.1 强制质量门禁（P0-2，修复 V2-02 门禁绕过）。

矩阵：
  strict（默认）  层A FAIL / 层B FAIL / 缺 manifest / 语义 unresolved → exit 1 零产物
  preview（显式） 仅层A FAIL 阻断；其余放行但文件名/MD/HTML/报告四处标注草稿
另覆盖：validation-report.json 机器契约、阻断时清理陈旧产物、矛盾检测阻断、
证据剥离防护、verify --report。
"""
import json
import unittest
from pathlib import Path

from _common import OUT, QUIZD, STAGE, TEMPLATE, ensure_fixtures, toolkit

T = "合成材料·证据链测试题库"   # quiz_ev.json 的 title


def report_of(d):
    return json.loads((d / "validation-report.json").read_text(encoding="utf-8"))


class TestBuildGate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    # ---- strict：通过路径 ----

    def test_strict_passes_with_report_and_gate(self):
        r = toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("[门禁] mode=strict", r.stdout)
        self.assertIn("release=READY", r.stdout)
        self.assertIn("validation=WARN", r.stdout)
        rep = report_of(OUT)
        self.assertEqual(rep["schema"], "courseware-quiz-builder/validation-report@2.2")
        self.assertEqual(rep["mode"], "strict")
        self.assertEqual(rep["release_status"], "READY")
        self.assertEqual(rep["command"], "build")
        self.assertEqual(rep["tool_version"], "2.2")
        self.assertFalse(rep["gate"]["blocked"])
        self.assertEqual(rep["validation_status"], "WARN")
        html = (OUT / f"刷题页-{T}.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("__QUIZ_DATA__"), 0)
        self.assertIn('"_gate"', html)                 # 门禁元数据注入页面
        self.assertIn('"draft": false', html)          # 正式交付 draft=false
        md = (OUT / f"题库-{T}.md").read_text(encoding="utf-8")
        self.assertIn("证据：材料原文", md)
        self.assertIn("定位：", md)
        self.assertIn("复核：", md)
        self.assertNotIn("草稿·未通过完整核验", md)     # 正式交付不得带草稿标注

    # ---- strict：阻断路径 ----

    def test_strict_blocks_layer_b_failure(self):
        """V2-02 修复：层B 引用错位必须 exit 1 且零产物。"""
        r = toolkit(["build", str(QUIZD / "quiz_bad_quote.json"), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("[阻断]", r.stdout)
        self.assertIn("拒绝产出", r.stdout)
        self.assertFalse((OUT / "刷题页-引用错位测试.html").exists())
        self.assertFalse((OUT / "题库-引用错位测试.md").exists())
        rep = report_of(OUT)
        self.assertTrue(rep["gate"]["blocked"])
        self.assertTrue(any(f["rule_id"].startswith("B-") for f in rep["findings"]))

    def test_strict_blocks_missing_manifest(self):
        r = toolkit(["build", str(QUIZD / "quiz_legacy.json"), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("B-MANIFEST-001", r.stdout)
        self.assertFalse((OUT / "刷题页-旧格式兼容测试.html").exists())

    def test_strict_blocks_contradiction(self):
        """解析结论与答案矛盾（层A）→ 阻断。"""
        r = toolkit(["build", str(QUIZD / "quiz_contradict.json"), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("A-EXPLAIN-CONSISTENCY", r.stdout)

    def test_strict_blocks_evidence_stripping(self):
        """证据剥离防护：有 manifest 但全部证据链字段被删 → B-EVIDENCE-STRIPPED 阻断。"""
        r = toolkit(["build", str(QUIZD / "quiz_ev_tampered.json"), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("B-EVIDENCE-STRIPPED", r.stdout)

    def test_strict_blocked_preserves_stale_products(self):
        """v2.2 契约：同一个题库先成功后失败 → 不删除旧产物（不破坏已验证成果），
        但必须显式列出残留（防误认为本次成功），且本次不产生任何新产物。"""
        # 1) 成功 build
        r1 = toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(OUT),
                      "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r1.returncode, 0)
        self.assertTrue((OUT / f"刷题页-{T}.html").exists())
        # 2) 同 title 坏引用副本 → strict 阻断，旧产物保留并警告
        import json
        broken = json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))
        broken["questions"][0]["source_quote"] = "故意写错的引用文本，无法定位"
        probe = QUIZD / "quiz_stale_probe.json"
        probe.write_text(json.dumps(broken, ensure_ascii=False, indent=1), encoding="utf-8")
        r2 = toolkit(["build", str(probe), "-o", str(OUT),
                      "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r2.returncode, 1)
        self.assertIn("[注意]", r2.stdout)
        self.assertIn("不代表本次验证结果", r2.stdout)
        self.assertFalse((OUT / "刷题页-{T}（草稿）.html").exists())
        # 3) 旧产物仍在（保护性契约变更：v2.1 删除 → v2.2 保留+警告）
        self.assertTrue((OUT / f"刷题页-{T}.html").exists(),
                        "旧正式产物必须保留（不破坏已验证成果）")
        self.assertTrue((OUT / f"题库-{T}.md").exists())
        # 4) 诊断报告仍在（不删）
        self.assertTrue((OUT / "validation-report.json").exists())
        rep = report_of(OUT)
        self.assertEqual(rep["release_status"], "BLOCKED")
        probe.unlink()

    # ---- preview：草稿放行 / 层A 仍阻断 ----

    def test_preview_allows_draft_with_labels(self):
        """层B 失败在 preview 下放行，但文件名/MD/HTML/报告四处标注草稿。"""
        r = toolkit(["build", str(QUIZD / "quiz_bad_quote.json"), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "preview"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("草稿放行", r.stdout)
        md = OUT / "题库-引用错位测试（草稿）.md"
        html = OUT / "刷题页-引用错位测试（草稿）.html"
        self.assertTrue(md.exists() and html.exists())
        self.assertIn("草稿·未通过完整核验", md.read_text(encoding="utf-8"))
        htext = html.read_text(encoding="utf-8")
        self.assertIn('"draft":true', htext.replace(" ", ""))  # _gate.draft = true
        self.assertIn("草稿·未通过完整核验", htext)             # 横幅文本随数据注入
        rep = report_of(OUT)
        self.assertFalse(rep["gate"]["blocked"])
        self.assertEqual(rep["mode"], "preview")

    def test_preview_still_blocks_layer_a(self):
        """preview 只放行非结构失败：层A 缺 source_quote 仍阻断。"""
        r = toolkit(["build", str(QUIZD / "quiz_bad_partial.json"), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "preview"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("A-QUOTE", r.stdout)
        self.assertFalse((OUT / "刷题页-证据残缺测试.html").exists())
        self.assertFalse((OUT / "刷题页-证据残缺测试（草稿）.html").exists())

    def test_invalid_mode_rejected(self):
        """非法 --mode：argparse 拒绝（exit 2，错误信息在 stderr）。"""
        r = toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "yolo"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid choice", r.stdout + r.stderr)

    # ---- 报告契约 ----

    def test_report_contract_fields(self):
        toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(OUT),
                 "--html-template", str(TEMPLATE), "--mode", "strict"])
        rep = report_of(OUT)
        for key in ("schema", "tool_version", "command", "generated_at", "quiz", "manifest", "mode",
                    "input_digest", "validation_status", "release_status", "gate", "checks",
                    "summary", "findings", "per_question"):
            self.assertIn(key, rep)
        self.assertEqual(rep["schema"], "courseware-quiz-builder/validation-report@2.2")
        self.assertIn("layer_a", rep["summary"])
        self.assertIn("layer_b", rep["summary"])
        self.assertIn("layer_c", rep["summary"])
        # v2.2 三维一致性：blocked ⟺ release_status=BLOCKED（不允许矛盾组合）
        self.assertEqual(rep["gate"]["blocked"], rep["release_status"] == "BLOCKED")
        # checks 执行状态契约
        check_ids = {c["id"] for c in rep["checks"]}
        for cid in ("layer_a_structure", "manifest_load", "source_file_integrity",
                    "layer_b_location", "layer_c_semantic_rules", "image_security"):
            self.assertIn(cid, check_ids)
        for c in rep["checks"]:
            self.assertIn(c["execution"], ("EXECUTED", "SKIPPED", "UNAVAILABLE"))
            self.assertIn(c["result"], ("PASS", "WARN", "FAIL", "NOT_VERIFIED"))
        # 状态枚举合法
        self.assertIn(rep["validation_status"], ("PASS", "WARN", "FAIL", "NOT_VERIFIED"))
        self.assertIn(rep["release_status"], ("READY", "DRAFT_ONLY", "BLOCKED", "NOT_APPLICABLE"))
        for f in rep["findings"]:
            for k in ("rule_id", "severity", "question_id", "message", "evidence", "suggested_fix"):
                self.assertIn(k, f)

    def test_verify_report_flag(self):
        rp = OUT / "verify-report.json"
        r = toolkit(["verify", str(QUIZD / "quiz_ev.json"), "--report", str(rp)])
        self.assertEqual(r.returncode, 0, r.stdout)
        rep = json.loads(rp.read_text(encoding="utf-8"))
        self.assertEqual(rep["mode"], "verify")
        self.assertEqual(rep["summary"]["layer_b"]["pass"], 4)

    def test_unresolved_marked_not_verified(self):
        """语义 unresolved：不冒充通过——overall 不得为 PASS，findings 记录 NOT_VERIFIED。"""
        import json
        data = json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))
        data["title"] = "语义未决测试"
        data["questions"][0]["evidence_status"] = "unresolved"
        from _common import write_quiz
        p = write_quiz("quiz_unresolved.json", data)
        r = toolkit(["build", str(p), "-o", str(OUT),
                     "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 1, "strict 模式语义 unresolved 必须阻断")
        rep = report_of(OUT)
        self.assertTrue(any(f["severity"] == "FAIL" and "C-SEM" in f["rule_id"]
                            for f in rep["findings"]), r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
