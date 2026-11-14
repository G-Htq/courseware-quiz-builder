#!/usr/bin/env python3
"""make_fixtures.py - 课件智练 v2 测试夹具生成器（全部合成数据，不含真实用户隐私）

生成：
  materials/good.pptx     3页（含 xml:space 属性 <a:t>、表格、图片、演示顺序与文件名序不同）
  materials/good.docx     段落+标题样式+表格+图片（文档序）
  materials/notes.md      带标题层级的 Markdown
  materials/plain.txt     多段落纯文本
  materials/empty.txt     空文件
  materials/blank.txt     仅空白
  materials/bad.pptx      截断的 zip（损坏）
  materials/bomb.pptx     高压缩比条目（zip 炸弹模拟，无害）
  materials/imgs/real.png 真实 PNG
  materials/imgs/fake.png GIF 字节改名 .png（魔数不一致攻击样本）
  quiz/quiz_ev.json       含完整证据链的正例题库（与 manifest 对应）
  quiz/quiz_bad_*.json    各种故意错误的题库（来源不存在/片段不存在/引用错位/状态非法/魔数伪装）
"""
import json
import struct
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAT = ROOT / "materials"
QUIZ = ROOT / "quiz"
MAT.mkdir(parents=True, exist_ok=True)
QUIZ.mkdir(parents=True, exist_ok=True)
(MAT / "imgs").mkdir(exist_ok=True)

NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def make_png(path: Path, w=60, h=40, rgb=(40, 90, 200)):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


make_png(MAT / "imgs" / "real.png")
# 伪 PNG：实际 GIF 头（魔数与扩展名不一致）
(MAT / "imgs" / "fake.png").write_bytes(b"GIF89a" + b"\x00" * 64)


def slide_xml(texts, table=None, blip_rid=None):
    shapes = []
    for t in texts:
        attr = ' xml:space="preserve"' if t.get("attr") else ""
        shapes.append(
            f'<p:sp><p:txBody><a:p><a:r><a:t{attr}>{t["t"]}</a:t></a:r></a:p></p:txBody></p:sp>')
    if table:
        rows = "".join(
            "<a:tr>" + "".join(f'<a:tc><a:txBody><a:p><a:r><a:t>{c}</a:t></a:r></a:p></a:txBody></a:tc>'
                               for c in row) + "</a:tr>"
            for row in table)
        shapes.append(f'<p:graphicFrame><a:graphic><a:graphicData uri="table"><a:tbl>{rows}</a:tbl>'
                      f'</a:graphicData></a:graphic></p:graphicFrame>')
    if blip_rid:
        shapes.append(f'<p:pic><p:blipFill><a:blip r:embed="{blip_rid}"/></p:blipFill></p:pic>')
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">'
            f'<p:cSld><p:spTree>{"".join(shapes)}</p:spTree></p:cSld></p:sld>')


def build_pptx(path: Path):
    """3 张幻灯片；演示顺序 sldIdLst=[slide2, slide1, slide3]（与文件名序不同，验证真实顺序解析）。"""
    s1 = slide_xml([{"t": "堆栈是后进先出的线性表"}])
    s2 = slide_xml([{"t": "队列是先进先出的线性表", "attr": True}],
                   table=[["结构", "特点"], ["栈", "后进先出"], ["队列", "先进先出"]])
    s3 = slide_xml([{"t": "图的三种存储结构"}], blip_rid="rId1")
    pres = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:presentation xmlns:p="{NS_P}" xmlns:r="{NS_R}"><p:sldIdLst>'
            f'<p:sldId id="256" r:id="rId1"/><p:sldId id="257" r:id="rId2"/><p:sldId id="258" r:id="rId3"/>'
            f'</p:sldIdLst></p:presentation>')
    pres_rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 f'<Relationships xmlns="{NS_REL}">'
                 f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide2.xml"/>'
                 f'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>'
                 f'<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide3.xml"/>'
                 f'</Relationships>')
    slide3_rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   f'<Relationships xmlns="{NS_REL}">'
                   f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image1.png"/>'
                   f'</Relationships>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/></Types>')
    root_rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 f'<Relationships xmlns="{NS_REL}">'
                 f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
                 f'</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("ppt/presentation.xml", pres)
        z.writestr("ppt/_rels/presentation.xml.rels", pres_rels)
        z.writestr("ppt/slides/slide1.xml", s1)
        z.writestr("ppt/slides/slide2.xml", s2)
        z.writestr("ppt/slides/slide3.xml", s3)
        z.writestr("ppt/slides/_rels/slide3.xml.rels", slide3_rels)
        z.writestr("ppt/media/image1.png", (MAT / "imgs" / "real.png").read_bytes())


