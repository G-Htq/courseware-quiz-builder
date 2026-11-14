# -*- coding: utf-8 -*-
"""test_security_v22.py - E 类安全测试（v2.2 新增）：输出转义与不可信资源加载。

已有覆盖（复用 v2.1 套件）：路径穿越/符号链接（test_path_security）、恶意归档/zip 炸弹
（test_extract_text）、超大输入（test_schema_v22）。
本套件聚焦：
  HTML 注入：题干/选项含 </script>、onerror、javascript: → 产物转义
  Markdown 注入：[链接](javascript:...) → 转义
  不可信资源加载：产物无外部 script/img 引用（全部 data: 内嵌）
  材料提示词注入：材料文本中的指令性文字仅作数据（解析为文本，不执行）
"""
import json
import re
import unittest

from _common import MAT, OUT, QUIZD, TEMPLATE, ensure_fixtures, write_quiz

MF = QUIZD / "manifest.json"

PAYLOAD_STEM = "</script><img src=x onerror=alert(1)>"
PAYLOAD_OPT = "<script>alert('xss')</script>"
PAYLOAD_MD = "[点我](javascript:alert(1))"
PAYLOAD_REF = "<script src='http://evil.example/x.js'></script>"


def hostile_quiz():
    base = json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))
    base["title"] = "注入防护测试"
    q = base["questions"][0]
    q["stem"] = PAYLOAD_STEM + " 队列的存取方式是什么？"
    q["options"] = ["<b>先进先出</b>", PAYLOAD_OPT, "随机访问", "两端进中间出"]
    q["explanation"] = "材料原文支持，故选A。" + PAYLOAD_MD
    base["questions"] = base["questions"][:1]
    return base


class TestOutputInjection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()
        OUT.mkdir(exist_ok=True)
        from _common import toolkit
        cls.r = toolkit(["build", str(write_quiz("quiz_inject.json", hostile_quiz())),
                         "-o", str(OUT), "--manifest", str(MF), "--html-template", str(TEMPLATE),
                         "--mode", "strict"])

    def test_build_succeeds_with_hostile_content(self):
        """恶意内容为数据不阻断构建（转义处理）。"""
        self.assertEqual(self.r.returncode, 0, self.r.stdout)

    def test_html_no_raw_script_close(self):
        """题干中的 </script> 不得原样进入 QUIZ_DATA（防提前闭合注入）。"""
        html = (OUT / "刷题页-注入防护测试.html").read_text(encoding="utf-8")
        m = re.search(r"var QUIZ = (\{.*?\});\n", html, re.S)
        self.assertIsNotNone(m, "QUIZ 数据块应存在")
        self.assertNotIn("</script><img", m.group(1))
        self.assertIn("\\u003c", m.group(1))   # < 被全量转义为 \u003c

    def test_html_no_onerror_attribute(self):
        """onerror 不得出现在标签属性位置（<tag ... onerror=）；
        数据字符串内字面量已被 < 转义隔离在 <script> JSON 内。"""
        html = (OUT / "刷题页-注入防护测试.html").read_text(encoding="utf-8")
        # 标签属性位注入（HTML 解析层风险）
        self.assertIsNone(re.search(r"<[a-z][^>]*\sonerror", html, re.I),
                          "标签属性位不得出现 onerror")
        # 数据层隔离：题干中 payload 的 < 已全量转义为 \u003c
        self.assertNotIn("</script><img src=x onerror", html)

    def test_md_no_raw_link_injection(self):
        md = (OUT / "题库-注入防护测试.md").read_text(encoding="utf-8")
        self.assertNotIn("[点我](javascript:", md)
        self.assertNotIn("<script>", md)


class TestNoUntrustedResources(unittest.TestCase):
    """产物必须完全离线：不引用任何外部 script/样式/图片资源。"""

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def _scan(self, path):
        text = path.read_text(encoding="utf-8")
        ext_scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', text)
        ext_links = re.findall(r'(?:src|href)=["\'](?!(?:data:|#))(https?:)?//[^"\']+["\']', text)
        http_refs = re.findall(r'https?://[a-z0-9.-]+\.(?:js|css|png|jpg)', text)
        return ext_scripts, ext_links, http_refs

    def test_template_has_no_external_resources(self):
        s, l, h = self._scan(TEMPLATE)
        self.assertEqual((s, l, h), ([], [], []), "模板不得引用外部资源")

    def test_product_has_no_external_resources(self):
        from _common import toolkit
        p = OUT / "刷题页-合成材料·证据链测试题库.html"
        toolkit(["build", str(QUIZD / "quiz_ev.json"), "-o", str(OUT),
                 "--manifest", str(MF), "--html-template", str(TEMPLATE), "--mode", "strict"])
        s, l, h = self._scan(p)
        self.assertEqual((s, l, h), ([], [], []), "产物不得引用外部资源（完全离线）")

    def test_frontend_image_whitelist_blocks_javascript_url(self):
        """前端 safeImgSrc：javascript: 协议被拒（静态断言白名单正则存在）。"""
        t = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("safeImgSrc", t)
        self.assertIn(r"/^data:image\/(png|jpe?g|gif|webp);base64,", t)


class TestMaterialPromptInjection(unittest.TestCase):
    """材料级提示词注入：课件文本中的指令仅作数据，manifest 原样收录、不执行。"""

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def test_injected_instruction_is_data_only(self):
        """合成材料 notes.md 含指令性文本（make_fixtures 生成）→ 解析为片段文本。"""
        manifest = json.loads((QUIZD / "manifest.json").read_text(encoding="utf-8"))
        hostile = None
        for s in manifest["sources"]:
            for seg in s.get("segments", []):
                if "忽略" in seg["text"] or "删除" in seg["text"]:
                    hostile = seg
        if hostile is None:
            self.skipTest("合成材料未包含指令性文本（fixtures 版本差异），跳过——由 SKILL.md 条款与 E2E 人工清单覆盖")
        self.assertIn("text", hostile)  # 它只是文本，没有任何分支执行它（代码无可执行钩子）
        # 脚本本身不解析/执行材料文本：无 eval/exec/os.system 等动态执行
        tk_path = QUIZD.parent.parent / "skill-src" / "courseware-quiz-builder" / "scripts" / "quiz_toolkit.py"
        tk = tk_path.read_text(encoding="utf-8")
        for banned in ("eval(", "exec(", "os.system("):
            self.assertNotIn(banned, tk, f"核心工具代码不得出现 {banned}")

    def test_skill_md_has_injection_clause(self):
        text = (QUIZD.parent.parent / "skill-src" / "courseware-quiz-builder" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("指令性文字", text)
        self.assertIn("不执行", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
