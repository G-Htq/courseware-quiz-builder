# 点课成题-课件刷题工坊 v2.2——测试与质量验收报告

> 测试日期：2026-11-13 ｜ 环境：Windows 11 + PowerShell 5.1 + Python 3.12.13（核心功能仅标准库；
> PDF 解析运次借助临时目录内 pypdf）｜ 浏览器：Playwright Chromium v24（本地 HTTP 服务，
> 禁 file:// 直测）｜ 自动化测试材料为合成数据；真实材料评测使用参赛者本人备考材料副本（见
> REAL_MATERIAL_EVAL.md）。

## 一、测试命令（可复现）

```
cd F:\Project\新建文件夹\课件智练v2
python tests\run_tests.py            # 113 项自动化测试（unittest 全绿）
```

浏览器 E2E：v2.1 轮 22 场景（tests/e2e/E2E_CHECKLIST.md）+ v2.2 轮 10 组
（tests/e2e/E2E_CHECKLIST_V22.md），均已实际执行，截图归档 `evidence/`。
分层验收状态见第七节。

## 二、自动化测试结果（tests/ 分文件套件，10 个文件）

**总数 113 ｜ 通过 113 ｜ 失败 0 ｜ 错误 0**（`Ran 113 tests ... OK`，实测输出；
独立复核代理复跑一致）

| 测试文件 | 用例数 | 结果 | 覆盖 |
|---|---|---|---|
| test_extract_text.py | 17 | 全过 | pptx 属性节点/演示顺序/表格/水印过滤；docx 段落/表格/隐藏文本/图片；md 分段；manifest 结构；6 类降级 |
| test_office_edge_cases.py（v2.1 新增） | 5 | 全过 | 6 类 Office 边界文件明确报错无 Traceback；混合批次 2坏+2好 互不破坏；全坏诚实记录 |
| test_quiz_validation.py | 13 | 全过 | 层B 定位正反例；无 manifest 诚实跳过；伪 PNG 魔数；../ 穿越拒绝；解析-答案矛盾；旧格式兼容 |
| test_build_gate.py（v2.1 新增，v2.2 修订） | 12 | 全过 | strict 通过；层B 失败/缺 manifest/矛盾/证据剥离阻断零产物；**阻断保留旧产物并整版警告（v2.2 契约反转）**；preview 草稿四处标注；preview 层A 仍阻断；C-SEM-003 |
| test_path_security.py（v2.1 新增） | 11 | 全过 | ../ 穿越、..\ 变体、绝对路径、http/file 协议、目录内缺失、svg、伪装魔数拒绝；合法相对路径/data URL 放行 |
| test_skill_structure.py | 6 | 全过 | frontmatter；门禁文档一致性；文件结构；模板占位符唯一；前端静态特征（无 state.submitted 残留）；两脚本编译 |
| test_schema_v22.py（v2.2 新增） | 16 | 全过 | 顶层空数组/null/字符串数字；空对象缺 questions；questions 为字符串/空数组/混入字符串数字null/全字符串；嵌套类型错；id 缺失与重复；损坏 JSON；超大输入不挂起；非法 data URL；Schema 失败仍落盘报告并 verify exit≠0 |
| test_source_integrity_v22.py（v2.2 新增） | 12 | 全过 | source_ref=第999页被 verify 拒绝（exit1）+ strict 阻断；canonical 引用进入产物；坏 source/segment 仍拒；材料 SHA-256 一致/不符/不可达三态；篡改材料阻断；短引用 THIN 标记不阻断；重复短引用 UNIQUE；正常引用无质量标记 |
| test_release_gate_v22.py（v2.2 新增） | 12 | 全过 | 混合证据（Q2 缺证）strict 阻断、preview 草稿放行；语义未执行 NOT_VERIFIED 阻断 strict；渲染失败零半成品；重复构建可用；草稿产物隔离；verify 退出码矩阵；无 manifest exit1；build 退出码矩阵；状态不矛盾（blocked⟺BLOCKED）；verify --report - 输出 stdout；input_digest 落盘 |
| test_security_v22.py（v2.2 新增） | 9 | 全过 | 恶意材料文本不影响构建；产物无原始 script/onerror；MD 无激活链接；模板无外链扩展；产物无外链扩展；前端图片白名单钳制；材料指令文本仅作数据；SKILL.md 指令隔离条款在位 |

