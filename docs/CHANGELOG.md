# 课件智练——版本迭代记录与原创性说明

## 版本迭代

### v2.2（2026-11-13）质量闭环版——反伪造核验、三维状态契约与原子化构建

基线审计复现 5 类缺陷（docs/audit/v2.2-baseline.md，复现脚本 .temp/v22-repro/）后实施：

**P0-1 逐题门禁（V22-A）**
- 混合证据题库不再整体逃逸：manifest 在场时任何一题缺 source_id/segment_id/
source_quote/evidence_status 任一字段 → `B-EVIDENCE-REQUIRED` FAIL，strict 阻断
- release_decision 独立于逐题矩阵：一题失败即 BLOCKED，不因其他题通过而放行

**P0-2 统一 Schema 入口（V22-B）**
- 新增 schema_errors()：顶层非对象/缺 questions/非数组/空数组 → A-SCHEMA-001/002，
在任何字段访问前返回；questions 内非对象项逐题报错（A-STRUCT）不中断其余题
- 空数组/null/字符串数字/嵌套错型/损坏 JSON/超大输入（截断查重键防 O(n²)）/非法
 data URL 全部稳定报错无 Traceback，Schema 失败也落盘结构化报告

**P0-3 反伪造（V22-C/D）**
- canonical_ref_of()：由 manifest 结构化字段生成规范出处（如“课件《good.pptx》第1页”），
产物优先渲染 canonical，source_ref 仅作注释
- `B-REF-CONFLICT`：source_ref 页码/段号与真实定位矛盾 → FAIL（“第999页”无法再冒充）
- `B-SOURCE-HASH`：按 --source-root 重算材料 SHA-256，与 manifest 不符 → 材料被替换，阻断
- `B-QUOTE-THIN` / `B-QUOTE-UNIQUE`：短证据已定位但证据不足/多处歧义 → WARN，不拢统
判“全部通过”，不一刀切拒绝

**P0-4 三维状态契约与退出码（V22-E1/E2）**
- validation-report.json schema@2.2：validation_status（PASS/WARN/NOT_VERIFIED/FAIL）、
release_status（READY/DRAFT_ONLY/BLOCKED/NOT_APPLICABLE）、checks[]{id,execution,result}
（EXECUTED/SKIPPED/UNAVAILABLE）分离；blocked ⟺ BLOCKED 恒等
- 退出码：0=承诺操作成功；1=验证失败/阻断/关键检查未执行；2=用法/IO
- verify 无 manifest：exit 1 + layer_b=UNAVAILABLE 明示（v2.1 曾 exit 0）
- verify --report - 支持 stdout；input_digest（题库 SHA-256）与 tool_version 落盘

**P0-5 原子化构建**
- 渲染在 .build-tmp-{pid} 临时目录完成并自检，通过后 os.replace 提交；失败零半成品
- 阻断/失败时旧正式产物保留并在终端整版警告“历史产物不代表本次验证结果”
（v2.1 的“清理陈旧产物”契约按用户指令反转，避免误毁已验证成果）

**P1 测试体系扩充**
- 新增 4 个套件：test_schema_v22（16）/test_source_integrity_v22（12）/
test_release_gate_v22（12）/test_security_v22（9）；test_build_gate 按 v2.2 契约修订
- 自动化 64 → 113 用例全绿；浏览器 E2E 新增 10 组（累计 32）全过

**P1 真实材料评测**
- 9 份真实备考材料（约 4.0MB，2845 片段）解析 9/9 成功；8 题真实证据链题库：
verify 8/8 精确定位、哈希校验 PASS、strict build WARN/READY（Q5 needs-review 诚实标注）
- 详见 docs/REAL_MATERIAL_EVAL.md

**P1 文档与发布链**
- SKILL.md/quiz-format.md/generation-workflow.md 同步 v2.2 门禁与命令；
工具 docstring 版本号与规范文本 A-SCHEMA 编号口径对齐（删 003 死键）
- 发布链：6 文件同步注册目录哈希一致 → quick_validate → Register success →
claw_scan 0 高风险 → dist/courseware-quiz-builder-v2.2.zip
- 独立复核（隔离上下文）：K1-K10 中 9 PASS + 1 CONDITIONAL（文档口径），已全部修正

