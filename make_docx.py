#!/usr/bin/env python3
"""make_docx.py - 生成参赛《技能说明（500字内）》Word 文档（最小 OOXML，标准库）。"""
import zipfile
from pathlib import Path

OUT = Path(r"F:\Project\新建文件夹\课件智练v2\技能说明（500字内）.docx")

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

TITLE = "课件智练技能说明（v2.2）"

SECTIONS = [
    ("作品思路", "AI出题无据可查。课件智练把课件变成“每题可溯源”题库，机器门禁让未核验题库无法冒充交付，伪造“已验证”也被拦。"),
    ("功能说明", "输入PPT/PDF/Word/TXT/MD或粘贴文本，按考点生成四题型题库；刷题页含复习/考试双模式、解析与证据展开、错题重做对比、学习报告、记录导出导入；支持图片题"),
    ("技术实现", "标准库解析OOXML生成证据链；三层验证（结构/来源/语义）；逐题门禁缺证即阻断；引用与材料哈希交叉核对；原子化构建零半成品；报告三维状态；单文件离线HTML。"),
    ("使用说明", "对TeleAgent说“帮我把这份PPT变成复习题”附课件；产出题库与刷题页，双击即用，全程本地"),
    ("主要提示词", "“生成一套数据结构章节练习”“对上次错题进行强化练习”。"),
    ("工作流", "解析→知识点提取→覆盖规划→分批出题→三层验证→门禁渲染"),
    ("迭代优化", "v1修10项；v2证据链与错题闭环；v2.1门禁与路径安全；v2.2反伪造/三维报告/原子化；113用例+32场景E2E全过。"),
]


def para(lead, text, bold_lead=True):
    lead_run = f'<w:r><w:rPr><w:b/><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr><w:t xml:space="preserve">【{lead}】</w:t></w:r>' if bold_lead else ""
    text_run = f'<w:r><w:rPr><w:sz w:val="21"/><w:szCs w:val="21"/></w:rPr><w:t xml:space="preserve">{text}</w:t></w:r>'
    return f'<w:p><w:spacing w:after="120" w:line="312" w:lineRule="auto"/>{lead_run}{text_run}</w:p>'


title_p = ('<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
           '<w:r><w:rPr><w:b/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr>'
           f'<w:t>{TITLE}</w:t></w:r></w:p>')

body = title_p + "".join(para(k, v) for k, v in SECTIONS)
doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       f'<w:document xmlns:w="{W}"><w:body>{body}'
       f'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
       f'<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>'
       f'</w:body></w:document>')

ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
      '</Types>')
rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", ct)
    z.writestr("_rels/.rels", rels)
    z.writestr("word/document.xml", doc)

chars = sum(len(k) + len(v) + 4 for k, v in SECTIONS)
print(f"written: {OUT}")
print(f"生成内容字符（含小标题估算）≈ {chars}；平台 AIGC 水印约 48 字符另计，目标总字符 ≤500")
