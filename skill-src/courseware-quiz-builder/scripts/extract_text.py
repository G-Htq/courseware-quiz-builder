#!/usr/bin/env python3
"""extract_text.py v2 - 课程材料解析器：结构化提取文本、图片与来源清单（manifest）

职责：
  1) 用 XML 解析器（stdlib ElementTree）可靠解析 Office Open XML，不使用脆弱的标签正则
  2) 生成 source_manifest.json：每份材料有稳定 source_id，每个内容片段有 segment_id，
     供 quiz_toolkit.py verify 做来源核验（证据链）
  3) 实施资源上限：文件大小 / zip 条目数 / 解压后总量 / 单条目压缩比（zip 炸弹防护）/ 图片数
  4) PDF 三态状态：ok（文字已提取）/ needs-ocr（需 OCR）/ failed（未能识别或缺依赖）
  5) 指令隔离：材料文本一律作为数据处理，本脚本不执行、不解析、不访问其中任何指令

支持格式: .txt / .md / .markdown / .pptx / .docx / .pdf（pdf 需 pdfplumber 或 pypdf）

用法:
  python extract_text.py <文件1> [文件2 ...] [--out 合并输出.txt]
                         [--images 图片目录] [--manifest source_manifest.json]
                         [--max-file-mb 200] [--max-total-mb 1500] [--max-images 300]

退出码: 0=全部成功  1=存在失败文件  2=用法错误

安全与边界:
  - 只读取命令行显式传入的文件；只写入 --out/--images/--manifest 指定的路径
  - zip 炸弹防护：条目数、解压总量、单条目压缩比三项上限，超限拒绝解析该文件
  - 图片仅按白名单扩展名抽取（svg 不收：可携带脚本）
"""

import argparse
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

SUPPORTED = {".txt", ".md", ".markdown", ".pptx", ".docx", ".pdf"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

MIN_VALID_CHARS = 300

# ---- 资源上限（可通过 CLI 覆盖；超限即拒绝解析，防止 zip 炸弹与异常文件拖垮宿主） ----
MAX_FILE_MB = 200          # 单个输入文件大小上限
MAX_ZIP_ENTRIES = 4000     # zip 容器条目数上限
MAX_TOTAL_MB = 1500        # 解压后总大小上限
MAX_RATIO = 200            # 单条目 压缩比 上限（file_size/compress_size）
MAX_IMAGES = 300           # 单个来源图片抽取上限

# OOXML 命名空间
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"   # DrawingML 文本 a:t / 表格 a:tbl
NS_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"  # 演示文稿
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"  # 文字处理
NS_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"  # r:embed / r:id
NS_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"  # .rels 文件


class LimitError(Exception):
    """资源上限越界（zip 炸弹/异常文件）。"""


# ---------------------------------------------------------------- 基础工具

def read_text_file(path: Path):
    """读取纯文本文件，自动尝试常见编码。返回 (text, error)。"""
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=enc), None
        except UnicodeDecodeError:
            continue
        except OSError as e:
            return None, f"读取失败: {e}"
    return None, "无法识别文件编码（尝试过 utf-8/gb18030）"


def check_size(path: Path, max_mb: int):
    size = path.stat().st_size
    if size > max_mb * 1024 * 1024:
        raise LimitError(f"文件大小 {size / 1048576:.1f}MB 超过上限 {max_mb}MB，拒绝解析")
    return size


def safe_zip(path: Path, max_entries: int, max_total_mb: int, max_ratio: int):
    """带 zip 炸弹防护地打开 zip 容器。返回 ZipFile；超限抛 LimitError。"""
    z = zipfile.ZipFile(path)
    infos = z.infolist()
    if len(infos) > max_entries:
        z.close()
        raise LimitError(f"zip 条目数 {len(infos)} 超过上限 {max_entries}")
    total = sum(i.file_size for i in infos)
    if total > max_total_mb * 1024 * 1024:
        z.close()
        raise LimitError(f"解压后总量 {total / 1048576:.1f}MB 超过上限 {max_total_mb}MB（疑似压缩炸弹）")
    for i in infos:
        if i.compress_size > 0 and i.file_size / i.compress_size > max_ratio:
            z.close()
            raise LimitError(f"条目 {i.filename} 压缩比 {i.file_size / i.compress_size:.0f} "
                             f"超过上限 {max_ratio}（疑似压缩炸弹）")
    return z