### v2.1（2026-11-13）质量门禁版——让未通过核验的题库无法冒充正式交付

基线审计复现 4 项已报告缺陷 + 3 项新发现（docs/BASELINE_AUDIT.md）后按 P0→P1→P2 实施：

**P0-1 Office 返回值契约（V2-01）**
- extract_pptx/extract_docx 全部早退/异常分支统一返回 (result, error) 二元组；
  main() 单文件兜底隔离；新增 6 类边界夹具（无slides/缺document.xml/空body/
  无文本/类型伪装/非zip）全部明确报错无 Traceback；混合批次坏文件不毁好文件

**P0-2 强制质量门禁（V2-02，本次核心）**
- 三层验证统一 findings 契约（rule_id/severity/question_id/message/evidence/suggested_fix）
- build 默认 strict：层A/层B FAIL、缺 manifest、证据剥离（B-EVIDENCE-STRIPPED）、
  语义 unresolved（C-SEM-003）→ exit 1 零产物+清理陈旧产物
- 显式 --mode preview：仅层A阻断，其余放行但文件名/MD/页面横幅/报告四处标注草稿
- validation-report.json（schema@2.1）无论阻断与否落盘：逐条 findings + 逐题三层矩阵
- 新增确定性检测：解析-答案矛盾（A-EXPLAIN-CONSISTENCY）

**P0-3 图片路径安全（V2-03）**
- 包含判定改用 Path.resolve()+is_relative_to（展开符号链接，弃字符串前缀）
- ../ 与 ..\ 穿越、绝对路径、http/file 协议、目录内缺失、svg、伪装魔数分类拒绝；
  单图 ≤20MB；目录内合法引用（正/反斜杠）与 data URL 不受影响

**P0-4 前端考试状态机（V2-04）+ 导入校验（V2-05）**
- state v3：examPaper（attempt_id/qids/idx/submitted+交卷快照）驱动
  IDLE→IN_PROGRESS→SUBMITTED→REVIEW；新卷新 ID 清空作答、qHistory/attempts 保留；
  中途刷新恢复；重复交卷守卫；旧卷成绩快照回看；再考一次/放弃入口
- 导入先 normalizeState 全字段 Schema 校验（非法拒绝且状态不变），v2 记录自动迁移；
  进行中考试拒绝导入；_gate 草稿横幅+核验 chip 注入页面

**P1 文档与测试体系**
- SKILL.md/quiz-format.md 同步门禁说明（9.4 节门禁契约）
- 测试套件重组为 7 个分文件 + fixtures 脚本：36→64 用例全绿；v2.0 漏洞用例
  （real_png 通过断言）翻转为穿越拒绝断言并新增合法正例
- 浏览器 E2E 16→22 场景全过（考试状态机 8 场景/门禁可视化/复练闭环/导入导出/健壮性）

**修复的 v2.0 缺陷**：V2-01/01b/02/03/04/05 + 新发现 V2-06（单图无上限，并入 P0-3）、
V2-07（verify 无机器可读输出，并入 P0-2）+ 新发现两处（verify 引用 manifest 不存在崩溃、
矛盾规则被 answer 关键词抢占归类）

### v1（2026-11-10 ~ 11-11）点课成题·课件刷题工坊

- 初版技能：extract_text（正则解析 OOXML）→ quiz.json（LLM 手写）→ validate/build → MD + HTML
- 四题型质检：字段/枚举/答案下标/查重/偷懒选项/图片白名单+魔数
- 图片能力：内嵌图抽取、题干图/选项图、@key 共享图（每图仅内嵌一次）
- 4 套华能真题题库实战交付（146 题，含图片题 36 题）
- 提交前安全审查修复 5 项（ZIP 分隔符/MD 注入/HTML 注入/提示注入条款/标题动态化）

### v2（2026-11-12）课件智练——特等奖冲刺升级

基线审计（docs/BASELINE_AUDIT.md，10 项指定检查 + 10 项自查发现）后按 P0→P1 实施：

