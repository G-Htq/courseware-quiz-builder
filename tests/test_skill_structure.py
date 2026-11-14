# -*- coding: utf-8 -*-
"""test_skill_structure.py - Skill 静态规范（v2.1）。

注册目录一致性由发布流程（同步 + quick_validate）保证，不在开发套件断言；
此处校验暂存副本自身的规范项与 v2.1 关键前端静态特征。
"""
import py_compile
import unittest

from _common import STAGE, TEMPLATE


class TestSkillStatic(unittest.TestCase):

    def test_skill_md_frontmatter(self):
        text = (STAGE / "SKILL.md").read_text(encoding="utf-8")
        for field in ("name:", "description:", "name_cn:", "description_cn:"):
            self.assertIn(field, text)

    def test_skill_md_mentions_gate_modes(self):
        """SKILL.md 必须说明 strict/preview 门禁（文档与实现一致）。"""
        text = (STAGE / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("strict", text)
        self.assertIn("preview", text)
        self.assertIn("validation-report", text)

    def test_scripts_exist(self):
        for p in ("scripts/extract_text.py", "scripts/quiz_toolkit.py",
                  "assets/quiz-template.html", "references/quiz-format.md",
                  "references/generation-workflow.md"):
            self.assertTrue((STAGE / p).is_file(), p)

    def test_template_placeholder(self):
        t = TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual(t.count("__QUIZ_DATA__"), 1)

    def test_template_has_v21_frontend_features(self):
        """v2.1 前端关键静态特征：草稿横幅容器、考试状态机、导入 Schema 校验。"""
        t = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('id="gate-banner"', t)
        self.assertIn("function examActive()", t)
        self.assertIn("function normalizeState(", t)
        self.assertIn("function newAttemptId()", t)
        self.assertNotIn("state.submitted", t)   # v2 全局 submitted 标志必须移除

    def test_scripts_compile(self):
        for s in ("scripts/extract_text.py", "scripts/quiz_toolkit.py"):
            py_compile.compile(str(STAGE / s), doraise=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
