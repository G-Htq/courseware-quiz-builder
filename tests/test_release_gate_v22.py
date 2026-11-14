# -*- coding: utf-8 -*-
"""test_release_gate_v22.py - P0-3/P0-6 发布门禁三态、原子化与退出码契约。

三维契约：
  validation_status ∈ PASS/WARN/FAIL/NOT_VERIFIED（验证结论）
  release_status    ∈ READY/DRAFT_ONLY/BLOCKED/NOT_APPLICABLE（发布决策）
  checks[].execution ∈ EXECUTED/SKIPPED/UNAVAILABLE（检查执行状态）
退出码：0=命令承诺操作成功；1=验证失败/门禁阻断/关键检查未执行；2=用法/IO。
"""
import json
import importlib.util
import shutil
import sys
import unittest
from pathlib import Path

from _common import MAT, OUT, QUIZD, STAGE, TEMPLATE, ensure_fixtures, toolkit, write_quiz

MF = QUIZD / "manifest.json"
T = "合成材料·证据链测试题库"


def report_of(p=None):
    p = p or (OUT / "validation-report.json")
    return json.loads(Path(p).read_text(encoding="utf-8"))


class TestPerQuestionGate(unittest.TestCase):
    """V22-A：逐题来源门禁——一题缺证据即阻断，不因其他题通过而放行。"""

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()
        OUT.mkdir(exist_ok=True)

    def test_mixed_evidence_blocked(self):
        r = toolkit(["build", str(QUIZD / "quiz_mixed_evidence.json"), "-o", str(OUT),
                     "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("B-EVIDENCE-REQUIRED@Q2", r.stdout)
        self.assertIn("release=BLOCKED", r.stdout)
        rep = report_of()
        self.assertEqual(rep["release_status"], "BLOCKED")
        self.assertEqual(rep["validation_status"], "FAIL")
        self.assertEqual(rep["per_question"]["Q2"]["layer_b"], "FAIL")
        self.assertEqual(rep["per_question"]["Q1"]["layer_b"], "PASS")  # 好题不受牵连

    def test_mixed_evidence_preview_is_draft(self):
        """preview 下逐题缺失允许草稿（DRAFT_ONLY），但文件名/横幅/报告三处标注。"""
        r = toolkit(["build", str(QUIZD / "quiz_mixed_evidence.json"), "-o", str(OUT),
                     "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "preview"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("release=DRAFT_ONLY", r.stdout)
        draft_html = OUT / "刷题页-逐题门禁测试（草稿）.html"
        self.assertTrue(draft_html.exists())
        h = draft_html.read_text(encoding="utf-8")
        self.assertIn("草稿·未通过完整核验", h)
        self.assertIn('"release": "DRAFT_ONLY"', h.replace("  ", " "))
        rep = report_of()
        self.assertEqual(rep["release_status"], "DRAFT_ONLY")

    def test_semantic_not_executed_blocks_strict(self):
        """语义未执行（NOT_VERIFIED）在 strict 下阻断正式发布（用户 3.2 策略）。"""
        import json as _json
        data = _json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))
        data["title"] = "语义未执行测试"
        data["questions"][0].pop("evidence_status", None)
        p = write_quiz("quiz_sem_not_executed.json", data)
        r = toolkit(["build", p, "-o", str(OUT), "--manifest", str(MF),
                     "--html-template", str(TEMPLATE), "--mode", "strict"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("C-SEM-001@Q1", r.stdout)
        self.assertIn("release=BLOCKED", r.stdout)


class TestAtomicBuild(unittest.TestCase):
    """V22-3.3：原子化——临时目录生成→自检→提交；失败不留半成品、不破坏旧产物。"""

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()
        OUT.mkdir(exist_ok=True)

    def _load_toolkit(self):
        spec = importlib.util.spec_from_file_location("qtk_v22", STAGE / "scripts" / "quiz_toolkit.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_render_failure_leaves_no_artifacts(self):
        """渲染期异常：无半成品、无 tmp 残留、旧正式产物完好、报告 BLOCKED。"""
        import tempfile
        mod = self._load_toolkit()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            # 1) 先成功构建正式产物
            rc = mod.cmd_build(QUIZD / "quiz_ev.json", out, TEMPLATE, str(MF), "strict", None, str(MAT))
            self.assertEqual(rc, 0)
            ok_html = out / f"刷题页-{T}.html"
            ok_mtime = ok_html.stat().st_mtime_ns
            self.assertTrue(ok_html.exists())
            # 2) 注入渲染期故障（collect_images 抛异常）再构建同名题库
            orig = mod.collect_images
            def boom(*a, **k):
                raise RuntimeError("模拟渲染中断：图片处理阶段故障")
            mod.collect_images = boom
            try:
                rc2 = mod.cmd_build(QUIZD / "quiz_ev.json", out, TEMPLATE, str(MF), "strict", None, str(MAT))
            finally:
                mod.collect_images = orig
            self.assertEqual(rc2, 1)
            # 3) 旧产物完好且未被覆盖（mtime 不变）
            self.assertTrue(ok_html.exists())
            self.assertEqual(ok_html.stat().st_mtime_ns, ok_mtime, "旧正式产物不得被渲染失败覆盖")
            # 4) 无半成品/无 tmp 目录残留
            leftovers = [p.name for p in out.iterdir() if p.name.startswith(".build-tmp") or p.name.endswith(("（草稿）.html",))]
            self.assertEqual(leftovers, [], f"不得残留临时半成品: {leftovers}")
            # 5) 报告为 BLOCKED（渲染失败），validation_status 与 release 一致
            rep = report_of(out / "validation-report.json")
            self.assertEqual(rep["release_status"], "BLOCKED")
            self.assertTrue(any("渲染失败" in r for r in rep["gate"]["reasons"]))

    def test_build_repeat_idempotent(self):
        """重复执行：连续两次成功构建，产物被原子替换（第二次为最新，无草稿混入）。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            r1 = toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(out),
                          "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
            r2 = toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(out),
                          "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
            self.assertEqual((r1.returncode, r2.returncode), (0, 0))
            files = sorted(p.name for p in out.iterdir() if p.suffix in (".html", ".md"))
            self.assertEqual(files, [f"刷题页-{T}.html", f"题库-{T}.md"])
            rep = report_of(out / "validation-report.json")
            self.assertEqual(rep["release_status"], "READY")

    def test_draft_and_formal_products_isolated(self):
        """草稿与正式产物隔离：同名题库 draft 与正式文件并存互不覆盖。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(out),
                     "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
            r = toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(out),
                         "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "preview"])
            self.assertEqual(r.returncode, 0, r.stdout)
            formal = out / f"刷题页-{T}.html"
            draft = out / f"刷题页-{T}（草稿）.html"
            self.assertTrue(formal.exists() and draft.exists())
            # 隔离性看注入数据而非模板静态字符串（模板 JS 恒含横幅文案，仅 draft=true 时渲染）
            fd = formal.read_text(encoding="utf-8")
            dd = draft.read_text(encoding="utf-8")
            self.assertIn('"release": "READY"', fd)
            self.assertIn('"draft": false', fd)
            self.assertIn('"release": "DRAFT_ONLY"', dd)
            self.assertIn('"draft": true', dd)
            self.assertNotIn('"release": "READY"', dd)


class TestStatusAndExitCodes(unittest.TestCase):
    """P0-6：状态组合与退出码回归矩阵（失败=exit 1；未执行关键检查=exit 1；用法=2）。"""

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()
        OUT.mkdir(exist_ok=True)

    def test_exit_code_matrix_verify(self):
        cases = [
            (["verify", str(QUIZD / "quiz_ev.json"), "--manifest", str(MF)], 0, "核验干净"),
            (["verify", str(QUIZD / "quiz_bad_quote.json"), "--manifest", str(MF)], 1, "引用错位"),
            (["verify", str(QUIZD / "quiz_fake_ref.json"), "--manifest", str(MF)], 1, "来源引用矛盾"),
            (["verify", str(QUIZD / "quiz_ev.json"), "--manifest", "no-such.json"], 2, "manifest 不存在"),
        ]
        for args, want, label in cases:
            with self.subTest(case=label):
                r = toolkit(args)
                self.assertEqual(r.returncode, want, f"{label}: {r.stdout[-300:]}")

    def test_verify_no_manifest_exit_nonzero(self):
        """V22-E2：无 manifest（关键检查未执行）→ exit 1 且 checks 明示 UNAVAILABLE。"""
        import json as _json
        data = _json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))
        data.pop("manifest", None)
        p = write_quiz("quiz_no_manifest_v22.json", data)
        r = toolkit(["verify", p, "--report", str(OUT / "noman.json")])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("未执行", r.stdout)
        rep = report_of(OUT / "noman.json")
        lb = next(c for c in rep["checks"] if c["id"] == "layer_b_location")
        self.assertEqual(lb["execution"], "UNAVAILABLE")
        self.assertIn("不构成", lb["detail"])
        # verify 的 release_status 无发布语义
        self.assertEqual(rep["release_status"], "NOT_APPLICABLE")

    def test_exit_code_matrix_build(self):
        scenarios = [
            ("strict clean → READY/0", ["build", str(QUIZD / "quiz_ev.json"), "-o", str(OUT),
                                         "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"], 0),
            ("strict mixed evidence → BLOCKED/1", ["build", str(QUIZD / "quiz_mixed_evidence.json"), "-o", str(OUT),
                                                    "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"], 1),
            ("preview mixed → DRAFT_ONLY/0", ["build", str(QUIZD / "quiz_mixed_evidence.json"), "-o", str(OUT),
                                               "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "preview"], 0),
        ]
        for label, args, want in scenarios:
            with self.subTest(case=label):
                r = toolkit(args)
                self.assertEqual(r.returncode, want, f"{label}: {r.stdout[-300:]}")

    def test_status_no_contradiction(self):
        """V22-E1 回归：任何场景报告不得出现 validation=PASS 而发布被阻断的组合。"""
        for quiz in ("quiz_ev.json", "quiz_mixed_evidence.json", "quiz_bad_quote.json", "quiz_legacy.json"):
            with self.subTest(quiz=quiz):
                r = toolkit(["build", str(QUIZD / quiz), "-o", str(OUT),
                             "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
                rep = report_of()
                blocked = rep["release_status"] == "BLOCKED"
                self.assertEqual(rep["gate"]["blocked"], blocked, "gate.blocked ⟺ release=BLOCKED")
                if blocked:
                    self.assertNotEqual(rep["validation_status"], "PASS",
                                        "被阻断时 validation_status 不得为 PASS")
                self.assertIn(rep["validation_status"], ("PASS", "WARN", "FAIL", "NOT_VERIFIED"))

    def test_report_stdout_json(self):
        """--report - 输出机器可读 JSON 到 stdout（JSON 后仍有人类可读行，用 raw_decode 截取）。"""
        r = toolkit(["verify", str(QUIZD / "quiz_ev.json"), "--manifest", str(MF), "--report", "-"])
        self.assertEqual(r.returncode, 0, r.stdout)
        text = r.stdout
        schema_at = text.index('"schema"')
        brace = text.rindex("{", 0, schema_at)
        rep, _end = json.JSONDecoder().raw_decode(text[brace:])
        self.assertEqual(rep["schema"], "courseware-quiz-builder/validation-report@2.2")
        self.assertEqual(rep["release_status"], "NOT_APPLICABLE")
        self.assertEqual(len(rep["checks"]), 6)

    def test_input_digest_present(self):
        r = toolkit(["verify", str(QUIZD / "quiz_ev.json"), "--manifest", str(MF),
                     "--report", str(OUT / "dg.json")])
        rep = report_of(OUT / "dg.json")
        self.assertIn("sha256_16", rep["input_digest"])
        self.assertEqual(rep["input_digest"]["bytes"], (QUIZD / "quiz_ev.json").stat().st_size)


if __name__ == "__main__":
    unittest.main(verbosity=2)
