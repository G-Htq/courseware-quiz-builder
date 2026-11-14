# REVIEW_REPORT - 独立复核报告（隔离上下文代理执行）

> 复核时间：2026-11-13（两轮：v2.1 轮 + v2.2 轮）｜ 复核方式：与开发过程隔离的独立代理，
> 仅依据磁盘实际文件与亲自构造运行的验证（其验证脚本留存于 .temp 下），未采信开发方文档自述。
> 分级：PASS / CONDITIONAL / FAIL / NOT_VERIFIED
> 复核后处置：两轮发现均已落实修复并复验（见各轮“处置”节）。

---

# 第一轮：v2.1 复核

## 原始结论（10 项）

| 项 | 内容 | 结论 |
|---|---|---|
| A | dist ZIP 与注册目录 6 文件 SHA-256 逐字节一致；暂存副本亦一致 | **PASS** |
| B | 代理实测 run_tests.py：64/64 通过 exit 0（5.5s）；抽查 build_gate/path_security 断言真实；全部测试文件恒真断言模式扫描 0 可疑（但发现文档声称 65 与实测 64 不符 → 触发 F 项 FAIL） | PASS（附发现） |
| C | 代理自构造恶意题库（source_quote 改为胡话）实测：strict exit 1 零产物仅留诊断报告；preview 产出（草稿）文件且 MD 含"草稿·未通过完整核验" | **PASS** |
| D | 代理自构造三种攻击 image（绝对路径/http 外链/多级 ../ 穿越）全部 exit 1 拒绝且原因明确；目录内 123 字节真 PNG 引用 exit 0 不误伤 | **PASS** |
| E | 模板源码核验：state.submitted 全局标志 0 次残留；examActive/normalizeState/newAttemptId 存在；交卷入口有 submitted 守卫；answers/results 深拷贝快照；importData 先校验后应用 | **PASS** |
| F | 文档真实性：测试用例数 65 vs 实测 64 不符（"Ran 65"为虚报，build_gate 表写 13 实为 12） | **FAIL**（已修复，见处置） |
| G | Word 合法 zip；正文口径 485 字达标，但含主标题口径 513 字有超限风险；且写有"65 项"数字错 | CONDITIONAL（已修复） |
| H | 参赛材料完整性：README + docs 8 份 + 审计记录全齐备，无缺失 | **PASS** |
| I | 水印全部保留；SKILL.md 有提示注入防护条款；quiz_toolkit.py 当时缺同等条款（仅有代码级转义防护） | CONDITIONAL（已修复） |
| J | L3 平台级验证诚实标注 NOT_VERIFIED 未冒充；但 7 处"65 用例"数字与实测不符 | CONDITIONAL（已修复） |

## 代理总体结论（原文摘要）

> 不建议以"v2.1 正式参赛版"名义直接提交，需先完成两处低成本修复：
> 1. 必改——测试数字虚报（65→64）；
> 2. 建议改——docx 含标题口径超限风险 + quiz_toolkit.py 补指令隔离声明。
> 修复后 F/J 可转 PASS。值得肯定：dist 零偏差、门禁是真实阻断而非摆设、
> 三类路径攻击全部拒绝且不误伤、前端状态机与深拷贝快照/导入先校验后应用
> 在源码中逐一落实、L3 未验证项诚实申报。

## 修复处置（复核后已完成并复验）

| # | 问题 | 修复 | 复验 |
|---|---|---|---|
| 1 | 8 处文档写 65 用例（README/TEST_REPORT/CHANGELOG/ORIGINALITY/SCREENPLAY/COMPETITION_DESCRIPTION/reports/test-results/Word docx），run_tests.py docstring 分项亦误 | 全部改为实测 64（分项 17/5/13/12/11/6） | 复跑 run_tests.py = `Ran 64 tests ... OK / 64/64 通过`（quiz_toolkit.py 修改后回归无影响） |
| 2 | docx 含主标题 513 字超限风险 | 标题缩短为"课件智练技能说明（v2.1）"+迭代句压缩 | 正文（含小标题）494 字，含主标题约 497 字，两种口径均 ≤500 |
| 3 | quiz_toolkit.py 无指令隔离声明条款 | 文件头新增"安全约定"段（不可信数据/指令性文字不执行/图片仅限目录内或 data URL），并同步 v2.1 门禁用法说明 | py_compile 通过；已同步注册目录（哈希 SAME）；64/64 回归通过；quick_validate 通过；ZIP 重建（62084 字节）；已重新注册（Register success） |

修复后状态：A/C/D/E/H 维持 PASS；F/J 的问题点已消除（数字 64 全局一致）；
G/I 的建议项已落实。

---

# 第二轮：v2.2 复核（本轮）