build_pptx(MAT / "good.pptx")

# ---------------- docx ----------------

def w_p(text, style=None, blip_rid=None):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    run = f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>' if text else ""
    drawing = ""
    if blip_rid:
        drawing = (f'<w:r><w:drawing><a:graphic xmlns:a="{NS_A}"><a:graphicData>'
                   f'<a:blip r:embed="{blip_rid}"/></a:graphicData></a:graphic></w:drawing></w:r>')
    return f'<w:p>{ppr}{run}{drawing}</w:p>'


def build_docx(path: Path):
    tbl = ('<w:tbl>'
           '<w:tr><w:tc>' + w_p("遍历方式") + '</w:tc><w:tc>' + w_p("时间复杂度") + '</w:tc></w:tr>'
           '<w:tr><w:tc>' + w_p("层序遍历") + '</w:tc><w:tc>' + w_p("O(n)") + '</w:tc></w:tr>'
           '<w:tr><w:tc>' + w_p("中序遍历") + '</w:tc><w:tc>' + w_p("O(n)") + '</w:tc></w:tr>'
           '</w:tbl>')
    body = (
        w_p("第二章 线性表", style="Heading1")
        + w_p("线性表是最基本、最简单的一种数据结构，由 n 个具有相同性质的数据元素组成。")
        + w_p("顺序表支持随机访问，链表支持高效插入删除。")
        + tbl
        + w_p("", blip_rid="rId1")
        + w_p("本章小结：线性表是后续栈与队列的基础。")
    )
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document xmlns:w="{NS_W}" xmlns:r="{NS_R}" xmlns:a="{NS_A}">'
           f'<w:body>{body}</w:body></w:document>')
    doc_rels = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<Relationships xmlns="{NS_REL}">'
                f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/img1.png"/>'
                f'</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", doc)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/media/img1.png", (MAT / "imgs" / "real.png").read_bytes())


build_docx(MAT / "good.docx")

# ---------------- 文本类 ----------------
(MAT / "notes.md").write_text(
    "# 数据结构复习笔记\n\n"
    "二叉树的性质：第 i 层最多有 2 的 i 减 1 次方个节点。\n\n"
    "完全二叉树的节点总数介于 2 的 h 减 1 次方与 2 的 h 次方减 1 之间。\n\n"
    "## 树的遍历\n\n"
    "先序遍历顺序为根左右，中序为左根右，后序为左右根。\n", encoding="utf-8")
(MAT / "plain.txt").write_text(
    "快速排序平均时间复杂度为 O(nlogn)。\n\n"
    "归并排序是稳定排序，快速排序是不稳定排序。\n\n"
    "哈希表在理想情况下查找时间复杂度为 O(1)。\n", encoding="utf-8")
(MAT / "empty.txt").write_text("", encoding="utf-8")
(MAT / "blank.txt").write_text("   \n\n  \n", encoding="utf-8")