def _slide_no(name: str) -> int:
    m = re.search(r"(\d+)", name)
    return int(m.group(1)) if m else 0


def parse_rels(z: zipfile.ZipFile, rels_name: str):
    """解析 .rels，返回 {rId: target}。target 为包内绝对路径（正斜杠）。"""
    rels = {}
    if rels_name not in z.namelist():
        return rels
    try:
        root = ET.fromstring(z.read(rels_name))
    except ET.ParseError:
        return rels
    for rel in root.iter(f"{NS_REL}Relationship"):
        rid, target = rel.get("Id"), rel.get("Target")
        if not rid or not target:
            continue
        t = target.replace("\\", "/")
        if t.startswith("../"):
            # rels 位于 <dir>/_rels/，相对 Target 以基目录解析
            base = rels_name.rsplit("/_rels/", 1)[0]  # e.g. ppt/slides
            t = _normalize(base, t)
        elif t.startswith("/"):
            t = t.lstrip("/")
        else:
            # 普通相对路径（如 slides/slide2.xml）：相对 rels 所属目录的父目录
            base = rels_name.rsplit("/_rels/", 1)[0] if "/_rels/" in rels_name else ""
            t = _normalize(base, t)
        rels[rid] = t
    return rels


def _normalize(base: str, rel: str):
    """把相对路径解析为包内绝对路径（base 为 rels 所属目录的父目录）。"""
    parts = (base.split("/") if base else [])
    for seg in rel.split("/"):
        if seg == "..":
            if parts:
                parts.pop()
        elif seg and seg != ".":
            parts.append(seg)
    return "/".join(parts)


# ---------------------------------------------------------------- PPTX

