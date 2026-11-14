# -*- coding: utf-8 -*-
"""test_extract_text.py - 文档解析与降级行为（v2.0 TestParse/TestDegradation 迁移）。

覆盖：pptx 属性节点/演示顺序/表格/水印过滤；docx 段落/标题/表格/隐藏文本/图片；
md/txt 章节分段；多文件 source_manifest；损坏 zip / zip 炸弹 / 大小上限 /
空文件 / 不支持格式 / 不存在文件的诚实降级。
"""
import json
import unittest

from _common import MAT, QUIZD, ensure_fixtures, extract


class TestParse(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()
        cls.m = json.loads((QUIZD / "manifest.json").read_text(encoding="utf-8"))

    def seg(self, sid):
        for s in self.m["sources"]:
            for seg in s["segments"]:
                if seg["segment_id"] == sid:
                    return seg
        return None

    def test_pptx_attributed_text_node(self):
        """A1 修复：<a:t xml:space="preserve"> 带属性节点必须被提取。"""
        seg = self.seg("S1:P1")  # 演示顺序第1页 = slide2（队列）
        self.assertIsNotNone(seg)
        self.assertIn("队列是先进先出的线性表", seg["text"])

    def test_pptx_presentation_order(self):
        """按 presentation.xml sldIdLst 解析真实顺序，而非文件名序。"""
        p1, p2, p3 = self.seg("S1:P1"), self.seg("S1:P2"), self.seg("S1:P3")
        self.assertIn("队列", p1["text"])
        self.assertIn("堆栈", p2["text"])
        self.assertIn("图的三种存储结构", p3["text"])

    def test_pptx_table_structure(self):
        """表格行列结构保留（| 与换行分隔）。"""
        seg = self.seg("S1:P1")
        self.assertIn("结构 | 特点", seg["text"])
        self.assertIn("栈 | 后进先出", seg["text"])

    def test_pptx_watermark_filtered(self):
        """平台水印形状（*Watermark*）不进入片段文本。"""
        for s in self.m["sources"]:
            if s["format"] != "pptx":
                continue
            for seg in s["segments"]:
                self.assertNotIn("AI生成", seg["text"])
                self.assertNotIn("生成时间", seg["text"])

    def test_docx_paragraphs_and_chapter(self):
        seg = self.seg("S2:B3")
        self.assertIn("顺序表支持随机访问", seg["text"])
        self.assertEqual(seg.get("chapter"), "第二章 线性表")

    def test_docx_table(self):
        seg = self.seg("S2:B4")
        self.assertIsNotNone(seg)
        self.assertEqual(seg["type"], "table")
        self.assertIn("遍历方式 | 时间复杂度", seg["text"])
        self.assertIn("层序遍历 | O(n)", seg["text"])

    def test_docx_hidden_text_filtered(self):
        """w:vanish 隐藏文本（AIGC 标识）不进入正文。"""
        for s in self.m["sources"]:
            if s["format"] != "docx":
                continue
            for seg in s["segments"]:
                self.assertNotIn("AIGC标识", seg["text"])

    def test_docx_image_in_manifest(self):
        docx = [s for s in self.m["sources"] if s["format"] == "docx"][0]
        self.assertTrue(any("docx_img1" in i for i in docx["images"]))

    def test_md_headings_as_chapters(self):
        seg = self.seg("S3:B5")
        self.assertIn("先序遍历顺序为根左右", seg["text"])
        self.assertEqual(seg.get("chapter"), "树的遍历")

    def test_manifest_structure(self):
        for s in self.m["sources"]:
            self.assertRegex(s["source_id"], r"^S\d+$")
            self.assertEqual(s["status"], "ok")
            self.assertRegex(s["sha256"], r"^[0-9a-f]{64}$")
            for seg in s["segments"]:
                self.assertEqual(seg["source_id"], s["source_id"])
                self.assertTrue(seg["text"] or seg.get("images"))

    def test_multiple_sources_and_ids(self):
        self.assertEqual([s["source_id"] for s in self.m["sources"]], ["S1", "S2", "S3"])


class TestDegradation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ensure_fixtures()

    def test_bad_zip(self):
        r = extract([MAT / "bad.pptx"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("zip 容器无法打开", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_zip_bomb_rejected(self):
        r = extract([MAT / "bomb.pptx"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("压缩比", r.stdout)
        self.assertIn("拒绝解析", r.stdout)

    def test_size_limit(self):
        r = extract([MAT / "plain.txt"], ["--max-file-mb", "0"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("超过上限", r.stdout)

    def test_empty_and_blank(self):
        r = extract([MAT / "empty.txt", MAT / "blank.txt"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("文件为空或仅含空白", r.stdout)

    def test_unsupported_format(self):
        r = extract([MAT / "x.xyz"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("不支持的格式", r.stdout)

    def test_missing_file(self):
        r = extract([MAT / "no-such.pptx"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("失败", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
