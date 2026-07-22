# Code Agent 开发规则

本文件适用于 `Code Agent/` 目录及其全部子目录。所有参与本项目开发的 Codex Chat 和 Agent 都必须遵守以下规则。

## 1. 项目范围

- Git 仓库根目录是 `Personal-AI/`，本项目目录是 `Personal-AI/Code Agent/`。
- 同一仓库还包含 `Travel Agent/`；未经用户明确授权，不得读取后修改、暂存或提交其他项目文件。
- 仓库根级文件只有在用户明确授权时才可以修改或提交。
- 已存在的用户改动和无关未提交状态必须保留，不得擅自恢复、覆盖或删除。

## 2. Phase、Chat 与分支

- 主干分支固定为 `master`。
- 一个 Phase 对应一个 Codex Chat 和一个 Git Branch。
- 分支映射：
  - Phase 1：`phase1-refactor`
  - Phase 2：`phase2-workflow`
  - Phase 3：`phase3-planner`
  - Phase 4：`phase4-tool-calling`
  - Phase 5：`phase5-domain-extension`
- 每个 Phase 分支必须从包含上一 Phase 合并结果的最新 `master` 创建。
- 上一 Phase 未完成并合并到 `master` 前，不得进入下一 Phase。
- 当前规划 Chat 不承担 Phase 开发；每个 Phase 必须在对应的新 Chat 中执行。

## 3. Phase 范围控制

- 每次只开发一个 Phase。
- 不得为了“顺便完善”而实现后续 Phase 的功能。
- 发现需求会扩大当前 Phase 范围时，必须停止并向用户说明。
- 业务行为调整必须符合 `PROJECT.md` 中当前 Phase 的目标和验收标准。
- 用户未明确授权开始开发前，不得修改业务代码。

## 4. 固定开发门禁

每个 Phase 必须按以下顺序执行，禁止跳步：

```text
Phase 开发
→ Code Review
→ 修复 Review 问题
→ Test 验证
→ Git 提交
→ 用户审核并决定是否合并
→ 下一 Phase
```

- Review 未通过时，必须在同一 Phase Chat 和分支修复并重新 Review。
- 测试未通过时，Phase 不得标记为 `Done`，不得提交完成状态。
- Codex 默认只完成 Phase 分支提交，不默认合并或推送。
- 合并到 `master` 和推送远端必须由用户亲自执行，或由用户明确授权 Codex 执行。

## 5. Code Review 门禁

Review 至少检查：

- 修改是否严格属于当前 Phase。
- 模块职责是否清晰，是否出现循环依赖或不合理的反向依赖。
- 是否保持当前 Phase 要求的向后兼容。
- 配置、密钥、日志和异常信息是否安全。
- 错误处理和边界条件是否明确。
- 重要逻辑是否具备测试。
- 是否意外修改仓库根目录、`Travel Agent/` 或其他无关文件。
- 是否提前实现了后续 Phase。

Review 结论、发现的问题及修复情况应在提交前向用户说明，并记录到当前 Phase 的工作结果中。

## 6. Test 门禁

每个 Phase 至少考虑三层验证：

1. 单元测试：验证当前 Phase 新增或调整的独立模块。
2. 集成测试：使用 Mock Embedding、Mock LLM 或固定测试数据验证完整链路。
3. 真实链路验证：仅在环境、API 和用户授权允许时执行。

要求：

- 核心自动化测试不得以真实外部 API 可用为通过前提。
- 测试必须覆盖正常流程、空输入、无结果和关键异常路径。
- 测试命令、通过数量、失败项和未验证项必须如实报告。
- 不得把历史评测结果当作当前代码的测试结果。

## 7. Git 提交安全门禁

每次提交前必须执行并核对：

1. 从整个 Git 仓库范围检查状态：
   `git status --short --untracked-files=all`
2. 确认当前分支与当前 Phase 的约定分支一致。
3. 检查未暂存变更和格式问题：
   `git diff --check`
4. 精确暂存当前 Phase 文件。
5. 检查暂存文件清单：
   `git diff --cached --name-status`
6. 检查暂存内容和格式问题：
   `git diff --cached --check`
7. 确认暂存区不包含无关文件后才能提交。
8. 提交后再次检查完整仓库状态、最新提交和分支关系。

强制规则：

- 禁止使用 `git add .`。
- 禁止使用 `git add -A`。
- 必须使用明确、精确的路径暂存文件。
- 默认只允许暂存 `Code Agent/` 内属于当前 Phase 的文件。
- 仓库根级文件必须有用户明确授权。
- 出现 `Travel Agent/`、未知文件或其他无关路径时，必须停止提交并向用户报告。
- 禁止使用 `git reset --hard`、`git checkout --` 等破坏性恢复命令，除非用户明确指定目标并授权。

## 8. Commit 与状态记录

- Commit 信息应清晰描述单一意图，优先使用 Conventional Commits。
- 每个 Phase 原则上至少包含：
  1. 实现与测试提交。
  2. 更新 `PROJECT.md` 的状态记录提交。
- `PROJECT.md` 记录实现提交的 Commit Hash；不记录状态文件自身最终 Hash，避免循环引用。
- Phase 状态按 `Todo → In Progress → Review → Testing → Done` 更新。
- 只有开发、Review、测试和分支提交全部完成后，Phase 才能标记为 `Done`。
- `Done` 不等于已合并；是否合并以 Git 分支状态和用户决定为准。

## 9. 文档维护

- `PROJECT.md` 是项目目标、Phase 状态、验收结果和 Commit 记录的唯一项目进度来源。
- 五个 Phase 保持在同一个 `PROJECT.md` 中。
- 每次只更新当前正在开发的 Phase，不改写其他 Phase 的状态和验收记录。
- 架构或流程规则发生变化时，应先与用户确认，再更新文档。
