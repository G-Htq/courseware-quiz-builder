# test-results.md - v2.2 自动化测试结果报告

> 生成时间：2026-11-13（本报告数字为真实运行结果，可复现）
> 运行方式：`python 课件智练v2/tests/run_tests.py`（Python 3.12.13，核心仅标准库）
> 测试事实源：`课件智练v2/skill-src/courseware-quiz-builder/`（与注册目录哈希一致）

## 汇总

| 套件 | 用例数 | 通过 | 失败 | 说明 |
|---|---|---|---|---|
| test_extract_text.py（解析+降级） | 17 | 17 | 0 | pptx 属性节点/演示顺序/表格/水印过滤；docx 段落/表格/隐藏文本/图片；md 分段；manifest 结构；6 类降级 |
| test_office_edge_cases.py（边界隔离） | 5 | 5 | 0 | 6 类边界文件明确报错无 Traceback；混合批次 2 坏+2 好互不破坏；全坏仍写 manifest |
| test_quiz_validation.py（层A/B） | 13 | 13 | 0 | 证据定位正反例；图片魔数/穿越/矛盾/旧格式/答案越界 |
| test_build_gate.py（门禁，v2.2 修订） | 12 | 12 | 0 | strict 通过/阻断×4/旧产物保留+警告；preview 草稿；报告契约；C-SEM-003 |
| test_path_security.py（路径安全） | 11 | 11 | 0 | ../ 与 ..\ 穿越、绝对路径、协议、svg、伪装魔数拒绝；合法引用放行 |
| test_skill_structure.py（静态规范） | 6 | 6 | 0 | frontmatter；门禁文档一致；文件结构；模板占位符；前端静态特征；脚本编译 |
| test_schema_v22.py（v2.2 新增） | 16 | 16 | 0 | 非法 JSON 全矩阵（顶层[]/null/questions 混类型/损坏/超大/非法 data URL）+ 结构化报告 |
| test_source_integrity_v22.py（v2.2 新增） | 12 | 12 | 0 | 伪造 source_ref/哈希三态/篡改阻断/短证据 THIN·UNIQUE/canonical 进产物 |
| test_release_gate_v22.py（v2.2 新增） | 12 | 12 | 0 | 混合证据逐题阻断/preview 草稿/NOT_VERIFIED 阻断/渲染失败零半成品/退出码矩阵/三维不矛盾/stdout 报告/input_digest |
| test_security_v22.py（v2.2 新增） | 9 | 9 | 0 | 注入防护/无原始 script/前端白名单/材料指令仅作数据/SKILL 条款 |
| **合计** | **113** | **113** | **0** | unittest 全绿（实测输出 `Ran 113 tests ... OK`；独立复核代理复跑一致） |

分项以 unittest 实际收集的测试方法为准（unittest 按方法收集，无参数化扩展）。

## 与 v2.1 基线对比

| 指标 | v2.1 | v2.2 |
|---|---|---|
| 自动化用例 | 64 | **113** |
| 逐题证据缺失被整体逃逸（V22-A） | Q2 删证仍 exit 0 产出 | 逐题阻断 B-EVIDENCE-REQUIRED |
| 非法 JSON 崩溃（V22-B） | 顶层[]/混类型 AttributeError | 统一 Schema 入口结构化报错 |
| 展示引用可伪造（V22-C） | "第999页"仍 PASS | 交叉核对+canonical，B-REF-CONFLICT |
| 短证据无质量维度（V22-D） | 2 字引用"通过" | THIN/UNIQUE WARN 区分 |
| 状态/退出码矛盾（V22-E） | overall=WARN+blocked=true；无 manifest exit 0 | 三维契约+退出码矩阵 |
| 构建原子性 | 失败路径可能留半成品 | 临时目录自检后原子提交；旧产物保留+警告 |
| 材料完整性 | 仅清单内一致性 | SHA-256 重算（EXECUTED/PASS/UNAVAILABLE 三态） |
| 真实材料 | 未评测 | 9 份/2845 片段 9/9 解析 + 8 题证据链实测 |

## 关键回归点（防"改预期凑全绿"说明）

- v2.1 的 `test_strict_cleans_stale_products`（断言阻断后清理旧产物）按 v2.2 用户指令
  改为 `test_strict_blocked_preserves_stale_products`（断言旧产物保留 + 整版警告）。
- 原 v2.1 断言（解析/降级/证据定位/魔数/门禁矩阵/路径安全）全部保留并通过；
  v2.2 新套件断言均基于真实子进程输出与产物文件检查，无恒真断言。

## 浏览器 E2E（真实浏览器，非本套件）

两轮共 32 场景全部通过：v2.1 轮 22（E2E_CHECKLIST.md）+ v2.2 轮 10 组
（E2E_CHECKLIST_V22.md）。覆盖考试状态机/门禁可视化/错题复练闭环/导入导出/
草稿横幅 DRAFT_ONLY/存储降级/375px/键盘，截图见 `evidence/`。

## 真实材料评测

9 份真实备考材料（约 5.0MB、2845 片段、95,654 字符）解析 9/9 成功；8 题证据链
verify 8/8 精确定位、材料哈希 PASS、strict build WARN/READY；产物浏览器冒烟通过。
详见 `docs/REAL_MATERIAL_EVAL.md`。

## 平台级验收状态（诚实申报）

| 层级 | 状态 |
|---|---|
| L1 代码级（静态规范/编译） | ✅ 通过 |
| L2 本地链路（CLI 全链路 + 浏览器 E2E + 发布链） | ✅ 通过 |
| L3 TeleAgent 平台（自然语言触发/桌面端加载/真实大型课件） | ⚠️ NOT_VERIFIED（本环境无桌面客户端，人工清单见 docs/PLATFORM_ACCEPTANCE.md） |

> AI生成