> 复核对象：v2.2 候选（113 用例版本）。代理独立执行十项检查（K1-K10），
> 自构造攻击题库亲测，不采信开发文档；容器内无桌面客户端，平台项按诚实原则判。

## 原始结论（10 项）

| 项 | 内容 | 结论 |
|---|---|---|
| K1 | 代理亲跑 run_tests.py：**113/113 通过 exit 0**，抽查 v2.2 新套件断言真实非恒真；5.5s 内完成 | **PASS** |
| K2 | 逐题门禁绕过：代理自构造 3 组混合证据题库（Q2 删字段/Q2 改 null/Q2 只留 quote），strict 全部 exit 1 且零产物，报 `B-EVIDENCE-REQUIRED@Q2` | **PASS** |
| K3 | 非法 JSON 矩阵：顶层[]/null/questions 混类型/损坏 JSON 全部结构化报错无 Traceback，Schema 失败仍落盘报告 | **PASS** |
| K4 | 反伪造：source_ref=“第999页”被 verify exit 1 + B-REF-CONFLICT；篡改材料哈希触发 B-SOURCE-HASH；canonical 引用出现在产物中 | **PASS** |
| K5 | 原子化：注入渲染期异常 → 零半成品、旧正式产物保留并在输出整版提示；重复构建可恢复 | **PASS** |
| K6 | 三维契约与退出码：blocked⟺BLOCKED 恒等、无 manifest 时 layer_b=UNAVAILABLE 且 exit 1、checks[] 六项执行状态真实 | **PASS** |
| K7 | 交付一致性：dist ZIP 6 文件 = 注册目录 = 源码暂存副本，三方 SHA-256 逐字节一致 | **PASS** |
| K8 | 真实材料证据链：对 quiz-real.json 8 题逐条回 manifest 核验，8/8 quote 均为对应片段原文子串；9/9 材料解析 ok | **PASS** |
| K9 | 文档口径：TEST_REPORT.md 仍为 v2.1 口径（64 用例）、CHANGELOG 缺 v2.2 段、REVIEW_REPORT 为 v2.1 轮；quiz_toolkit.py 头部署 v2.1；quiz-format.md 写 A-SCHEMA-001~003 而实现仅 001/002（003 为死键）；run_tests.py docstring 写 111 实为 113（security 写 8 实为 9） | **CONDITIONAL** |
| K10 | L3 诚实申报：平台项 NOT_VERIFIED 未冒充；注册 API 有 Register success 但与客户端加载分离申报 | **PASS** |

## 代理总体结论（原文摘要）

> 代码与测试层面具备提交条件：113 用例可复现、三类门禁绕过全部被拦、原子化与旧产物
> 保留行为符合用户 v2.2 指令、真实材料 8/8 引用可回溯。唯一阻塞项是文档口径未随代码
> 更新（K9），属低成本修复；修复并重走发布链后可转 PASS。

## 修复处置（复核后已完成并复验）

| # | 问题 | 修复 | 复验 |
|---|---|---|---|
| 1 | TEST_REPORT.md 仍 v2.1 口径 | 全文重写为 v2.2：113 用例明细（10 套件）、五类缺陷反例矩阵、32 场景 E2E、真实材料摘要、L3 保持 NOT_VERIFIED | 数字与实测输出逐项核对一致 |
| 2 | CHANGELOG 缺 v2.2 段 | 顶部新增 v2.2 完整段（扣除/修复/测试/真实材料/发布链/复核）；原创性与文件清单同步 113/32 | 通读无 v2.1 残留失实数字 |
| 3 | REVIEW_REPORT 为 v2.1 轮 | 追加本轮 v2.2 复核（本节） | — |
| 4 | quiz_toolkit.py 头部署 v2.1 | docstring 改为 v2.2；删除 `SUGGESTED_FIX["A-SCHEMA-003"]` 死键 | py_compile 通过；113/113 回归通过 |
| 5 | quiz-format.md 编号口径 | 改为“A-SCHEMA-001/002；questions 内非对象项报‘必须是对象’按 A-STRUCT 归类”；baseline 审计文档同口径注记 | 与实现一致 |
| 6 | run_tests.py docstring 数字 | 111→113；security 8→9；source_integrity 11→12；标题改 v2.2 | 与 `Ran 113 tests` 输出一致 |
| 7 | 修复后重新发布 | 6 文件同步注册目录（哈希 SAME）→ quick_validate 通过 → Register success → ZIP 重建（6 文件/72119 字节） | 全部成功 |

**第二轮最终状态**：K1-K8、K10 维持 PASS；K9 的文档口径问题已全部消除。
L3 平台级验收仍为 NOT_VERIFIED（无桌面客户端，人工清单见 PLATFORM_ACCEPTANCE.md）。

> AI生成
