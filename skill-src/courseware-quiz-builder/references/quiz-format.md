# quiz.json 题库格式规范与出题质量标准

生成 `quiz.json` 时必须严格遵守本规范。质检脚本 `quiz_toolkit.py validate` 会按此规则逐项检查，任何 ERROR 都会导致无法渲染产出。

目录：
1. [顶层结构](#1-顶层结构)
2. [题目字段定义](#2-题目字段定义)
3. [四种题型的硬性规则](#3-四种题型的硬性规则)
4. [题量建议](#4-题量建议)
5. [难度分级定义](#5-难度分级定义)
6. [出题质量标准](#6-出题质量标准)
7. [质检脚本自动检查项](#7-质检脚本自动检查项)
8. [图片字段规范](#8-图片字段规范)
9. [证据链字段与三层验证体系（v2）](#9-证据链字段与三层验证体系v2)

---

## 1. 顶层结构

```json
{
  "title": "数据结构·树与二叉树 复习题库",
  "source_desc": "《数据结构》第4章课件（共32页）+ 个人笔记",
  "generated_date": "2026-11-11",
  "notes": "可选：给使用者的说明，如侧重第2节",
  "manifest": "source_manifest.json",
  "topics": [ {"id": "T1", "name": "二叉树性质"}, {"id": "T2", "name": "树的遍历"} ],
  "images": { "dz1": "imgs/材料图1.png" },
  "questions": [ { ... }, { ... } ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| title | 是 | 题库名称，会用于输出文件名，避免包含 `\ / : * ? " < > |` |
| source_desc | 是 | 材料来源一句话说明 |
| generated_date | 建议 | 生成日期 YYYY-MM-DD |
| notes | 否 | 备注说明 |
| manifest | 否 | source_manifest.json 相对路径（build 自动探测同目录默认名） |
| topics | 否 | 考点表 [{id,name}]，id 用 T1/T2…；供刷题页按考点聚合学习报告 |
| images | 否 | 全局共享图片表，见第 8.1 节 |
| questions | 是 | 题目对象数组，非空 |

## 2. 题目字段定义

```json
{
  "id": "Q1",
  "type": "single",
  "difficulty": "易",
  "topic": "二叉树性质",
  "source_ref": "课件第3页",
  "stem": "二叉树第 i 层（i≥1）最多有多少个节点？",
  "options": ["2i", "2^(i-1)", "i^2", "2i+1"],
  "answer": [1],
  "explanation": "由二叉树性质逐层最多翻倍，第 i 层最多 2^(i-1) 个。A/C/D 分别把层数、平方、双倍关系弄混。"
}
```

v2 证据链字段（可选，见第 9 节）：`source_id` `segment_id` `source_quote` `evidence_status`
`verification_notes` `topic_id` `knowledge_type`。

| 字段 | 必填 | 规则 |
|---|---|---|
| id | 是 | 字符串，全局唯一，统一用 `Q1`、`Q2`… 连续编号 |
| type | 是 | `single` 单选 / `multiple` 多选 / `judge` 判断 / `short` 简答 |
| difficulty | 是 | `易` / `中` / `难` |
| topic | 是 | 考点标注，≤30字，如「哈夫曼树构造」 |
| topic_id | 否（v2） | `T1`/`T2`…，与顶层 topics 对应；同一知识点的多题/变式题用同一 topic_id |
| source_ref | 是 | 材料出处定位：页码/章节/笔记位置，用于溯源（人类可读） |
| source_id | 否（v2） | `S1`/`S2`…，对应 source_manifest.json 的材料序号 |
| segment_id | 否（v2） | `S1:P3`（页）或 `S1:B12`（块），对应 manifest 片段 |
| source_quote | 否（v2） | 材料原文引用（≥8字），build 时由脚本在片段中定位核验 |
| evidence_status | 否（v2） | 层C 语义复核结论：`semantic-pass` / `needs-review` / `unresolved` |
| verification_notes | 否（v2） | 复核备注，如“存疑原因”，会展示给使用者 |
| knowledge_type | 否（v2） | `definition/property/formula/process/comparison/number/causal/application` |
| stem | 是 | 题干，≥5字符，表述完整无歧义，题干内不得泄露答案 |
| options | 客观题必填 | 非空字符串数组；简答题必须为 `[]` |
| answer | 是 | 客观题：正确选项下标数组（0 起点）；简答题：非空字符串（参考答案要点） |
| explanation | 是 | 解析，≥10字符，说明正确答案依据，客观题还需点出关键干扰项错在哪 |
| image | 否 | 题干配图：本地相对路径（相对 quiz.json）、`@key` 或 data:image base64 URL，见第 8 节 |
| option_images | 否 | 选项图数组，与 options 按下标对齐，无图选项用 "" 占位，见第 8 节 |

**兼容规则**：旧格式题库（无任何证据字段）可正常 validate/build，但会收到“无法来源核验”的 WARN，
刷题页相应题目标注“未核验”；一旦任意一题启用证据链，该题四项核心字段（source_id/segment_id/
source_quote/evidence_status）必须齐全，否则 ERROR。

## 3. 四种题型的硬性规则

- **single 单选**：选项 2-8 个（建议 4 个），恰好 1 个正确。
- **multiple 多选**：选项 3-8 个，正确答案 ≥2 个且必须少于选项总数（不允许全选）。
- **judge 判断**：`options` 必须恰好为 `["正确", "错误"]`，恰好 1 个正确。
- **short 简答**：`options` 为 `[]`，`answer` 为分点式参考答案（用①②③列出要点），`explanation` 写评分要点。

## 4. 题量建议

按去除页眉页脚后的有效字数取值，题目应分布覆盖材料各章节，不得集中在开头：

| 有效字数 | 总题量 | 结构建议 |
|---|---|---|
| 300-2000 | 6-8 | 单选2-4、判断2、简答1（材料少时可不设多选） |
| 2000-8000 | 10-15 | 单选4-6、多选2-3、判断3-4、简答2 |
| >8000 | 15-25 | 单选6-10、多选3-5、判断4-6、简答2-4，按章节分配 |

用户明确指定题量/题型时，以用户要求优先，但仍须满足各题型硬性规则。

## 5. 难度分级定义

- **易**：从原文直接读得到答案（定义、原句结论）。
- **中**：需要理解、辨析或简单推导（对比、因果、步骤顺序）。
- **难**：综合多个知识点、易混细节或需要计算应用。

合理配比：易约 30-40%、中约 40%、难约 20-30%。

## 6. 出题质量标准

1. **有据可依**：每道题（含干扰项设计思路）必须能对应到材料原文，`source_ref` 定位到页/节。
2. **不编造**：不得使用材料中不存在的数据、公式、结论。材料中可疑或错误的表述，可以照常出题，但必须在解析末尾追加：`[存疑] 材料原文如此，与通识不符，请以教材为准核对。`
3. **干扰项有效**：似是而非（常见误解、相邻概念、单位/数量级偏差），禁止「以上都不是」「全部正确」类偷懒选项。
4. **答案唯一可判**：客观题答案不依赖主观解释；避免「下列哪项最恰当」这类多答案可辩护的题干，除非干扰项明显错误。
5. **解析到位**：客观题解析 = 为什么对 + 关键干扰项为什么错；简答题解析 = 评分要点（答到什么算对）。
6. **表述干净**：题干不引用「如上页所述」等依赖排版的话；选项之间不互相提示。
7. **去重**：不出现题干相同或高度相似（仅换个数字）的重复题。

## 7. 质检脚本自动检查项

`quiz_toolkit.py validate` 自动拦截（ERROR 会阻止产出）：

- JSON 可解析；title/source_desc/questions 非空
- id 唯一；type/difficulty 枚举合法；topic/source_ref/explanation 非空且达最小长度
- 各题型选项数量、判断题固定选项、答案下标范围、单选/判断答案数=1、多选答案≥2且<选项数
- 题干完全重复（归一化后比对）
- 选项文本重复

仅提示（WARN，需人工判断）：

- id 不符合 `Q<数字>` 格式；题干相似度 ≥85% 疑似重复；「以上/都不」类偷懒选项；简答题带 options；题量≥8 但缺某种题型；topic 超 30 字

## 8. 图片字段规范

适用于图形推理、图表分析等**图片型题目**，以及题干需要配图的场景。两个均为可选字段：

```json
{
  "id": "Q5", "type": "single", ...,
  "image": "imgs/q5_stem.png",
  "option_images": ["imgs/q5_a.png", "", "imgs/q5_c.png", ""]
}
```

| 字段 | 规则 |
|---|---|
| image | 题干图。值为本地相对路径（相对 quiz.json 所在目录）或 `data:image/...;base64,...` URL |
| option_images | 选项图数组，下标与 options 对齐；无图的选项用空串 `""` 占位；数量不得超过 options |

硬性规则（质检 ERROR 拦截）：

- 仅支持 `.png .jpg .jpeg .gif .webp`；**禁止 svg**（可携带脚本）；禁止 http(s) 等外部链接与任何带协议地址
- 本地文件必须真实存在，且魔数与扩展名一致（防伪造，如把脚本改名 .png）
- 判断题/简答题携带 option_images 会被忽略并警告

### 8.1 全局图片表（共享图表，推荐用于资料分析等共享材料图）

同一张材料图被多道题引用时（典型：资料分析一组 5 小题共用同一图表），在 quiz.json 顶层定义可选字段
`images`（键值对），题目用 `@key` 引用；build 时每张图在 HTML 中只 base64 内嵌一次，避免文件膨胀：

```json
{
  "title": "...", "source_desc": "...",
  "images": { "dz1": "imgs/材料图1.png", "dz2": "imgs/材料图2.png" },
  "questions": [
    { "id": "Q1", ..., "image": "@dz1" },
    { "id": "Q2", ..., "image": "@dz1" }
  ]
}
```

- 键名仅限字母/数字/下划线/连字符（≤64 字符）；值与 image 字段遵循同样的硬性规则（本地文件或 data URL）
- `@key` 引用不存在的键 → 质检 ERROR；`images` 表中未被引用的键 → 质检 WARN
- 未定义 `images` 表时所有题目也可直接写路径/data URL，build 会自动为重复引用的同一张图合并共享

图片来源：`extract_text.py --images <目录>` 从课件抽取（pptx/pdf 按页命名，docx 按文档序）；也可用户提供。

渲染行为：

- Markdown 题库：本地图片复制到输出目录 `图片-<主题>/`，MD 以相对路径引用（打印时同目录携带）
- HTML 刷题页：全部转为 base64 内嵌，保证单文件离线双击可用（file:// 下 JS 无法读本地文件）

## 9. 证据链字段与三层验证体系（v2）

「每道题有材料依据」从流程约定升级为可机器核验的证据链。材料解析后先得到
`source_manifest.json`（extract_text.py 生成），出题时把证据写进题目，再由脚本定位核验。

### 9.1 三层验证体系

| 层 | 执行者 | 工具 | 结论口径 |
|---|---|---|---|
| 层A 结构验证 | 脚本 | `quiz_toolkit.py validate` | 字段/题型/答案/查重/图片安全 |
| 层B 来源定位 | 脚本 | `quiz_toolkit.py verify` | source_id/segment_id 存在、source_quote 能在片段中定位 |
| 层C 语义复核 | 宿主 LLM | 自审后写入 `evidence_status` | 题目是否被材料支持、答案是否有充分证据、干扰项是否有争议 |

规则核验不等于语义真实性核验：层A/B 只能证明“引用存在且可定位”，不能证明学科知识正确。
层C 由宿主模型在生成时自行完成，必须诚实标注：

- `semantic-pass`：AI语义复核通过（答案与解析均得到材料支持）
- `needs-review`：需人工复核（材料存疑、易混淆、引用了图片转写等不确定内容）
- `unresolved`：验证未通过（无法确认，应优先修复而不是交付）

没有有效证据的题目不得标注 `semantic-pass`。发现存疑时照常出题，但在 `verification_notes`
写明原因并选 `needs-review`，解析末尾追加 `[存疑]`。

### 9.2 manifest 生成与 verify 流程

```
python extract_text.py 课件.pptx 讲义.docx --manifest source_manifest.json --out extracted.txt
# （manifest: source_id S1/S2…，segment_id S1:P3/S2:B12…，含片段原文与页码定位）
# 出题时每题从 extracted.txt 找到依据片段，把 segment_id 与原文引用抄录进题目
python quiz_toolkit.py verify quiz.json            # 层A+层B 核验报告（可加 --report 生成 validation-report.json）
python quiz_toolkit.py build quiz.json -o 输出目录  # 默认 strict 门禁（详见 9.4）
```

verify 输出的每题结论：`定位通过（精确）/定位通过（近似）/来源不存在/片段不存在/引用未定位/缺引用文本/无证据字段`。
前三类之外均为确定性失败（退出码 1），必须修复后重新核验。`定位通过（近似）`表示引用与片段
最佳窗口相似度 ≥75%（可能是改写或截取），可用但建议核对。

### 9.3 build 时的证据展示

- 找到 manifest 且层B 通过：每题渲染「出处（segment_id）+ 证据原文引用 + 复核结论 + 定位结果」
- strict 门禁下缺 manifest/层B 失败：直接阻断不产出（详见 9.4）；preview 草稿页题目标注“未核验”，不伪装为已验证
- `needs-review`/`unresolved` 在刷题页以醒目徽标展示，提示使用者人工确认

### 9.4 强制门禁与 validation-report.json（v2.2 三维契约）

build 是正式交付的最后闸口，默认 `--mode strict`：

| 情况（strict） | 结果 |
|---|---|
| 层A 结构失败（含 Schema 非法/图片安全/解析-答案矛盾） | BLOCKED，退出码 1 |
| 逐题证据字段缺失（source_id/segment_id/source_quote/evidence_status 任一） | BLOCKED（B-EVIDENCE-REQUIRED）|
| 层B 来源定位失败（来源/片段/引用无法定位） | BLOCKED，退出码 1 |
| 展示引用矛盾（source_ref 页码与真实定位冲突） | BLOCKED（B-REF-CONFLICT，展示以 manifest 规范引用为准） |
| 材料文件哈希与 manifest 不符 | BLOCKED（B-SOURCE-HASH，需 --source-root 指向材料目录核对） |
| 缺失或不可用 source_manifest.json | BLOCKED（B-MANIFEST-001/002），退出码 1 |
| 语义 unresolved（C-SEM-003） | BLOCKED，退出码 1 |
| 语义未执行（无 evidence_status，C-SEM-001） | BLOCKED（正式发布要求全部题已执行语义复核）或 preview 草稿 |
| 过短引用/片段内重复（B-QUOTE-THIN / B-QUOTE-UNIQUE） | WARN 放行，逐题标注"已定位但证据不足" |
| needs-review（C-SEM-002） | WARN 放行，页面醒目标注 |

阻断时：退出码 1、零产物、**旧产物保留并显式列出**（防误认为本次成功）；渲染采用
临时目录生成→自检→原子提交，失败不留半成品。`validation-report.json`（schema
`courseware-quiz-builder/validation-report@2.2`）无论是否阻断都落盘，三维契约：

- `validation_status` ∈ PASS / WARN / NOT_VERIFIED / FAIL（验证结论，按最差 finding 推导）
- `release_status` ∈ READY / DRAFT_ONLY / BLOCKED / NOT_APPLICABLE（verify 无发布语义）
- `checks[]`：每项检查 id / execution（EXECUTED / SKIPPED / UNAVAILABLE）/ result；
  关键检查未执行必须明示（如无 manifest 时 layer_b_location=UNAVAILABLE，verify 退出码 1）

另含 `command` / `tool_version` / `input_digest`（quiz SHA-256 摘要）与逐条 findings
（rule_id / severity / question_id / message / evidence / suggested_fix）、逐题三层矩阵。

显式 `--mode preview` 仅用于预览草稿（release_status=DRAFT_ONLY）：层A 失败仍阻断，其余
放行，但输出文件名追加「（草稿）」、MD 头部与页面横幅标注「草稿·未通过完整核验」。
常见 rule_id：A-SCHEMA-001/002（顶层/questions 结构非法；questions 内非对象项报“必须是对象”，按 A-STRUCT 归类）、
A-IMG / A-EXPLAIN-CONSISTENCY、
B-SRC-LOCATE / B-MANIFEST / B-EVIDENCE-REQUIRED / B-EVIDENCE-STRIPPED / B-REF-CONFLICT /
B-SOURCE-HASH / B-QUOTE-THIN / B-QUOTE-UNIQUE、C-SEM-001/002/003。

退出码：0=命令承诺操作成功（build 产出 READY/DRAFT_ONLY；verify 核验执行且无确定性失败）；
1=验证失败 / 门禁阻断 / 关键检查未执行；2=用法/IO 错误。

> AI生成