## 三、v2.2 五类缺陷反例矩阵（全部实锤复现→修复→回归）

基线审计见 `docs/audit/v2.2-baseline.md`（复现脚本 `.temp/v22-repro/`）。

| 编号 | 缺陷（复现实锤） | v2.2 结果 | 回归用例 |
|---|---|---|---|
| V22-A | Q2 删光证据字段，strict 仍 exit 0 并产出 HTML | exit 1 + `B-EVIDENCE-REQUIRED@Q2`，零产物 | test_release_gate_v22::mixed_evidence |
| V22-B1 | 顶层 `[]` → AttributeError 崩溃 | exit 1 结构化 `A-SCHEMA-001`，无 Traceback | test_schema_v22::top_level_empty_array 等 |
| V22-B2 | questions 混字符串 → build 崩溃 | 逐题“必须是对象”（A-STRUCT）+ 继续处理其余题，exit 1 | test_schema_v22::questions_mixed_types |
| V22-C | source_ref=“课件第999页” 仍 PASS | verify exit 1 + `B-REF-CONFLICT`；strict 阻断；产物展示 canonical 真实页码 | test_source_integrity_v22::fake_ref |
| V22-D | quote=“栈”（2字）拿到 located-exact 无提示 | 定位通过但 `B-QUOTE-THIN` WARN；多次出现加 `B-QUOTE-UNIQUE` | test_source_integrity_v22::thin_quote |
| V22-E1 | 报告 overall=WARN 但 blocked=true 自相矛盾 | 三维契约：validation_status/release_status/checks 分离，不矛盾 | test_release_gate_v22::status_no_contradiction |
| V22-E2 | verify 无 manifest 仍 exit 0 | exit 1 + layer_b=UNAVAILABLE 明示“关键检查未执行” | test_release_gate_v22::verify_no_manifest |
| 新增 N1 | 超长题干查重 O(n²) 风险 | 查重键截断 500 字符+警告，超大输入测试不挂起 | test_schema_v22::huge_input_no_hang |

## 四、门禁反例矩阵（v2.1 建立、v2.2 扩展，全部拦截）

| 反例 | strict 结果 |
|---|---|
| 层B 引用错位仍渲染 | exit 1，零产物（B-SRC-LOCATE） |
| 缺 manifest 静默放行 | exit 1（B-MANIFEST-001） |
| 解析结论与答案矛盾 | exit 1（A-EXPLAIN-CONSISTENCY） |
| 证据剥离绕过核验 | exit 1（B-EVIDENCE-STRIPPED） |
| 逐题证据缺失（v2.2） | exit 1（B-EVIDENCE-REQUIRED） |
| 展示引用伪造（v2.2） | exit 1（B-REF-CONFLICT） |
| 材料文件被替换（v2.2） | exit 1（B-SOURCE-HASH） |
| ../ 与 ..\ 穿越、绝对路径、协议外链、伪装魔数 | exit 1（路径/魔数拒绝） |
| 语义未执行/未通过伪装交付 | exit 1（NOT_VERIFIED / C-SEM-003） |
| 非法 JSON 任意形态（v2.2） | exit 1，稳定编号不崩溃 |
| 渲染期异常（v2.2） | 零半成品；旧产物保留+整版警告；报告 release=BLOCKED |

## 五、浏览器 E2E（真实 Chromium，两轮共 32 场景全过）

**v2.1 轮 22 场景**（tests/e2e/E2E_CHECKLIST.md）：考试状态机 8（含 V2-04 回归）/门禁
可视化 2/错题复练闭环 5/导入导出 Schema 4/健壮性 3（存储禁用/375px/键盘）。

**v2.2 轮 10 组**（tests/e2e/E2E_CHECKLIST_V22.md，页面由 v2.2 模板构建）：