**P0 可靠解析**
- `extract_text.py` 重写：ElementTree 真 XML 解析（修复 `<a:t xml:space>` 带属性节点漏提）；
  pptx 按 presentation.xml 演示顺序；docx 按文档序遍历段落/表格（表格行列结构保留）/
  图片（blip→rels 文档序）；md/txt 分段与章节；PDF 三态（已提取/需OCR/失败）
- 资源上限四重防护：单文件 200MB、解压总量 1500MB、zip 条目 4000、单条目压缩比 200
- 水印形状过滤（pptx 按 Watermark 形状名 / docx 跳过 w:vanish 隐藏文本）

**P0 证据链（本次核心改造）**
- source_manifest.json：source_id/segment_id/片段原文/页码定位/sha256
- quiz.json v2 证据字段：source_id/segment_id/source_quote/evidence_status/
  verification_notes/topic_id/knowledge_type（向后兼容旧格式）
- 三层验证：validate（层A 结构）→ verify（层B 来源定位：精确/模糊≥75%窗口）→
  evidence_status（层C 语义复核三态）；build 自动注入定位结果；页面诚实区分
  已核验/需人工复核/未核验，绝不伪装已验证

**P1 出题工作流**：references/generation-workflow.md 九步流水线（知识点清单→覆盖计划
先行→分批出题→三层验证）；可配置参数表；变式题与针对性强化离线约束

**P1 刷题页全面重构**（435 行 → 约 1300 行）：题库首页 / 复习（即时反馈+证据展开）/
考试（整卷判分）/ 成绩解析（客观判分与简答自评分列、考点正确率）/ 错题中心（考点分组、
错误原因、重做本题·全部、作答历史前后对比，复练不影响历史）/ 学习报告（掌握度=答对÷作答
统计+口径说明、薄弱建议、历次成绩、导出导入）；键盘操作；移动端响应式；存储失败警示+导出兜底

**修复的 v1 缺陷**：A1 属性节点、A2 魔数-扩展名一致性、A5/A6 错题复练闭环、A7 静默失败、
A10 两处文档失实、B1-B10（见 BASELINE_AUDIT.md 第四节）

## 原创性说明

- 本技能（SKILL.md、两个 Python 脚本、HTML 模板、两份 references 规范、测试夹具与
  测试套件、全部参赛文档）均为参赛者本人原创开发，未复制任何现有技能/开源项目代码
- 未使用任何受版权保护的商业题库内容；演示与测试全部使用合成材料（标准库生成的
  pptx/docx/md）或本人有权处理的备考材料
- 开发过程真实执行并留存证据：113 项自动化测试（v2.2）+ 32 场景浏览器 E2E 截图 +
  validation-report.json 机器可读验证报告 + 真实材料 9/9 解析评测 + 安全扫描 0 高风险
- AI 辅助声明：开发过程由参赛者主导设计与验收，AI 工具参与代码起草与文档撰写
  （平台在生成文件中注入 AIGC 水印，符合大赛 AI 应用创新定位）
- 产出文件中的题目内容由 AI 基于用户材料生成，页面明确标注生成属性与核验状态

## 附：主要改动文件清单（v2.2）

| 文件 | 改动 |
|---|---|
| scripts/quiz_toolkit.py | schema_errors/canonical_ref/哈希核验/逐题门禁/三维报告/原子化构建（约 1245→1771 行，TOOL_VERSION=2.2） |
| scripts/extract_text.py | v2.2 本轮未改动（v2.1 契约维持） |
| assets/quiz-template.html | canonical 出处优先渲染、引用矛盾徽标、三维状态 chip/横幅 |
| references/quiz-format.md | 9.4 节重写为三维契约；A-SCHEMA 编号口径校正 |
| references/generation-workflow.md | 第7/9步命令补 --source-root、门禁与报告说明 |
| SKILL.md | 第6/8步 v2.2 命令与阻断条件；异常表补充哈希/引用矛盾/无 manifest 等 |
| tests/ | 新增 4 套件 49 用例（累计 113）；新增 v2.2 题库夹具 4 类 |
| docs/ | 新增 REAL_MATERIAL_EVAL.md、PLATFORM_ACCEPTANCE.md、audit/v2.2-baseline.md；TEST_REPORT/REVIEW_REPORT/CHANGELOG/README 等同步 v2.2 |

> AI生成
