# REAL_MATERIAL_EVAL - 真实课件评测报告（v2.2）

> 评测时间：2026-11-13 ｜ 环境：Windows 11 + Python 3.12.13（PDF 用临时目录
> `.temp/pylibs-v22` 内 pypdf）｜ 材料：参赛者本人备考材料副本（已授权用于技能效果评测，
> 产物中的个人信息已最小化，仅保留题目与组织公开信息）
> 评测定位：**工程链路评测**——验证"解析→证据链→反伪造核验→门禁→产物→刷题页"在真实
> 材料上的可用性；**不是**题库内容质量的学术评测（见文末局限）。

## 一、评测材料（9 份，约 5.0MB）

| 批次 | 来源 | 文件 | 格式 | 大小 | 片段数 | 状态 |
|---|---|---|---|---|---|---|
| big6 | S1 | 华能集团--通信类真题.docx | docx | 21,876B | 351 | ok |
| big6 | S2 | 华能集团--电力类真题.docx | docx | 92,173B | 351 | ok |
| big6 | S3 | 华能集团--会计类真题.docx | docx | 27,222B | 351 | ok |
| big6 | S4 | 华能集团--机械类真题.docx | docx | 23,420B | 352 | ok |
| big6 | S5 | 华能集团--真题1.docx | docx | 1,342,542B | 431 | ok |
| big6 | S6 | 华能集团--真题2.docx | docx | 2,352,944B | 429 | ok |
| small | S1 | 华能集团--计算机类真题.docx | docx | 21,744B | 352 | ok |
| small | S2 | 华能集团企业文化练习题docx.docx | docx | 17,640B | 211 | ok |
| pdf | S1 | 华能集团--24学生版.pdf | pdf | 1,120,647B | 17 | ok |

**解析结果：9/9 成功、0 失败**；合计 2,845 片段、95,654 字符、0 张内嵌图片
（材料本身不含图，图片题能力由合成夹具覆盖）。docx 批次解析约 0.2s；PDF 为文本型，
借助 pypdf 提取 17 个片段。

## 二、评测题库（8 题，来自真实材料）

基于 small 批次（计算机类真题 + 企业文化练习题）经九步工作流出题，manifest 锚点
逐题绑定（quiz-real.json）：

| 题 | 题型 | 难度 | 考点 | 证据锚点 | 语义状态 |
|---|---|---|---|---|---|
| Q1 | 单选 | 易 | 数据库基础 | S1:B2 | semantic-pass |
| Q2 | 单选 | 中 | 关系代数 | S1:B23 | semantic-pass |
| Q3 | 判断 | 易 | 数据库基础 | S1:B30 | semantic-pass |
| Q4 | 多选 | 中 | 企业文化 | S2:B57 | semantic-pass |
| Q5 | 判断 | 中 | 企业文化 | S2:B58 | **needs-review（诚实标注）** |
| Q6 | 单选 | 中 | 企业文化 | S2:B65 | semantic-pass |
| Q7 | 简答 | 中 | 企业文化 | S2:B50 | semantic-pass |
| Q8 | 单选 | 中 | 数据库基础 | S1:B11 | semantic-pass |

题型分布：单选 4 / 多选 1 / 判断 2 / 简答 1；难度：易 2 / 中 6 / 难 0；
考点：数据库基础 3 / 关系代数 1 / 企业文化 4。Q5 因材料表述可作多角度理解，
按"没有有效证据不得标通过"原则标 needs-review，未强标通过。

## 三、反伪造核验结果（v2.2 核心）

`verify --source-root`：

- 来源定位：**8/8 located-exact（精确）**，source_quote 均为对应片段原文子串
- 材料完整性：source_file_integrity **EXECUTED / PASS**（SHA-256 与 manifest 一致）
- canonical 出处：产物展示"讲义《华能集团--计算机类真题.docx》段落2（S1:B2）"
  等规范引用；source_ref 与真实定位交叉核对无不一致

## 四、strict 门禁与报告（schema@2.2）

| 项 | 实测值 |
|---|---|
| validation_status | **WARN**（唯一 finding：C-SEM-002 Q5 需人工复核） |
| release_status | **READY**（needs-review 属诚实降级，不阻断正式发布） |
| checks[] | layer_a_structure PASS / manifest_load PASS / source_file_integrity PASS / layer_b_location PASS / layer_c_semantic_rules WARN / image_security PASS —— **六项全部 EXECUTED** |
| tool_version | 2.2 ｜ schema `courseware-quiz-builder/validation-report@2.2` |

产物（`.temp/v22-real/out/`）：刷题页 HTML 79,907 字节、题库 MD 7,464 字节、
validation-report.json 3,089 字节。

## 五、产物浏览器冒烟（真实 Chromium）

打开产物刷题页（本地 HTTP）：

- 首页：题量 8（单选4 多选1 判断2 简答1）、难度 易2·中6·难0、考点 3；
  chip 显示 **"核验：WARN · 发布：READY · strict模式"**；证据链说明
  "8/8 题携带来源证据；8 题通过脚本定位核验；1 题标注需人工复核"
- 复习模式：Q1 选 A → 即时判对；解析与出处正常；展开「来源证据」显示
  **材料原文 + canonical 出处 + "来源已定位（精确）" + "AI语义复核通过" + 复核备注**
- Q5：题卡显示 **"需人工复核"** 徽标（页面不把 needs-review 冒充通过）
- 截图：`evidence/v22-real-quiz.png`

全量 32 场景 E2E（考试状态机/错题闭环/导入导出/草稿横幅/移动端）以合成夹具题库执行
（状态机与材料无关，见 TEST_REPORT 第五节）；本评测补齐"真实材料产物可用"这一维度。

## 六、局限与诚实申报

1. 材料均为参赛者本人备考材料，评测覆盖工程链路；题库学术内容正确性未做全量人工判卷
   （Q5 保留 needs-review 作为降级示例，未强标通过）。
2. 材料不含图片，图片题能力仍由合成夹具覆盖（无带图真实 PDF/docx 样例）。
3. 最大真实文件约 2.4MB；>50MB 课件性能仍为未验证项（见 KNOWN_LIMITATIONS）。
4. 解析耗时为本机小体积材料的量级参考，不代表大文件线性或次线性外推。

> AI生成