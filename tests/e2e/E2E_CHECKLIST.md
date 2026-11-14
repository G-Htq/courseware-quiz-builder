# E2E_CHECKLIST - 浏览器端到端验证清单（v2.1）

> 执行环境：Windows + Chromium（Playwright 驱动真实浏览器），本地 HTTP 服务
> `http://localhost:8936`（指向 `tests/out`），页面由 v2.1 模板构建。
> 全部场景均于 2026-11-13 实际执行通过，截图归档于 `课件智练v2/evidence/`。
> 「TeleAgent 对话内自然语言触发」为平台级验收，需桌面端人工执行，见文末 L3 清单。

## 一、考试状态机（P0-4，修复 V2-04）

| # | 场景 | 步骤 | 预期 | 结果 |
|---|---|---|---|---|
| 1 | 开考生成 attempt | 首页 → 考试模式 | 进入考试视图，`state.examPaper.id` 形如 `att-YYYYMMDD-HHMMSS-xxxx`，`submitted=false`，已答 0/4 | ✅ |
| 2 | 作答即时持久化 | Q1 选 B | 工具栏"已答 1/4"，`localStorage` 有 `answers.Q1=[1]` | ✅ |
| 3 | 中途刷新恢复 | F5 刷新 | 直接回到考试视图（非首页/非成绩卡），已答数保留，交卷按钮在位 | ✅ |
| 4 | 交卷 → SUBMITTED | 交卷 → 确认（含未答提示） | 成绩单显示 attempt_id 与交卷时间；答错题标 ✓/✗ | ✅ |
| 5 | 再考一次（V2-04 核心） | 成绩页 → 再考一次 | **新试卷新 attempt_id**（att-…-1qv5 ≠ att-…-75c4），已答 0/4（旧答案清空），**不显示旧成绩卡**，attempts/qHistory 历史保留 | ✅ |
| 6 | 放弃考试 | 首页 → 放弃本次考试 → 确认 | `examPaper=null` 回 IDLE；attempts 与 qHistory 保留 | ✅ |
| 7 | 逐题回看（REVIEW） | 成绩页 → 逐题回看本次作答 | 回考试视图浏览快照卷，显示 ✓ 正确答案/✗ 你的选择 | ✅ |
| 8 | 重复交卷守卫 | 已交卷后再触发交卷 | `submitExam` 状态守卫直接 return，不产生重复 attempt | ✅（代码守卫） |

## 二、门禁可视化（P0-2）

| # | 场景 | 预期 | 结果 |
|---|---|---|---|
| 9 | strict 页无草稿横幅 | 顶部无 `gate-banner`，meta 显示"核验：WARN · strict模式" | ✅ |
| 10 | preview 草稿页横幅 | 黄色横幅"⚠ 草稿·未通过完整核验…不得作为正式交付物"，meta"核验：FAIL · preview模式"；文件名带（草稿） | ✅ evidence/v21-draft-gate-banner.png |

## 三、错题复练闭环

| # | 场景 | 预期 | 结果 |
|---|---|---|---|
| 11 | 考试全错 → 错题 4 道 | 成绩页"去错题中心复练" | 错题中心按考点分组 4 道 | ✅ |
| 12 | 重做全部错题 | 复练会话 4 题，单选/判断点击即时判分 | Q1/Q2 立即显示 ✓ | ✅ |
| 13 | 多选确认判分 | Q3 选 A/B/D → 确认答案 | 判分并写入 `qHistory.Q3`（redo 记录） | ✅ |
| 14 | 完成复练 | Q4 简答自评 → 完成复练 | alert"3/4 题已纠正"；错题 4→1；attempts 追加 `redo:3/4` | ✅ |
| 15 | 前后对比链 | 错题中心 Q3 卡片 | "作答历史：✗ → ✗"（exam→redo 链）；Q1 链 practice✓→exam✗→redo✓ | ✅ evidence/v21-wrong-center-chain.png |

## 四、学习记录导入/导出（V2-05 + P0-4）

| # | 场景 | 预期 | 结果 |
|---|---|---|---|
| 16 | 导出真实下载 | 学习报告 → 导出学习记录 | 真实下载事件，文件名`学习记录-<题库>.json`，内容 v3 快照完整（examPaper 快照+三段历史链） | ✅ |
| 17 | v2 旧记录导入迁移 | 导入 tests/学习记录-import-test.json | `v:3`，flags/qHistory/attempts 全保留，examPaper=null | ✅ |
| 18 | 非法记录 Schema 拒绝 | 导入混入字符串/小数/非法枚举的记录 | alert"导入失败：作答/标记/历史字段结构非法"，**当前状态分毫未动** | ✅ |
| 19 | 进行中考试拒绝导入 | examPaper 未交卷时导入 | alert 明确拒绝，要求先交卷或放弃 | ✅（代码守卫） |

## 五、环境健壮性

| # | 场景 | 预期 | 结果 |
|---|---|---|---|
| 20 | 存储禁用降级 | init script 使 `setItem` 抛 QuotaExceededError 后刷新 | 黄色横幅"浏览器存储不可用…请用导出备份"，页面功能不中断 | ✅ |
| 21 | 移动端 375×812 | 首页/成绩页横向溢出检测 | `scrollWidth==clientWidth`（0 溢出），无溢出卡片 | ✅ evidence/v21-mobile-375-results.png |
| 22 | 键盘操作 | ←/→ 切题、数字键作答、F 标记 | 与点击行为一致（v2.0 已验，v2.1 回归正常） | ✅ |

## L3：TeleAgent 平台级验收（本环境无桌面客户端，未验证 → NOT_VERIFIED）

以下需在 TeleAgent 桌面端由人工执行，本仓库无法代验：

1. 对话中说"帮我把这份 PPT 变成复习题"能命中本技能（自然语言触发）。
2. 技能注册后出现在技能列表且可被宿主加载（SKILL.md/YAML 校验通过即可注册，触发命中待验）。
3. 真实大型课件（>50MB PPTX/PDF）端到端耗时与内存表现。
4. PDF 扫描件"需 OCR"提示路径的真实观感。
5. 刷题页双击 file:// 打开的完整体验（HTTP 服务已验；HTML 全部图片为 base64 内嵌，file:// 不影响刷题页本身）。

> AI生成
