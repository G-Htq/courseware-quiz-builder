# -*- coding: utf-8 -*-
"""test_schema_v22.py - P0-4 统一 Schema 校验入口：非法 JSON 全覆盖矩阵（V22-B）。

要求：任何非法输入不得抛出未处理 Traceback；输出稳定错误编号（A-SCHEMA-xxx）；
build/verify 对非法输入也尽可能落盘结构化验证报告；退出码受控。
"""
import json
import unittest

from _common import OUT, QUIZD, TEMPLATE, ensure_fixtures, toolkit, write_quiz

EVREF = "manifest.json"   # tests/quiz 同目录下存在


def _bad_quiz(name, payload):
    p = OUT / name
    if isinstance(payload, str):
        p.write_text(payload, encoding="utf-8")
    else:
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return p


def one_good_question():
    return {"id": "Q9", "type": "single", "difficulty": "易", "topic": "t",
            "source_ref": "x", "stem": "正常题目占位？", "options": ["a", "b"],
            "answer": [0], "explanation": "占位解析长度足够的要求是十个字符"}


class TestSchemaMatrix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()
        OUT.mkdir(exist_ok=True)

    def _assert_no_traceback(self, r, ctx):
        combined = r.stdout + r.stderr
        self.assertNotIn("Traceback", combined, f"{ctx} 不得抛出未处理异常:\n{combined[-800:]}")
        return combined

    # ---- 顶层结构非法 ----

    def test_top_level_empty_array(self):
        p = _bad_quiz("s1_top_array.json", "[]")
        r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
        self._assert_no_traceback(r, "build 顶层[]")
        self.assertEqual(r.returncode, 1)
        self.assertIn("A-SCHEMA-001", r.stdout)
        self.assertIn("顶层必须是 JSON 对象", r.stdout)

    def test_top_level_null(self):
        p = _bad_quiz("s2_null.json", "null")
        r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
        self._assert_no_traceback(r, "build null")
        self.assertEqual(r.returncode, 1)
        self.assertIn("A-SCHEMA-001", r.stdout)

    def test_top_level_string_number(self):
        for i, raw in enumerate(['"hello"', "42", "true"]):
            p = _bad_quiz(f"s3_toplevel_{i}.json", raw)
            r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
            self._assert_no_traceback(r, f"build {raw}")
            self.assertEqual(r.returncode, 1)
            self.assertIn("A-SCHEMA-001", r.stdout)

    def test_empty_object_missing_questions(self):
        p = _bad_quiz("s4_empty_obj.json", {})
        r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
        self._assert_no_traceback(r, "build {}")
        self.assertEqual(r.returncode, 1)
        self.assertIn("A-SCHEMA-002", r.stdout)

    def test_questions_is_string(self):
        p = _bad_quiz("s5_qstr.json", {"title": "t", "source_desc": "d", "questions": "Q1"})
        r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
        self._assert_no_traceback(r, "questions 字符串")
        self.assertEqual(r.returncode, 1)
        self.assertIn("A-SCHEMA-002", r.stdout)

    def test_questions_empty_list(self):
        p = _bad_quiz("s6_qempty.json", {"title": "t", "source_desc": "d", "questions": []})
        r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
        self._assert_no_traceback(r, "questions 空数组")
        self.assertEqual(r.returncode, 1)
        self.assertIn("A-SCHEMA-002", r.stdout)

    # ---- questions 元素非法（题目级，逐题报错不中断） ----

    def test_questions_mixed_types(self):
        p = _bad_quiz("s7_mixed.json", {"title": "t", "source_desc": "d",
                                        "questions": ["字符串", 42, None, one_good_question()]})
        r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
        self._assert_no_traceback(r, "混入字符串/数字/null")
        self.assertEqual(r.returncode, 1)
        self.assertIn("必须是对象", r.stdout)   # 逐题错误（A-STRUCT）

    def test_questions_all_strings(self):
        p = _bad_quiz("s8_allstr.json", {"title": "t", "source_desc": "d",
                                         "questions": ["a", "b"]})
        r = toolkit(["verify", p])
        self._assert_no_traceback(r, "verify 全字符串")
        self.assertEqual(r.returncode, 1)

    # ---- 嵌套字段类型 ----

    def test_nested_wrong_types(self):
        p = _bad_quiz("s9_nested.json", {"title": "t", "source_desc": "d",
                                         "questions": [dict(one_good_question(), options="不是数组", answer="不是数组")]})
        r = toolkit(["validate", p])
        self._assert_no_traceback(r, "嵌套类型错误")
        self.assertEqual(r.returncode, 1)
        self.assertIn("options", r.stdout)

    def test_question_id_missing_and_duplicate(self):
        q1 = one_good_question()
        q2 = one_good_question()   # 同 id
        q3 = {k: v for k, v in one_good_question().items() if k != "id"}
        p = _bad_quiz("s10_ids.json", {"title": "t", "source_desc": "d", "questions": [q1, q2, q3]})
        r = toolkit(["validate", p])
        self.assertEqual(r.returncode, 1)
        self.assertIn("id 重复", r.stdout)
        self.assertIn("缺少非空 id", r.stdout)

    def test_options_count_and_unknown_type(self):
        q1 = dict(one_good_question(), options=["a", "b", "c"], answer=[0])
        q2 = dict(one_good_question(), type="essay")
        p = _bad_quiz("s11_type.json", {"title": "t", "source_desc": "d", "questions": [q1, q2]})
        r = toolkit(["validate", p])
        self.assertEqual(r.returncode, 1)
        self.assertIn("type 必须是", r.stdout)

    # ---- 损坏 JSON / 超大输入 ----

    def test_broken_json(self):
        p = _bad_quiz("s12_broken.json", '{"title": "t", "questions": [}')
        r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
        self._assert_no_traceback(r, "损坏 JSON")
        self.assertEqual(r.returncode, 1)
        self.assertIn("不是有效的 JSON", r.stdout)

    def test_huge_input_no_hang(self):
        """超大输入不得挂死（题目数多+超长题干）；查重截断防护生效。"""
        qs = []
        for i in range(300):
            q = one_good_question()
            q["id"] = f"Q{i+1}"
            q["stem"] = f"第{i}题题干" + "长" * 3000   # 每题 3KB 题干
            q["options"] = [f"选项{c}" for c in "ABCD"]
            q["answer"] = [0]
            q["explanation"] = "这是一段足够长的解析，超出十个字符的要求。"
            qs.append(q)
        p = _bad_quiz("s13_huge.json", {"title": "超大输入测试", "source_desc": "d", "questions": qs})
        import subprocess
        import sys
        import time
        from _common import TOOLKIT
        t0 = time.time()
        r = subprocess.run([sys.executable, str(TOOLKIT), "validate", str(p)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        elapsed = time.time() - t0
        self._assert_no_traceback(r, "超大输入")
        self.assertIn("异常超长", r.stdout)  # 超长题干警告（截断查重生效的证据）
        self.assertLess(elapsed, 90, f"超大输入应在可控时间内完成（实际 {elapsed:.1f}s）")

    def test_invalid_image_data_url(self):
        q = one_good_question()
        q["image"] = "data:application/octet-stream;base64,AAAA"
        p = write_quiz("s14_baddata.json", {"title": "非法图片", "source_desc": "d", "questions": [q]})
        r = toolkit(["validate", p])
        self.assertEqual(r.returncode, 1)
        self.assertIn("image", r.stdout)

    # ---- 非法输入也产出结构化报告（build 通道） ----

    def test_schema_failure_still_writes_report(self):
        p = _bad_quiz("s15_rpt.json", [])
        r = toolkit(["build", p, "-o", str(OUT), "--mode", "strict"])
        self.assertEqual(r.returncode, 1)
        rep = json.loads((OUT / "validation-report.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["schema"], "courseware-quiz-builder/validation-report@2.2")
        self.assertEqual(rep["release_status"], "BLOCKED")
        self.assertEqual(rep["validation_status"], "FAIL")
        self.assertTrue(any(f["rule_id"].startswith("A-SCHEMA") for f in rep["findings"]))

    def test_verify_top_list_structured(self):
        p = _bad_quiz("s16_vfy.json", [])
        r = toolkit(["verify", p])
        self._assert_no_traceback(r, "verify 顶层[]")
        self.assertEqual(r.returncode, 1)
        self.assertIn("拒绝核验", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
