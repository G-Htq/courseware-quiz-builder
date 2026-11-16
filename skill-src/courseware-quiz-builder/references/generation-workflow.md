# 出题工作流规范（v2）——从材料到可核验题库的九步流水线

本规范约束 LLM 在 TeleAgent 中执行点课成题-课件刷题工坊时的出题流程（v2.2 起含反伪造核验
与强制门禁，命令参数以 SKILL.md 工作流程为准）。目标：题目有据可依、
覆盖均衡、可审计、参数可配置。与 quiz-format.md（数据契约）配合使用。

## 流水线总览

```
材料接收 → 解析(manifest) → 知识点提取 → 考点覆盖规划 → 分批出题
   → 层A 规则质检 → 层B 来源核验 → 层C 语义复核 → 渲染交付
```

任何一步失败都按 SKILL.md 异常表降级，不得跳过质检或伪造核验结论。

## 第 1 步：材料接收与参数确认

可配置参数（全部来自用户请求或默认值，**不写死在提示词里**）：

| 参数 | 默认 | 说明 |
|---|---|---|
| 题量 | 按 quiz-format.md 第 4 节字数分档 | 用户指定时优先，但须告知材料可支撑的实际上限 |
| 题型比例 | 单选为主，多选/判断/简答按材料适配 | 用户可指定如“只要单选” |
| 难度倾向 | 易 30-40% / 中 40% / 难 20-30% | 用户可指定“都是难题” |
| 章节范围 | 全部材料 | 用户可指定“只出第三章” |
| 用途模式 | 复习 | 考试冲刺时可提高难与综合题占比 |

用户未指定的参数直接用默认值推进，不反复确认（快速交付偏好）。

## 第 2 步：解析（extract_text.py）

```
python "<技能目录>/scripts/extract_text.py" <材料文件...> \
    --out .temp/extracted.txt --manifest .temp/source_manifest.json \
    --images .temp/imgs
```

产出三个资产：合并文本（供通读）、source_manifest.json（证据链锚点）、图片目录。
manifest 中每个片段有稳定 segment_id（S1:P3 / S1:B12），后续每题引用它。

## 第 3 步：知识点提取

通读 extracted.txt，产出**考点清单**（写入 .temp/topics.md，供审计）：

```
T1 栈与队列的定义与特性       | S1:P1, S1:P2 | definition/property | 重要度 高
T2 线性表存储结构对比         | S2:B3        | comparison          | 重要度 中
T3 二叉树遍历顺序             | S3:B5        | process             | 重要度 高
```

规则：
- 每条记录 topic_id（T1/T2…）、名称、segment_id 列表、knowledge_type、重要度
- 重要度依据：定义性/考试高频/篇幅占比；纯过渡性语句不作为考点
- 材料可疑表述照常列入，但标注“存疑”

## 第 4 步：考点覆盖规划

先出计划再出题（**禁止直接开写题目**）：

1. 按章节长度与重要度为考点分配题量：材料前部/后部均衡，不集中在开头几页
2. 每个考点分配 1-3 题；重要考点可出“原题 + 变式”两题（同一 topic_id）
3. 题型适配：definition→单选/判断；process→多选/简答；number→单选计算
4. 产出**覆盖计划表**（追加到 .temp/topics.md）：

```
| 考点 | 题号 | 题型 | 难度 | segment |
| T1   | Q1,Q2 | 单选,判断 | 易,易 | S1:P1, S1:P2 |
```

5. 材料不足时：明确说明可支撑题量与缺口（如“表格仅2行，数字题最多1道”），
   不得为凑题量凭空补充材料外知识

## 第 5 步：分批出题

按覆盖计划逐考点生成题目，写入 quiz.json：

- 每题从对应 segment 抄录 source_quote（材料原文，≥8 字，**逐字引用不改写**）
- 干扰项设计来自：常见误解、相邻概念、数量级/单位偏差、因果倒置——
  禁止“以上都不是”类无效选项（质检会警告）
- 变式题（同 topic_id 不同题干角度）用于针对性强化；变式与原题题干相似度
  会被质检提示，属预期，在 notes 说明即可
- 简答题 answer 用①②③分点；解析写评分要点
- 顶层写 topics 表（与第 3 步清单一致）与 manifest 字段

## 第 6 步：层A 规则质检（脚本，不可跳过）

```
python "<技能目录>/scripts/quiz_toolkit.py" validate .temp/quiz.json
```

ERROR 逐条修复重跑（最多 3 轮）；WARN 逐条人工评估。

## 第 7 步：层B 来源核验（脚本）

```
python "<技能目录>/scripts/quiz_toolkit.py" verify .temp/quiz.json --source-root <材料目录>
```

来源不存在/片段不存在/引用未定位 = 确定性失败，必须回第 5 步修正
（通常是 segment_id 抄错或 quote 改写了原文——把引用改回逐字）。
另有三类新增拦载/标记：source_ref 展示引用与真实定位矛盾（B-REF-CONFLICT）、
材料文件哈希与 manifest 不符（B-SOURCE-HASH，材料被替换）、短引用质量标记
（B-QUOTE-THIN / B-QUOTE-UNIQUE，WARN，建议补长引用）。

## 第 8 步：层C 语义复核（LLM 自审）

对每题自问并写入 evidence_status：
- 题干是否被 source_quote 直接支持？（是→可 semantic-pass）
- 正确答案是否无争议？干扰项是否可能被辩护为也对？
- 解析与答案是否一致？是否引用了材料外事实？

任一不确定 → `needs-review` + verification_notes 写明原因；
确认无法成立 → `unresolved`，回第 5 步重出该题。
**没有有效证据的题不得标 semantic-pass。**

## 第 9 步：渲染交付

```
python "<技能目录>/scripts/quiz_toolkit.py" build .temp/quiz.json -o <输出目录> --source-root <材料目录>
```

build 默认 strict 门禁：层A/层B 任何 FAIL、逐题证据字段缺失（B-EVIDENCE-REQUIRED）、
语义未执行、材料哈希不符、缺 manifest → 阻断（exit 1，零产物，旧产物保留但整版
提示防误认）；产物在临时目录完整渲染自检通过后原子提交。
`validation-report.json`（v2.2 三维契约：validation_status / release_status /
checks 执行状态）无论阻断与否都落盘，按 findings 逐项修复后重跑。

交付时向用户报告：
题量分布、三层验证结论（结构/定位/语义各自通过数）、needs-review 题号清单、
产出文件路径、刷题页五种用法（复习/考试/错题中心/学习报告/导出备份）。

## 审计与记录

quiz.json 顶层可写 `notes` 记录：覆盖策略、补写解析的题号、存疑题号。
.temp/topics.md（考点清单+覆盖计划）保留到交付，便于复核“为什么出这些题”。

## 针对性强化的离线约束

离线刷题页**不能**声称实时生成 AI 变式题。强化路径：
1. 刷题页学习报告给出薄弱考点 → 用户把考点告诉 TeleAgent
2. TeleAgent 再次调用本技能，对该考点材料片段重新出题（可要求变式）
3. 可在初次出题时就为易错考点预生成 1 道变式题（同 topic_id），
   作为离线替代

> AI生成
