# -*- coding: utf-8 -*-
"""test_path_security.py - P0-3 图片路径安全（v2.1 新增，修复 V2-03）。

包含判定使用 Path.resolve()+is_relative_to（非字符串前缀）：
  ../ 与 ..\\ 穿越、绝对路径、协议外链、目录内不存在文件 → 分类拒绝；
  目录内正斜杠/反斜杠相对路径、合法 data URL → 放行。
"""
import base64
import json
import unittest

from _common import QUIZD, ensure_fixtures, toolkit, write_quiz

# 1x1 透明 PNG（合法 data URL 样本）
PNG_1PX = ("data:image/png;base64,"
           "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
           "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def one_image_quiz(title, image):
    """基于 quiz_ev 构造单题带 image 的题库（其余证据字段保留）。"""
    base = json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))
    base["title"] = title
    base["questions"] = base["questions"][:1]
    base["questions"][0]["image"] = image
    return base


class TestPathSecurity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def _validate_image(self, title, image):
        p = write_quiz(f"quiz_sec_{abs(hash(title)) % 10**8}.json", one_image_quiz(title, image))
        return toolkit(["validate", str(p)])

    def test_dotdot_escape_rejected(self):
        r = self._validate_image("穿越正斜杠测试", "../materials/imgs/real.png")
        self.assertEqual(r.returncode, 1)
        self.assertIn("路径越界", r.stdout)

    def test_dotdot_backslash_escape_rejected(self):
        r = self._validate_image("穿越反斜杠测试", "..\\materials\\imgs\\real.png")
        self.assertEqual(r.returncode, 1)
        self.assertIn("路径越界", r.stdout)

    def test_absolute_path_rejected(self):
        r = self._validate_image("绝对路径测试", "C:/Windows/system32/evil.png")
        self.assertEqual(r.returncode, 1)
        self.assertIn("绝对路径", r.stdout)

    def test_protocol_link_rejected(self):
        r = self._validate_image("外链测试", "http://evil.example.com/x.png")
        self.assertEqual(r.returncode, 1)
        self.assertIn("外部链接", r.stdout)

    def test_file_protocol_rejected(self):
        r = self._validate_image("file协议测试", "file:///C:/evil.png")
        self.assertEqual(r.returncode, 1)
        self.assertIn("外部链接", r.stdout)

    def test_missing_in_tree_file_rejected(self):
        r = self._validate_image("目录内缺失测试", "imgs/no-such.png")
        self.assertEqual(r.returncode, 1)
        self.assertIn("图片文件不存在", r.stdout)

    def test_in_tree_forward_slash_allowed(self):
        """目录内合法引用（正斜杠）→ 通过。"""
        r = toolkit(["validate", str(QUIZD / "quiz_img_ok.json")])
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_in_tree_backslash_allowed(self):
        """Windows 语义：目录内反斜杠分隔符等价相对路径 → 通过（非穿越）。"""
        r = self._validate_image("目录内反斜杠测试", "imgs\\real.png")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_data_url_allowed(self):
        r = self._validate_image("dataURL合法测试", PNG_1PX)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_svg_rejected(self):
        """svg 可携带脚本，不收录。"""
        r = self._validate_image("svg拒绝测试", "imgs/evil.svg")
        self.assertEqual(r.returncode, 1)
        self.assertIn("仅支持", r.stdout)

    def test_fake_png_still_rejected(self):
        """目录内但内容伪装（魔数不符）→ 拒绝。"""
        # materials/imgs/fake.png 是伪 PNG；复制进 quiz/imgs 以满足"目录内"
        import shutil
        from pathlib import Path
        src = QUIZD.parent / "materials" / "imgs" / "fake.png"
        dst = QUIZD / "imgs" / "fake.png"
        shutil.copyfile(src, dst)
        r = self._validate_image("目录内伪装测试", "imgs/fake.png")
        self.assertEqual(r.returncode, 1)
        self.assertIn("魔数校验失败", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
