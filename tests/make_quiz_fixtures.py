#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_quiz_fixtures.py - v2.1/v2.2 题库夹具生成。

v2.1:
  quiz/imgs/real.png            目录内合法图片（../materials 复制）
  quiz/quiz_img_ok.json         目录内合法图片引用 → strict 可通过
  quiz/quiz_contradict.json     解析写"故选B"但答案 A → A-EXPLAIN-CONSISTENCY
  quiz/quiz_ev_tampered.json    剥离全部证据字段 → B-EVIDENCE-STRIPPED
v2.2:
  quiz/quiz_mixed_evidence.json    Q2 删光证据字段（Q1 保留）→ B-EVIDENCE-REQUIRED
  quiz/quiz_fake_ref.json          source_ref=课件第999页 → B-REF-CONFLICT
  quiz/quiz_short_quote.json       quote=栈/堆栈 → B-QUOTE-THIN（+UNIQUE）
  quiz/quiz_repeat_quote.json      短引用在片段内多次出现 → B-QUOTE-UNIQUE
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
QUIZD = ROOT / "quiz"

# 1) 目录内合法图片
(QUIZD / "imgs").mkdir(exist_ok=True)
src = ROOT / "materials" / "imgs" / "real.png"
shutil.copyfile(src, QUIZD / "imgs" / "real.png")

# 1b) 伪 PNG（魔数不符）复制进 quiz/imgs/：使 quiz_fake_png.json 成为
#     "目录内但内容伪装" 样本（v2.0 引用 ../materials/... 属穿越，已由
#     quiz_real_png.json 单独承担穿越拒绝用例）
fake_src = ROOT / "materials" / "imgs" / "fake.png"
if fake_src.is_file():
    shutil.copyfile(fake_src, QUIZD / "imgs" / "fake.png")
    fp = QUIZD / "quiz_fake_png.json"
    if fp.is_file():
        d = json.loads(fp.read_text(encoding="utf-8"))
        for q in d.get("questions", []):
            if q.get("image"):
                q["image"] = "imgs/fake.png"
        fp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

base = json.loads((QUIZD / "quiz_ev.json").read_text(encoding="utf-8"))

# 2) quiz_img_ok.json：Q1 带目录内图片引用
ok = json.loads(json.dumps(base))
ok["title"] = "目录内图片合法引用测试"
ok["questions"] = ok["questions"][:1]
ok["questions"][0]["image"] = "imgs/real.png"
(QUIZD / "quiz_img_ok.json").write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding="utf-8")

# 3) quiz_contradict.json：解析结论与答案矛盾
c = json.loads(json.dumps(base))
c["title"] = "解析结论矛盾测试"
c["questions"] = c["questions"][:1]
c["questions"][0]["explanation"] = "队列是先进先出的线性表，故选B。A 为干扰项。"
(QUIZD / "quiz_contradict.json").write_text(json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")

# 4) quiz_ev_tampered.json：剥离全部证据链字段（复用同材料生成 manifest）→ B-EVIDENCE-STRIPPED
t = json.loads(json.dumps(base))
t["title"] = "证据剥离测试"
for q in t["questions"]:
    for k in ("source_id", "segment_id", "source_quote", "evidence_status", "verification_notes"):
        q.pop(k, None)
(QUIZD / "quiz_ev_tampered.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")

# 5) v2.2 quiz_mixed_evidence.json：Q2 删光证据字段（其余保留）→ B-EVIDENCE-REQUIRED（V22-A）
m = json.loads(json.dumps(base))
m["title"] = "逐题门禁测试"
for k in ("source_id", "segment_id", "source_quote", "evidence_status", "verification_notes"):
    m["questions"][1].pop(k, None)
(QUIZD / "quiz_mixed_evidence.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")

# 6) v2.2 quiz_fake_ref.json：Q1 source_ref 伪造页码 → B-REF-CONFLICT（V22-C）
fr = json.loads(json.dumps(base))
fr["title"] = "引用伪造测试"
fr["questions"] = fr["questions"][:2]
fr["questions"][0]["source_ref"] = "课件第999页"
fr["questions"][1]["evidence_status"] = "semantic-pass"
(QUIZD / "quiz_fake_ref.json").write_text(json.dumps(fr, ensure_ascii=False, indent=1), encoding="utf-8")

# 7) v2.2 quiz_short_quote.json：quote='栈'/'堆栈' → B-QUOTE-THIN（V22-D）
sq = json.loads(json.dumps(base))
sq["title"] = "短证据测试"
sq["questions"] = sq["questions"][:2]
sq["questions"][0]["source_quote"] = "栈"
sq["questions"][1]["source_quote"] = "堆栈"
(QUIZD / "quiz_short_quote.json").write_text(json.dumps(sq, ensure_ascii=False, indent=1), encoding="utf-8")

# 8) v2.2 quiz_repeat_quote.json：短引用在片段内多次出现 → B-QUOTE-UNIQUE
#    好材料 S2:B3 段含"顺序表"两次以上的场景用 S1:P1（结构｜特点 表格中"栈"、"队列"短词
#    多次出现）。quote="队列" 在 S1:P1 文本中出现 2 次。
rq = json.loads(json.dumps(base))
rq["title"] = "短证重据复测试"
rq["questions"] = rq["questions"][:2]
rq["questions"][0]["source_id"] = "S1"
rq["questions"][0]["segment_id"] = "S1:P1"
rq["questions"][0]["source_quote"] = "队列"
rq["questions"][1]["source_id"] = "S1"
rq["questions"][1]["segment_id"] = "S1:P2"
rq["questions"][1]["source_quote"] = "堆栈"
(QUIZD / "quiz_repeat_quote.json").write_text(json.dumps(rq, ensure_ascii=False, indent=1), encoding="utf-8")

print("quiz fixtures v2.1+v2.2 ->", QUIZD)