# ---------------- 异常文件 ----------------
(MAT / "bad.pptx").write_bytes(b"PK\x03\x04" + b"\x00" * 30)
with zipfile.ZipFile(MAT / "bomb.pptx", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    z.writestr("ppt/slides/slide1.xml", b"\x00" * 5_000_000)  # 5MB 零 → 压缩比极高，模拟 zip 炸弹

# ---------------- 证据链题库（与 manifest 对应；manifest 由 run_tests.py 先跑 extractor 生成） ----------------
base_q = {
    "title": "合成材料·证据链测试题库",
    "source_desc": "合成测试材料（good.pptx/good.docx/notes.md），无真实用户数据",
    "generated_date": "2026-11-12",
    "manifest": "manifest.json",
    "topics": [
        {"id": "T1", "name": "栈与队列"},
        {"id": "T2", "name": "线性表"},
        {"id": "T3", "name": "树与遍历"},
    ],
    "questions": [
        {"id": "Q1", "type": "single", "difficulty": "易", "topic": "栈与队列", "topic_id": "T1",
         "knowledge_type": "definition",
         "source_ref": "课件第1页", "source_id": "S1", "segment_id": "S1:P1",
         "source_quote": "队列是先进先出的线性表",
         "evidence_status": "semantic-pass",
         "stem": "队列采用哪种存取方式？",
         "options": ["先进先出", "后进先出", "随机访问", "两端进中间出"], "answer": [0],
         "explanation": "材料原文明确“队列是先进先出的线性表”，故选A。B 是栈的特点，C 是顺序表特点。"},
        {"id": "Q2", "type": "judge", "difficulty": "易", "topic": "栈与队列", "topic_id": "T1",
         "knowledge_type": "property",
         "source_ref": "课件第2页", "source_id": "S1", "segment_id": "S1:P2",
         "source_quote": "堆栈是后进先出的线性表",
         "evidence_status": "semantic-pass",
         "stem": "栈是后进先出的线性表。",
         "options": ["正确", "错误"], "answer": [0],
         "explanation": "材料原文即“堆栈是后进先出的线性表”，说法正确。"},
        {"id": "Q3", "type": "multiple", "difficulty": "中", "topic": "树与遍历", "topic_id": "T3",
         "knowledge_type": "process",
         "source_ref": "笔记", "source_id": "S3", "segment_id": "S3:B5",
         "source_quote": "先序遍历顺序为根左右，中序为左根右，后序为左右根",
         "evidence_status": "needs-review",
         "verification_notes": "三种遍历顺序易混淆，建议使用者对照教材确认",
         "stem": "下列关于二叉树遍历顺序的说法，正确的有：",
         "options": ["先序：根左右", "中序：左根右", "后序：根左右", "后序：左右根"], "answer": [0, 1, 3],
         "explanation": "由笔记原文：先序根左右、中序左根右、后序左右根；C 项后序写成根左右错误。"},
        {"id": "Q4", "type": "short", "difficulty": "中", "topic": "线性表", "topic_id": "T2",
         "knowledge_type": "comparison",
         "source_ref": "讲义段落", "source_id": "S2", "segment_id": "S2:B3",
         "source_quote": "顺序表支持随机访问，链表支持高效插入删除",
         "evidence_status": "semantic-pass",
         "stem": "请对比顺序表与链表各自的优势。",
         "options": [], "answer": "①顺序表支持随机访问；②链表支持高效插入删除。",
         "explanation": "评分要点：答到随机访问（顺序表）与插入删除效率（链表）两个要点即可。"},
    ],
}
(QUIZ / "quiz_ev.json").write_text(json.dumps(base_q, ensure_ascii=False, indent=1), encoding="utf-8")

bad = json.loads(json.dumps(base_q))
bad["title"] = "坏来源测试"
bad["questions"][0]["source_id"] = "S99"
(QUIZ / "quiz_bad_source.json").write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")

bad = json.loads(json.dumps(base_q))
bad["title"] = "坏片段测试"
bad["questions"][0]["segment_id"] = "S1:P99"
(QUIZ / "quiz_bad_segment.json").write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")

bad = json.loads(json.dumps(base_q))
bad["title"] = "引用错位测试"
bad["questions"][0]["source_quote"] = "这段话在任何材料里都不存在，用来验证引用定位失败"
(QUIZ / "quiz_bad_quote.json").write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")

bad = json.loads(json.dumps(base_q))
bad["title"] = "非法状态测试"
bad["questions"][0]["evidence_status"] = "definitely-pass"
(QUIZ / "quiz_bad_status.json").write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")

bad = json.loads(json.dumps(base_q))
bad["title"] = "证据残缺测试"
bad["questions"][1].pop("source_quote")
(QUIZ / "quiz_bad_partial.json").write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")

# 魔数伪装测试：引用 fake.png（GIF 头）
bad = json.loads(json.dumps(base_q))
bad["title"] = "魔数伪装测试"
bad["questions"][0]["image"] = "../materials/imgs/fake.png"
(QUIZ / "quiz_fake_png.json").write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")

# 图片正常引用（相对 quiz 目录）
good_img = json.loads(json.dumps(base_q))
good_img["title"] = "图片正常引用测试"
good_img["questions"][0]["image"] = "../materials/imgs/real.png"
(QUIZ / "quiz_real_png.json").write_text(json.dumps(good_img, ensure_ascii=False, indent=1), encoding="utf-8")

print("fixtures ready:", ROOT)