def pptx_slide_order(z: zipfile.ZipFile):
    """按 presentation.xml 的 sldIdLst 解析真实演示顺序，返回 slide xml 路径列表。"""
    names = set(z.namelist())
    try:
        pres_rels = parse_rels(z, "ppt/_rels/presentation.xml.rels")
        root = ET.fromstring(z.read("ppt/presentation.xml"))
        order = []
        for sld in root.iter(f"{NS_P}sldId"):
            rid = sld.get(f"{NS_R}id")
            target = pres_rels.get(rid)
            if target and target in names:
                order.append(target)
        if order:
            return order
    except (KeyError, ET.ParseError):
        pass
    # 回退：按文件名序（非标准顺序时定位降级为“近似”，manifest 仍可用）
    slides = [n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
    return sorted(slides, key=_slide_no)


def _is_watermark_shape(el) -> bool:
    """识别水印形状：平台/工具注入的标注形状（如 TeleWaxWatermark）。跳过其文本，
    避免每页重复的“AI生成/生成时间”喳声污染片段与证据引用；源文件本身不修改。"""
    for cNvPr in el.iter(f"{NS_P}cNvPr"):
        name = (cNvPr.get("name") or "")
        if "watermark" in name.lower():
            return True
    return False


def _walk_pptx_text(el, out: list):
    """按文档顺序收集 DrawingML 文本；表格子树转结构化行列文本；跳过水印形状。"""
    tag = el.tag
    if tag == f"{NS_P}sp" and _is_watermark_shape(el):
        return
    if tag == f"{NS_A}tbl":
        rows = []
        for tr in el.iter(f"{NS_A}tr"):
            cells = []
            for tc in tr.iter(f"{NS_A}tc"):
                cell_text = "".join(t.text or "" for t in tc.iter(f"{NS_A}t")).strip()
                cells.append(cell_text)
            if any(cells):
                rows.append(" | ".join(cells))
        if rows:
            out.append("\n".join(rows))
        return
    if tag == f"{NS_A}t":
        out.append(el.text or "")
        return
    for child in el:
        _walk_pptx_text(child, out)


def slide_texts(xml_bytes: bytes):
    """解析单页 slide XML，返回 (文本块列表, 该页引用的图片 rId 列表)。"""
    root = ET.fromstring(xml_bytes)
    out, rids = [], []
    _walk_pptx_text(root, out)
    for blip in root.iter(f"{NS_A}blip"):
        rid = blip.get(f"{NS_R}embed") or blip.get(f"{NS_R}link")
        if rid:
            rids.append(rid)
    texts = [html_unescape_keep(t.strip()) for t in out]
    return [t for t in texts if t], rids


def html_unescape_keep(s: str) -> str:
    # ET 已解码实体；此函数仅占位保证文本原样返回
    return s


def extract_pptx(path: Path, limits):
    """返回 (result_dict, error)：统一二元组契约（v2.1 修复 V2-01）。
    result_dict = {"segments": [...], "images": [...], "size": int}；失败时 (None, 错误信息)。"""
    try:
        size = check_size(path, limits["file_mb"])
        with safe_zip(path, limits["entries"], limits["total_mb"], limits["ratio"]) as z:
            names = set(z.namelist())
            slides = pptx_slide_order(z)
            if not slides:
                return None, "未找到幻灯片内容（可能不是标准 pptx，或为 docx/其它结构伪装）"
            segments, images = [], []
            img_quota = limits["images"]
            for i, slide_name in enumerate(slides, 1):
                xml = z.read(slide_name)
                texts, rids = slide_texts(xml)
                page_imgs = []
                if rids:
                    n = _slide_no(slide_name)
                    rels = parse_rels(z, f"ppt/slides/_rels/slide{n}.xml.rels")
                    k = 0
                    for rid in rids:
                        target = rels.get(rid)
                        if not target or Path(target).suffix.lower() not in IMG_EXTS or target not in names:
                            continue
                        if len(images) >= img_quota:
                            break
                        k += 1
                        page_imgs.append(("pptx", target, f"slide{i}_img{k}{Path(target).suffix.lower()}"))
                seg_text = "\n".join(texts)
                if seg_text or page_imgs:
                    segments.append({
                        "type": "slide", "page": i,
                        "text": seg_text,
                        "image_refs": [p[2] for p in page_imgs],
                        "raw_images": page_imgs,
                    })
            if not segments:
                return None, "幻灯片中未提取到文本（可能是纯图片课件，可结合 --images 走图片路径或 OCR）"
            return {"segments": segments, "images": images, "size": size}, None
    except LimitError as e:
        return None, f"拒绝解析: {e}"
    except zipfile.BadZipFile:
        return None, "文件损坏或不是有效的 pptx（zip 容器无法打开）"
    except ET.ParseError as e:
        return None, f"pptx 内部 XML 损坏: {e}"
    except Exception as e:  # noqa: BLE001
        return None, f"pptx 解析失败: {e}"


def save_pptx_images(z, raw_images, out_dir: Path, limits):
    saved = []
    for _, target, name in raw_images:
        if len(saved) >= limits["images"]:
            break
        dest = out_dir / name
        dest.write_bytes(z.read(target))
        saved.append(name)
    return saved


# ---------------------------------------------------------------- DOCX

HEADING_RE = re.compile(r"^(Heading[1-9]|[1-9])$", re.I)


def _docx_para_text(p_el):
    """收集段落内文本与 a:blip 图片引用（按 run 遍历；跳过 w:vanish 隐藏文本，如水印标识）。"""
    texts, rids = [], []
    for run in p_el.iter(f"{NS_W}r"):
        rPr = run.find(f"{NS_W}rPr")
        if rPr is not None and rPr.find(f"{NS_W}vanish") is not None:
            continue
        for node in run.iter(f"{NS_W}t"):
            texts.append(node.text or "")
        for blip in run.iter(f"{NS_A}blip"):
            rid = blip.get(f"{NS_R}embed")
            if rid:
                rids.append(rid)
    return "".join(texts), rids


def _para_style(p_el):
    for ps in p_el.iter(f"{NS_W}pStyle"):
        return ps.get(f"{NS_W}val") or ""
    return ""


def _docx_table_text(tbl_el):
    rows = []
    for tr in tbl_el.findall(f"{NS_W}tr"):
        cells = []
        for tc in tr.findall(f"{NS_W}tc"):
            cell_parts = []
            for p in tc.findall(f"{NS_W}p"):
                t, _ = _docx_para_text(p)
                if t.strip():
                    cell_parts.append(t.strip())
            cells.append(" ".join(cell_parts))
        if any(c.strip() for c in cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def extract_docx(path: Path, limits):
    """返回 ({segments, images, size}, error)。段落/表格按文档顺序；图片按文档内出现顺序。"""
    try:
        size = check_size(path, limits["file_mb"])
        with safe_zip(path, limits["entries"], limits["total_mb"], limits["ratio"]) as z:
            if "word/document.xml" not in z.namelist():
                return None, "文件损坏或不是有效的 docx（缺少 word/document.xml；若为 pptx/其它结构伪装也会走到此处）"
            root = ET.fromstring(z.read("word/document.xml"))
            doc_rels = parse_rels(z, "word/_rels/document.xml.rels")
            body = root.find(f"{NS_W}body")
            if body is None:
                return None, "docx 结构异常：document.xml 缺少正文 body（文档无内容）"
            segments, raw_images = [], []
            chapter = None
            block_no = 0
            for child in body:
                if child.tag == f"{NS_W}p":
                    text, rids = _docx_para_text(child)
                    style = _para_style(child)
                    if HEADING_RE.match(style) and text.strip():
                        chapter = text.strip()[:60]
                    local_imgs = []
                    for rid in rids:
                        target = doc_rels.get(rid)
                        if not target:
                            continue
                        t = target.replace("\\", "/")
                        t = t if t.startswith("word/") else "word/" + t
                        if Path(t).suffix.lower() not in IMG_EXTS:
                            continue
                        if len(raw_images) >= limits["images"]:
                            break
                        k = len(raw_images) + 1
                        name = f"docx_img{k}{Path(t).suffix.lower()}"
                        raw_images.append(("docx", t, name))
                        local_imgs.append(name)
                    if text.strip() or local_imgs:
                        block_no += 1
                        segments.append({
                            "type": "paragraph", "block": block_no,
                            "chapter": chapter, "text": text.strip(),
                            "image_refs": local_imgs, "raw_images": [],
                        })
                elif child.tag == f"{NS_W}tbl":
                    block_no += 1
                    segments.append({
                        "type": "table", "block": block_no,
                        "chapter": chapter, "text": _docx_table_text(child),
                        "image_refs": [], "raw_images": [],
                    })
            if not raw_images and not any(s["text"].strip() for s in segments):
                return None, "文档中未提取到文本（可能是纯图片文档，可结合 --images 走图片路径或 OCR）"
            # docx 图片统一按文档序落盘；segment 级 image_refs 已在段落内记录
            return {"segments": segments, "images": raw_images, "size": size}, None
    except LimitError as e:
        return None, f"拒绝解析: {e}"
    except zipfile.BadZipFile:
        return None, "文件损坏或不是有效的 docx（zip 容器无法打开）"
    except ET.ParseError as e:
        return None, f"docx 内部 XML 损坏: {e}"
    except Exception as e:  # noqa: BLE001
        return None, f"docx 解析失败: {e}"


# ---------------------------------------------------------------- PDF

def extract_pdf(path: Path, limits):
    """三态：ok / needs-ocr / failed。返回 ({segments, images, size, status}, error)。"""
    try:
        import pdfplumber  # noqa: F401
        have = "pdfplumber"
    except ImportError:
        try:
            import pypdf  # noqa: F401
            have = "pypdf"
        except ImportError:
            try:
                import PyPDF2  # noqa: F401
                have = "PyPDF2"
            except ImportError:
                return None, ("缺少 PDF 解析依赖。请先执行: pip install pdfplumber（或 pip install pypdf），"
                              "安装后重试"), "failed"
    try:
        size = check_size(path, limits["file_mb"])
        segments = []
        if have == "pdfplumber":
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    t = (page.extract_text() or "").strip()
                    if t:
                        segments.append({"type": "page", "page": i, "text": t,
                                         "image_refs": [], "raw_images": []})
        else:
            mod = __import__(have)
            reader = mod.PdfReader(str(path))
            for i, page in enumerate(reader.pages, 1):
                t = (page.extract_text() or "").strip()
                if t:
                    segments.append({"type": "page", "page": i, "text": t,
                                     "image_refs": [], "raw_images": []})
        if not segments:
            return None, "PDF 中未提取到文字（疑似扫描件/纯图片 PDF），需要 OCR 或视觉转写，不虚构识别结果", "needs-ocr"
        return {"segments": segments, "images": [], "size": size}, None, "ok"
    except Exception as e:  # noqa: BLE001
        return None, f"pdf 解析失败: {e}", "failed"


def extract_pdf_images(path: Path, out_dir: Path, limits):
    """用 pypdf 按「页→图片」抽取 pdf 内嵌图片（可选依赖）。"""
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return [], "PDF 图片抽取需要 pypdf: pip install pypdf（仅提取文本时可继续用现有依赖）"
    try:
        reader = pypdf.PdfReader(str(path))
        saved, raw = [], []
        for i, page in enumerate(reader.pages, 1):
            k = 0
            for im in page.images:
                ext = Path(im.name).suffix.lower() or ".png"
                if ext not in IMG_EXTS:
                    continue
                if len(raw) >= limits["images"]:
                    break
                k += 1
                raw.append(("pdf", None, f"page{i}_img{k}{ext}"))
                (out_dir / f"page{i}_img{k}{ext}").write_bytes(im.data)
                saved.append(f"page{i}_img{k}{ext}")
            if len(raw) >= limits["images"]:
                break
        return saved, None
    except Exception as e:  # noqa: BLE001
        return [], f"pdf 图片抽取失败: {e}"


# ---------------------------------------------------------------- TXT / MD

def extract_txt_md(path: Path, limits):
    text, err = read_text_file(path)
    if err:
        return None, err
    size = check_size(path, limits["file_mb"])
    lines = text.splitlines()
    segments, chapter = [], None
    block_no = 0
    buf, start = [], 0
    is_md = path.suffix.lower() in (".md", ".markdown")

    def flush(end_line):
        nonlocal block_no, buf, start
        if buf:
            block_no += 1
            segments.append({
                "type": "paragraph", "block": block_no, "chapter": chapter,
                "text": "\n".join(buf).strip(),
                "image_refs": [], "raw_images": [],
                "line_start": start, "line_end": end_line,
            })
        buf, start = [], end_line + 1

    for idx, line in enumerate(lines, 1):
        if is_md and re.match(r"^#{1,4}\s+\S", line):
            flush(idx - 1)
            chapter = line.lstrip("#").strip()[:60]
            start = idx + 1
            block_no += 1
            segments.append({
                "type": "heading", "block": block_no, "chapter": chapter,
                "text": line.strip(), "image_refs": [], "raw_images": [],
                "line_start": idx, "line_end": idx,
            })
            continue
        if not line.strip():
            flush(idx - 1)
            continue
        if not buf:
            start = idx
        buf.append(line)
    flush(len(lines))
    segments = [s for s in segments if s["text"]]
    if not segments:
        return None, "文件为空或仅含空白"
    return {"segments": segments, "images": [], "size": size}, None


# ---------------------------------------------------------------- 图片落盘与 manifest

def save_images(z: zipfile.ZipFile, raw_images, out_dir: Path, limits):
    """把 pptx/docx 的 raw_images 落盘。返回保存的文件名列表。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for _, target, name in raw_images:
        if len(saved) >= limits["images"]:
            break
        try:
            (out_dir / name).write_bytes(z.read(target))
            saved.append(name)
        except Exception:  # noqa: BLE001
            continue
    return saved


def seg_locator_label(seg):
    if seg["type"] in ("slide", "page"):
        return f"第{seg['page']}页"
    if "line_start" in seg:
        if seg["line_start"] == seg["line_end"]:
            return f"第{seg['line_start']}行"
        return f"第{seg['line_start']}-{seg['line_end']}行"
    if seg["type"] == "table":
        return f"表格块{seg['block']}"
    return f"段落{seg['block']}"


def seg_id(source_id, seg):
    if seg["type"] in ("slide", "page"):
        return f"{source_id}:P{seg['page']}"
    return f"{source_id}:B{seg['block']}"


def main() -> int:
    parser = argparse.ArgumentParser(description="课程材料解析器 v2：文本+图片+来源清单")
    parser.add_argument("files", nargs="+", help="输入文件路径（1 个或多个）")
    parser.add_argument("--out", default=None, help="合并输出到指定 txt 文件（供 LLM 通读）")
    parser.add_argument("--images", default=None, dest="images",
                        help="抽取内嵌图片到指定目录（每个源文件一个子目录）")
    parser.add_argument("--manifest", default=None,
                        help="生成 source_manifest.json（证据链清单，供 quiz_toolkit verify 核验）")
    parser.add_argument("--max-file-mb", type=int, default=MAX_FILE_MB)
    parser.add_argument("--max-total-mb", type=int, default=MAX_TOTAL_MB)
    parser.add_argument("--max-images", type=int, default=MAX_IMAGES)
    args = parser.parse_args()

    limits = {"file_mb": args.max_file_mb, "entries": MAX_ZIP_ENTRIES,
              "total_mb": args.max_total_mb, "ratio": MAX_RATIO, "images": args.max_images}

    manifest = {"version": 2, "generated_at": None, "extractor": "extract_text.py v2",
                "sources": [], "totals": {}}
    sections = []
    ok_count = fail_count = 0
    total_chars = 0
    total_imgs = 0
    total_segments = 0
    import datetime
    manifest["generated_at"] = datetime.datetime.now().isoformat(timespec="seconds")

    for si, raw in enumerate(args.files, 1):
        p = Path(raw)
        source_id = f"S{si}"
        print(f"--- 处理: {p.name}（{source_id}） ---")
        entry = {"source_id": source_id, "filename": p.name, "sha256": None,
                 "size_bytes": None, "format": p.suffix.lower().lstrip("."),
                 "status": "failed", "error": None, "segments": [], "images": [],
                 "stats": {"chars": 0, "pages": 0, "images": 0, "segments": 0}}
        try:
            entry["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError as e:
            entry["error"] = f"无法读取（计算散列失败）: {e}"
            manifest["sources"].append(entry)
            print(f"[失败] {entry['error']}")
            fail_count += 1
            continue
        if not p.exists() or not p.is_file():
            entry["error"] = "文件不存在或不是普通文件"
            manifest["sources"].append(entry)
            print(f"[失败] {entry['error']}")
            fail_count += 1
            continue

        ext = p.suffix.lower()
        res, err = None, None
        status = "ok"
        try:
            if ext in (".txt", ".md", ".markdown"):
                res, err = extract_txt_md(p, limits)
            elif ext == ".pptx":
                res, err = extract_pptx(p, limits)
            elif ext == ".docx":
                res, err = extract_docx(p, limits)
            elif ext == ".pdf":
                res, err, status = extract_pdf(p, limits)
                entry["status"] = status
            else:
                err = f"不支持的格式 .{ext.lstrip('.')}（支持: {' '.join(sorted(SUPPORTED))}）"
        except LimitError as e:
            res, err = None, f"拒绝解析: {e}"

        if err is not None:
            entry["error"] = err
            print(f"[失败] {err}")
            fail_count += 1
            # 纯图片/需OCR 时仍尝试抽图
            if args.images and ext in (".pptx", ".docx", ".pdf"):
                img_dir = _per_file_img_dir(Path(args.images), p)
                if ext == ".pdf":
                    imgs, img_err = extract_pdf_images(p, img_dir, limits)
                else:
                    try:
                        with safe_zip(p, limits["entries"], limits["total_mb"], limits["ratio"]) as z:
                            if ext == ".pptx":
                                slides = pptx_slide_order(z)
                                raws = []
                                for i, sn in enumerate(slides, 1):
                                    _, rids = slide_texts(z.read(sn))
                                    n = _slide_no(sn)
                                    rels = parse_rels(z, f"ppt/slides/_rels/slide{n}.xml.rels")
                                    k = 0
                                    for rid in rids:
                                        t = rels.get(rid)
                                        if not t or Path(t).suffix.lower() not in IMG_EXTS:
                                            continue
                                        if len(raws) >= limits["images"]:
                                            break
                                        k += 1
                                        raws.append(("pptx", t, f"slide{i}_img{k}{Path(t).suffix.lower()}"))
                                imgs = save_images(z, raws, img_dir, limits)
                            else:
                                root = ET.fromstring(z.read("word/document.xml"))
                                doc_rels = parse_rels(z, "word/_rels/document.xml.rels")
                                raws = []
                                for blip in root.iter(f"{NS_A}blip"):
                                    rid = blip.get(f"{NS_R}embed")
                                    t = doc_rels.get(rid)
                                    if not t or Path(t).suffix.lower() not in IMG_EXTS:
                                        continue
                                    if len(raws) >= limits["images"]:
                                        break
                                    tt = t.replace("\\", "/")
                                    tt = tt if tt.startswith("word/") else "word/" + tt
                                    k = len(raws) + 1
                                    raws.append(("docx", tt, f"docx_img{k}{Path(tt).suffix.lower()}"))
                                imgs = save_images(z, raws, img_dir, limits)
                    except (LimitError, zipfile.BadZipFile, ET.ParseError, Exception) as e:  # noqa: BLE001
                        imgs, img_err = [], f"图片抽取失败: {e}"
                if imgs:
                    total_imgs += len(imgs)
                    entry["images"] = imgs
                    entry["stats"]["images"] = len(imgs)
                    print(f"[图片] 已抽取 {len(imgs)} 张至 {img_dir.resolve()}（文本不可用，可走图片路径）")
            manifest["sources"].append(entry)
            continue

        # 成功路径（v2.1 V2-01b：兜底隔离——单个文件意外异常仅标记该文件失败，不终止整批）
        try:
            entry["size_bytes"] = res.get("size")
            segs = res["segments"]
            chars = sum(len(s["text"]) for s in segs)
            img_names = []
            if args.images:
                img_dir = _per_file_img_dir(Path(args.images), p)
                if ext == ".pptx":
                    raws = []
                    for s in segs:
                        raws.extend(s.get("raw_images") or [])
                    with safe_zip(p, limits["entries"], limits["total_mb"], limits["ratio"]) as z:
                        img_names = save_images(z, raws, img_dir, limits)
                elif ext == ".docx":
                    raws = res.get("images") or []
                    with safe_zip(p, limits["entries"], limits["total_mb"], limits["ratio"]) as z:
                        img_names = save_images(z, raws, img_dir, limits)
                elif ext == ".pdf":
                    img_names, _ = extract_pdf_images(p, img_dir, limits)
                if img_names:
                    total_imgs += len(img_names)
                if img_names:
                    print(f"[图片] {len(img_names)} 张 → {img_dir.resolve()}")

            entry["status"] = "ok"
            entry["error"] = None
            entry["images"] = img_names
            mseg = []
            for s in segs:
                sid = seg_id(source_id, s)
                refs = s.get("image_refs") or []
                if ext == "docx":
                    # docx 段落 image_refs 已是文件名；仅保留真实落盘成功的
                    refs = [r for r in refs if r in img_names]
                elif ext == "pptx":
                    refs = [n for _, _, n in (s.get("raw_images") or []) if n in img_names]
                mseg.append({
                    "segment_id": sid, "source_id": source_id,
                    "type": s["type"], "label": seg_locator_label(s),
                    "chapter": s.get("chapter"),
                    "text": s["text"],
                    "images": refs,
                })
                marker = f"【{sid}·{seg_locator_label(s)}" + (f"·{s['chapter']}" if s.get("chapter") else "") + "】"
                body = s["text"] if s["text"] else "（本片段无文字，含图片）"
                sections.append(f"{marker}\n{body}")
            entry["segments"] = mseg
            pages = sum(1 for s in segs if s["type"] in ("slide", "page"))
            entry["stats"] = {"chars": chars, "pages": pages, "images": len(img_names),
                              "segments": len(mseg)}
            total_chars += chars
            total_segments += len(mseg)
            ok_count += 1
            print(f"[成功] {chars} 字符 / {len(mseg)} 片段 / {len(img_names)} 图片")
        except Exception as e:  # noqa: BLE001 —— 记录该文件失败并继续其余材料（不吞错：错误写入 manifest）
            entry["status"] = "failed"
            entry["error"] = f"解析该文件时发生未预期错误: {type(e).__name__}: {e}"
            fail_count += 1
            print(f"[失败] {entry['error']}")
        manifest["sources"].append(entry)

    manifest["totals"] = {"sources": len(args.files), "ok": ok_count, "failed": fail_count,
                          "chars": total_chars, "segments": total_segments, "images": total_imgs}
    print(f"=== 汇总: 成功 {ok_count}/{len(args.files)}, 合计 {total_chars} 字符, "
          f"{total_segments} 片段, 图片 {total_imgs} 张 ===")
    if total_chars < MIN_VALID_CHARS and total_imgs == 0:
        print(f"[提示] 有效文本不足 {MIN_VALID_CHARS} 字，难以保证出题质量，建议补充材料。")

    if args.out and sections:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n\n".join(sections), encoding="utf-8")
        print(f"[输出] 文本: {out_path}")
    if args.manifest:
        mpath = Path(args.manifest)
        mpath.parent.mkdir(parents=True, exist_ok=True)
        mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[输出] 清单: {mpath}")
    if args.images:
        print(f"[图片] 目录: {Path(args.images).resolve()}")

    return 0 if fail_count == 0 else 1


def _per_file_img_dir(images_dir: Path, src: Path) -> Path:
    stem = re.sub(r"[\\/:*?\"<>|\s]", "_", src.stem)
    return images_dir / stem


if __name__ == "__main__":
    sys.exit(main())
