#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_edge_fixtures.py - v2.1 Office 边界文件夹具（复现 P0-1 解包异常）。

输出到 tests/edge/（相对脚本位置，不再硬编码临时目录）：
  noslides.pptx      zip 合法但无 slides
  noxml.docx         zip 合法但缺 word/document.xml
  emptybody.docx     document.xml 存在但 body 为空
  notext.pptx        slides 存在但纯图片无文本
  pptx_is_docx.pptx  扩展名 pptx、内容是 docx（类型伪装）
  pptx_is_text.pptx  扩展名 pptx、内容是纯文本（非 zip）
全部为合成文件，不含真实用户数据。
"""
import zipfile
from pathlib import Path

D = Path(__file__).resolve().parent / "edge"
D.mkdir(parents=True, exist_ok=True)

CT = '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
RELS = '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>'
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"

# 1) zip 合法但无 slides 的 pptx
with zipfile.ZipFile(D / "noslides.pptx", "w") as z:
    z.writestr("[Content_Types].xml", CT)

# 2) zip 合法但缺 word/document.xml 的 docx
with zipfile.ZipFile(D / "noxml.docx", "w") as z:
    z.writestr("[Content_Types].xml", CT)
    z.writestr("word/_rels/document.xml.rels", RELS)

# 3) document.xml 存在但 body 为空的 docx
with zipfile.ZipFile(D / "emptybody.docx", "w") as z:
    z.writestr("word/document.xml",
               f'<?xml version="1.0"?><w:document xmlns:w="{NS_W}"><w:body/></w:document>')

# 4) slides 存在但无文本的 pptx（纯图片占位）
with zipfile.ZipFile(D / "notext.pptx", "w") as z:
    z.writestr("[Content_Types].xml", CT)
    z.writestr("ppt/presentation.xml",
               f'<?xml version="1.0"?><p:presentation xmlns:p="{NS_P}"><p:sldIdLst/></p:presentation>')
    z.writestr("ppt/slides/slide1.xml",
               f'<?xml version="1.0"?><p:sld xmlns:p="{NS_P}" xmlns:a="{NS_A}"><p:cSld><p:spTree>'
               f'<p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill></p:pic>'
               f'</p:spTree></p:cSld></p:sld>')

# 5) 扩展名 pptx、内容是 docx（类型伪装）
with zipfile.ZipFile(D / "pptx_is_docx.pptx", "w") as z:
    z.writestr("[Content_Types].xml", CT)
    z.writestr("word/document.xml",
               f'<?xml version="1.0"?><w:document xmlns:w="{NS_W}"><w:body><w:p/></w:body></w:document>')

# 6) 扩展名 pptx、内容是纯文本（非 zip 容器）
(D / "pptx_is_text.pptx").write_text("this is not a zip file", encoding="utf-8")

print(f"edge fixtures -> {D}")
