# ORIGINALITY - 原创性说明

## 声明

参赛作品「点课成题-课件刷题工坊（courseware-quiz-builder）」的以下全部内容，均为参赛者本人在
本次赛事周期内原创开发，未复制、未抄改任何现有技能、开源项目或商业产品代码：

- `SKILL.md`（技能主文件：触发定义、九步工作流、异常处理表、禁止行为条款）
- `scripts/extract_text.py`（OOXML/PDF/文本材料解析器：真 XML 解析、manifest 证据锚点、
  资源上限防护、水印过滤、边界文件隔离）
- `scripts/quiz_toolkit.py`（三层验证引擎、强制门禁、矛盾检测、路径安全、渲染器）
- `assets/quiz-template.html`（单文件离线刷题页：考试状态机、错题闭环、学习报告、
  导入 Schema 校验、草稿横幅）
- `references/quiz-format.md`、`references/generation-workflow.md`（数据契约与工作流规范）
- 测试夹具生成脚本与 113 项自动化测试（v2.2）、两轮共 32 场景 E2E 清单、全部参赛文档

## 素材合规

- 全部演示与测试材料为**合成数据**（标准库程序化生成的 pptx/docx/md/图片），
  不含真实用户隐私，不使用受版权保护的商业题库内容
- 备考题库实战数据来自参赛者本人有权处理的个人备考材料
- 技能不收录 svg、不抓取外部资源、脚本无网络行为

## AI 辅助与水印说明

- 开发过程由参赛者主导架构设计、验收标准与测试判定；AI 工具参与代码起草与文档撰写
- 平台在生成文件中注入 AIGC 水印（如文档尾部"AI生成"标识），符合大赛 AI 应用创新
  定位，已按平台要求保留
- 产出题目内容由 AI 基于用户提供的材料生成，刷题页与题库均明确标注生成属性与
  核验状态（已核验/需人工复核/未核验），不冒充人工命题

## 第三方依赖说明

- 核心功能（解析/质检/门禁/渲染）**仅使用 Python 标准库**，不内嵌、不复制任何
  第三方代码，不引入任何前端外部资源（刷题页单文件零外链）
- PDF 文本/图片提取为可选能力：依赖 `pdfplumber` 或 `pypdf`（均为公开开源库，
  经 pip 安装，未修改其源码）；缺失时脚本如实提示安装命令，不虚构提取结果。
  本次真实材料评测中 pypdf 装于临时目录 `.temp/pylibs-v22`，未污染系统环境
- 测试与构建工具链（Playwright Chromium、Node.js 仅用于模板 JS 语法检查）
  不随交付物分发

## 可验证性

- 迭代过程与修复依据见 `docs/CHANGELOG.md`、`docs/audit/`（v2.1/v2.2 基线审计）
- 全部测试可一键复现：`python tests/run_tests.py`（**113 用例**）；
  E2E 步骤与截图见 `tests/e2e/E2E_CHECKLIST.md`、`tests/e2e/E2E_CHECKLIST_V22.md`、`evidence/`
- 真实材料评测可回溯：明细与产物见 `docs/REAL_MATERIAL_EVAL.md`
- 技能包与注册目录内容哈希一致（发布流程校验）

> AI生成