- G1 复习模式 + canonical 出处展开（“课件《good.pptx》第1页”）
- G2 考试全流程（4 题交卷 `exam:3/4`，成绩单含试卷 ID）
- G3/G3b 连续两次考试 attempt 隔离 + 旧卷逐题回看
- G4 错题复练 4/4 全纠正，attempts 三段链（3/4→0/4→4/4），错题 4→0
- G5 学习报告（历次成绩表 4 行、掌握度口径、薄弱建议）
- G6 导出真实下载→清空→导入全量回环（paperId 快照恢复）
- G7 刷新恢复复习进度
- G8 草稿横幅：含“发布状态 DRAFT_ONLY”+ 核验 FAIL chip（严格分发）
- G9 存储禁用降级横幅（功能不中断）
- G10 键盘 + 375px 移动端零横向溢出

strict 正式页 chip：`核验：WARN · 发布：READY · strict模式`，无草稿横幅。
截图：`evidence/v22-e2e-report.png`、`evidence/v22-e2e-draft-banner.png`。

## 六、真实课件评测摘要（详见 docs/REAL_MATERIAL_EVAL.md）

- 9 份真实备考材料（6 套真题 docx + 企业文化 docx + 计算机类 docx + 24 学生版 PDF），
  共约 4.0MB、2845 个片段、95654 字符，**解析 9/9 成功**（docx 单次 0.21s；
  PDF 借助临时目录 pypdf）
- 基于真实材料出 8 题（3 考点：数据库基础/关系代数/企业文化；覆盖易/中两档，四种题型）
- verify：8/8 精确定位 + 材料哈希 EXECUTED/PASS；strict build：validation=WARN
  （Q5 needs-review 诚实标注）、release=READY，checks[] 六项全 EXECUTED
- 产物：刷题页 79907 字节 / MD 7464 字节 / validation-report.json（schema@2.2）

## 七、v2.1 → v2.2 回归对照

| 缺陷（v2.2 基线编号） | v2.1 行为 | v2.2 结果 | 回归用例 |
|---|---|---|---|
| V22-A 逐题证据缺失被整体逃逸 | Q2 删证仍 exit 0 产出 | 逐题阻断 B-EVIDENCE-REQUIRED | release_gate 混合证据 |
| V22-B 非法 JSON 崩溃 | 顶层[]/混类型 AttributeError | 统一 Schema 入口，结构化报错 | schema 全矩阵 16 例 |
| V22-C 展示引用可伪造 | “第999页”仍 PASS | 与真实定位交叉核对，canonical 优先 | source_integrity 12 例 |
| V22-D 短证据无质量维度 | 2 字引用“通过” | THIN/UNIQUE WARN 区分 | source_integrity 短引用 |
| V22-E 状态/退出码矛盾 | overall=WARN+blocked=true；无 manifest exit 0 | 三维契约+退出码矩阵 | release_gate 12 例 |
| 原子化构建 | 失败可能留半成品/删旧产物 | 临时目录自检后提交；旧产物保留+警告 | release_gate 渲染失败 |
| v2.1 全部缺陷（V2-01~05 等） | — | 维持修复不回退（全量回归通过） | 原 64 例全过 |

## 八、分层验收状态（诚实申报）

| 层级 | 内容 | 状态 |
|---|---|---|
| L1 代码级 | 两脚本 py_compile、SKILL.md frontmatter、模板占位符、静态规范测试 | ✅ 通过 |
| L2 本地链路 | 113 项自动化 + 32 场景真实浏览器 E2E + quick_validate + 安全扫描 0 高风险 + 真实材料 9/9 | ✅ 通过 |
| L3 TeleAgent 平台 | 对话自然语言触发、桌面端技能加载、真实大型课件（>50MB）端到端 | ⚠️ **NOT_VERIFIED**（本环境无 TeleAgent 桌面客户端；注册 API 已返回 Register success，人工验收清单见 tests/e2e/E2E_CHECKLIST_V22.md 文末与 docs/PLATFORM_ACCEPTANCE.md，不宣称已通过平台验收） |

详见 `docs/PLATFORM_ACCEPTANCE.md`（平台验收记录与人工清单）。

> AI生成