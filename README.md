# AI 智能问题分析平台

这是一个基于 Python 的问题分析平台。它将问题规划、知识检索、工具调用和 LLM 分析组合为可追踪的 Workflow；当前以代码分析为主，并验证了测试故障和商业化 SE 问题等扩展场景。

## 能力概览

- Python AST 解析、函数级切分、Embedding 与 FAISS 检索。
- 统一 Workflow：问题规划、检索、分析、工具调用和回答生成。
- 工具注册机制：AST、代码搜索、依赖分析、日志解析和配置分析工具。
- 领域扩展机制：通过注册 `Problem`、`KnowledgeSource` 和 `ToolSet` 接入新领域。
- 统一分析结果：包含证据、原因、建议和后续验证步骤。

## 项目结构

```text
Personal-AI/
├── main.py                 # 命令行入口
├── core/                   # 配置与 LLM 客户端
├── agents/                 # Planner
├── rag/                    # Embedding、向量库与检索器
├── parser/                 # Python AST 解析器
├── tools/                  # 工具协议、注册表与领域工具
├── workflow/               # 代码分析与领域无关工作流
├── domains/                # 领域契约、注册表与固定场景
├── tests/                  # 单元与 Mock 集成测试
├── eval/                   # 评测入口与样例问题
└── data/repo/              # 待分析的 Python 代码仓库
```

## 快速开始

要求：Python 3.11+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中配置自己的 `OPENAI_API_KEY`，并将待分析的 Python 代码放入 `data/repo/`；随后运行：

```bash
python main.py
```

可通过 `REPO_PATH` 指向其他本地代码目录；Embedding、LLM 模型和可选的 API Base URL 也可在 `.env` 中配置。

## 测试

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

自动化测试使用 Mock LLM，不要求真实外部 API。当前覆盖代码分析、测试故障和商业化 SE 三个固定领域场景，以及空输入、无检索结果和关键异常路径。

## 扩展领域

新领域只需向 `DomainRegistry` 注册 `DomainDefinition`，提供知识源、工具集、提示构建器和结果解析器；领域无关的 `DomainOrchestrator` 会执行相同的检索、工具、生成和结构化结果流程。

内置验证场景见 `domains/scenarios.py`：

1. 代码分析：代码问题、代码知识和 AST/依赖工具。
2. 测试故障分析：Crash Log、Bug 知识和日志解析工具。
3. 商业化 SE 问题分析：产品文档、历史 Case 和配置分析工具。

## 安全与隐私

- 不要提交 `.env`、真实 API Key、访问令牌、密码、私有证书、客户数据或生产日志。
- `.env` 已被 Git 忽略；`.env.example` 只包含无效占位符和示例配置。
- 提交前请执行敏感信息检查，并确认待提交文件仅包含可公开的代码、文档和脱敏测试样例。
