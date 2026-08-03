# AI 智能问题分析平台

## 项目定位

AI 智能问题分析平台通过 Agent Workflow 结合知识检索与工具调用能力，实现从问题理解、任务拆解、信息检索、原因分析到解决方案生成和知识沉淀的完整闭环。

当前以 Python 代码分析作为验证场景，未来可扩展到日志诊断、技术支持和商业化问题分析。

## 当前基线

- 当前版本：Code Agent RAG Baseline
- 主干分支：`master`
- 当前入口：`app.py`
- 核心能力：Python AST、函数级 Chunk、Embedding、FAISS 检索、LLM 回答
- 技术约束：保留 Python、FAISS、Embedding 和 AST；当前阶段不引入 LangGraph、AutoGen 或 CrewAI

## 开发流程

每个 Phase 必须独立执行以下流程：

```text
Phase 开发
→ Code Review
→ 修复 Review 问题
→ Test 验证
→ Git 提交
→ 用户审核并决定是否合并
→ 下一 Phase
```

约束：

- 一个 Phase 对应一个 Codex Chat 和一个 Git Branch。
- 每个 Phase 分支从最新的 `master` 创建。
- 上一 Phase 未合并到 `master` 前，不进入下一 Phase。
- 每次只实现和更新一个 Phase，不提前实现后续 Phase。
- Codex 默认只完成 Phase 分支提交；合并和推送必须由用户决定或明确授权。
- Phase 状态按 `Todo → In Progress → Review → Testing → Done` 更新。
- `Done` 表示开发、Review、测试和提交均已完成，不代表已经合并到 `master`。

## Phase 1：代码重构和模块解耦

- 状态：Done
- 分支：`phase1-refactor`
- Codex Chat：Phase 1 专用 Chat
- 前置条件：无

### 目标

- 保持现有代码分析功能不变。
- 将入口、配置、LLM、RAG、AST 和分析流程拆分为职责清晰的模块。
- `main.py` 只负责程序入口和用户交互。
- 建立可复现的测试基线，为后续 Workflow 改造提供保障。

### 目标结构

```text
Code Agent/
├── main.py
├── core/
│   ├── config.py
│   └── llm.py
├── rag/
│   ├── embedding.py
│   ├── vector_store.py
│   └── retriever.py
├── parser/
│   └── ast_parser.py
├── workflow/
│   └── analyzer.py
├── tools/
├── tests/
├── eval/
└── data/
```

### 验收标准

- [x] `main.py` 只负责流程入口和交互。
- [x] RAG、Embedding、FAISS Vector Store 和 Retriever 职责独立。
- [x] AST Parser 独立。
- [x] LLM 配置和调用独立。
- [x] 当前“检索代码并由 LLM 回答”的功能保持不变。
- [x] 原有评测入口适配新模块结构。
- [x] Code Review 通过。
- [x] Test 验证通过。

### 测试结果

- 单元与 Mock 集成测试：17 项通过，0 项失败。
- 依赖检查：`pip check` 通过。
- 编译检查：核心模块、兼容模块、评测入口和程序入口通过。
- 真实外部 API 链路：未执行；当前环境未提供可用于验证的 API 配置和固定样例仓库。

### Commits

- `166c9fe` `refactor(code-agent): separate analysis modules`
---

## Phase 2：引入 Agent Workflow

- 状态：Done
- 分支：`phase2-workflow`
- Codex Chat：Phase 2 专用 Chat
- 前置条件：Phase 1 已完成并合并到 `master`

### 目标

- 新增 `workflow/orchestrator.py`。
- 建立统一 Workflow 入口、执行上下文和结果结构。
- 由 Orchestrator 调度 Retriever、分析流程和 LLM。
- 所有问题分析流程统一通过 Workflow 调用。

### 目标流程

```text
User Question
→ Orchestrator
→ Retriever
→ Analyzer / LLM
→ Analysis Result
```

### 验收标准

- [x] 代码中存在明确的 Workflow 入口。
- [x] `main.py` 不直接调用 Retriever 或 LLM。
- [x] Workflow 各步骤输入、输出和错误可以追踪。
- [x] 当前代码分析能力保持兼容。
- [x] Code Review 通过。
- [x] Test 验证通过。

### 测试结果

- 单元与 Mock 集成测试：24 项通过，0 项失败。
- 依赖检查：`pip check` 通过。
- 编译检查：核心模块、兼容模块、评测入口、测试和程序入口通过。
- 格式检查：`git diff --check` 通过。
- 真实外部 API 链路：未执行；核心自动化测试使用 Mock，不依赖外部 API。

### Commits

- `7d0ec33` `feat(code-agent): add analysis workflow orchestrator`

---

## Phase 3：增加 Planner Agent

- 状态：Todo
- 分支：`phase3-planner`
- Codex Chat：待创建
- 前置条件：Phase 2 已完成并合并到 `master`

### 目标

- 新增 `agents/planner.py`。
- 将用户问题拆解为结构化、可校验的任务计划。
- Planner 只负责任务规划，不执行检索、工具调用或原因分析。
- Orchestrator 能够接收并按顺序调度任务计划。

### 目标输出示例

```json
{
  "goal": "分析 login 函数异常原因",
  "tasks": [
    {
      "id": "task_1",
      "type": "code_search",
      "description": "查找 login 函数"
    },
    {
      "id": "task_2",
      "type": "dependency_analysis",
      "description": "分析调用和依赖关系"
    }
  ]
}
```

### 验收标准

- [ ] Planner 与任务执行职责分离。
- [ ] Planner 输出具有稳定、明确的数据结构。
- [ ] 无效任务计划能够被校验和拒绝。
- [ ] Orchestrator 能够消费任务计划。
- [ ] Code Review 通过。
- [ ] Test 验证通过。

### 测试结果

待执行。

### Commits

待提交。

---

## Phase 4：增加 Tool Calling 能力

- 状态：Todo
- 分支：`phase4-tool-calling`
- Codex Chat：待创建
- 前置条件：Phase 3 已完成并合并到 `master`

### 目标

- 建立统一 Tool 协议和 Tool Registry。
- 新增 AST Tool、Code Search Tool 和 Dependency Tool。
- 由 Orchestrator 根据任务计划选择和调用工具。
- 统一工具输入、输出和错误结构。

### 目标结构

```text
tools/
├── base.py
├── registry.py
├── ast_tool.py
├── code_search_tool.py
└── dependency_tool.py
```

### 工具能力

- AST Tool：函数解析、类关系分析、调用关系分析。
- Code Search Tool：文件搜索、文本搜索、函数定位。
- Dependency Tool：导入关系、函数依赖和调用依赖分析。

### 验收标准

- [ ] 所有工具实现统一接口。
- [ ] Agent 不直接依赖具体工具实现。
- [ ] Planner 任务类型能够映射到注册工具。
- [ ] 工具失败不会无信息地中断整个 Workflow。
- [ ] 每个工具具有独立测试。
- [ ] Code Review 通过。
- [ ] Test 验证通过。

### 测试结果

待执行。

### Commits

待提交。

---

## Phase 5：领域扩展能力设计与验证

- 状态：Todo
- 分支：`phase5-domain-extension`
- Codex Chat：待创建
- 前置条件：Phase 4 已完成并合并到 `master`

### 目标

- 将平台统一抽象为 `Problem + Knowledge Source + Tools + Workflow`。
- 证明 Orchestrator 和核心 Workflow 不依赖代码分析领域。
- 通过代码分析、测试问题分析和商业化问题分析三个场景验证扩展边界。

### 验证场景

1. 代码分析：代码问题 + 代码库 + AST/代码搜索工具。
2. 测试问题分析：Crash Log + Bug 库 + 日志解析工具。
3. 商业化 SE 问题分析：广告异常 + 历史 Case/产品文档/SDK 文档 + 配置分析工具。

### 验收标准

- [ ] Problem、Knowledge Source、Tool Set 和 Analysis Result 具有统一接口。
- [ ] 新领域可以通过注册知识源和工具接入。
- [ ] 核心 Orchestrator 不需要为每个领域重写。
- [ ] 三个场景均有固定样例和验证结果。
- [ ] 最终输出包含证据、原因、建议和后续验证步骤。
- [ ] Code Review 通过。
- [ ] Test 验证通过。

### 测试结果

待执行。

### Commits

待提交。
