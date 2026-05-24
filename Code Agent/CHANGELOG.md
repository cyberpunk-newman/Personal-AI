# Code Agent 项目文档

## 项目概述

Code Agent 是一个基于 RAG（检索增强生成）的代码分析工具，可以对代码仓库建立索引并回答用户关于代码的问题。

## 项目结构

```
Code Agent/
├── app.py                 # 主入口，CLI 交互界面
├── config.py              # API 配置（OpenAI）
├── requirements.txt       # 项目依赖
├── CHANGELOG.md          # 修改历史
├── .env.example          # 环境变量示例
├── .gitignore            # 忽略敏感文件和本地环境
├── agent/
│   ├── ast_parser.py     # 代码解析模块（AST）
│   ├── rag.py            # RAG 核心（构建索引）
│   ├── retriever.py      # 检索模块
│   └── llm.py            # LLM 调用封装
├── data/
│   └── repo/             # 测试代码仓库目录
└── index/                # 向量索引存储目录
```

## 模块说明

### 1. app.py (主入口)
- 提供 CLI 交互界面
- 循环接收用户输入问题
- 调用 RAG 系统回答问题

### 2. agent/ast_parser.py (代码解析)
- 使用 Python 内置 `ast` 模块解析代码
- 提取函数定义信息（函数名、源代码）
- 依赖：Python 标准库 `ast`

### 3. agent/rag.py (RAG 核心)
- 遍历代码仓库中的 Python 文件
- 调用 `extract_functions` 提取函数
- 使用 OpenAI Embedding 生成向量
- 使用 FAISS 建立向量索引
- 对缺失目录、空目录、无函数等基础异常给出清晰错误
- 依赖：`faiss-cpu`, `numpy`, `openai`

### 4. agent/retriever.py (检索模块)
- 接收用户查询
- 生成查询向量
- 在 FAISS 索引中检索最相似的 k 个结果
- 显式接收当前索引对应的 docs，避免依赖全局状态
- 依赖：`numpy`

### 5. agent/llm.py (LLM 封装)
- 调用 OpenAI GPT-4o-mini 生成回答
- 使用 `config.py` 中的 OpenAI 配置
- 依赖：`openai`

### 6. config.py (配置)
- 使用 `python-dotenv` 读取本地 `.env`
- 配置 OpenAI API Key、base URL、Embedding 模型、LLM 模型和待索引仓库路径
- 未设置 `OPENAI_API_KEY` 时给出清晰错误

## 环境要求

- Python 3.11
- 依赖包（见 requirements.txt）

## 依赖包列表

```
openai
faiss-cpu
numpy
python-dotenv
```

---

## 修改历史 (Changelog)

### 2026-05-02

#### v1.0 - 初始版本
- 创建项目结构
- 完成各模块的基础框架

#### 修改记录

| 日期 | 文件 | 修改内容 | 原因 |
|------|------|----------|------|
| 2026-05-02 | `agent/ast_parser.py` | 替换 `tree_sitter_languages` 为 Python 内置 `ast` 模块 | `get_language()` 函数参数不兼容，报错 `TypeError: __init__() takes exactly 1 argument (2 given)` |
| 2026-05-02 | `agent/rag.py`, `agent/llm.py` | 添加 `config.py` 管理 API 配置，使用 `python-dotenv` 读取 `.env` 文件 | 模块加载时缺少 API key，报错 `OpenAIError: The api_key client option must be set` |
| 2026-05-02 | `app.py` | 移除 emoji 符号，改为 ASCII 字符；改为英文交互 | Windows GBK 编码无法输出 emoji，报错 `UnicodeEncodeError` |
| 2026-05-02 | `requirements.txt` | 添加 `python-dotenv` 依赖 | 新增配置文件管理 API key |
| 2026-05-02 | 新增 `config.py` | 配置文件，管理 API key 和模型参数 | 解耦配置，方便维护 |
| 2026-05-02 | 新增 `.env` | 存储 API key 和模型配置 | 安全存储敏感信息，不会提交到 GitHub |
| 2026-05-02 | 新增 `.gitignore` | 忽略 `.env`, `__pycache__`, `*.pyc` | 防止敏感信息和缓存文件提交到 GitHub |
| 2026-05-09 | `config.py` | 使用 OpenAI API 配置 | 项目使用 GPT 接口 |
| 2026-05-09 | `.env` | 使用 OpenAI API Key 和模型配置 | 项目使用 GPT 接口 |
| 2026-05-09 | `agent/rag.py` | 使用 OpenAI Embedding 接口生成向量 | 适配 OpenAI API |
| 2026-05-09 | `agent/llm.py` | 使用 OpenAI Chat Completions 接口生成回答 | 适配 OpenAI API |
| 2026-05-16 | `CHANGELOG.md` | 将 API 说明统一为 OpenAI/GPT 接口 | 当前项目使用 OpenAI GPT 接口 |
| 2026-05-16 | `config.py`, `.env.example`, `.gitignore` | 补齐 OpenAI 配置读取、环境变量示例和忽略规则 | 修复可运行基线 |
| 2026-05-16 | `agent/ast_parser.py` | 改为使用 Python 标准库 `ast` 提取函数 | 避免 tree-sitter 兼容问题 |
| 2026-05-16 | `agent/rag.py`, `agent/retriever.py`, `agent/llm.py`, `app.py` | 修复缺目录、空索引、全局状态和配置硬编码问题 | 提升基础可运行性 |
| 2026-05-16 | `requirements.txt`, `data/repo/.gitkeep` | 同步依赖并保留默认代码仓库目录 | 修复本地启动前置条件 |
| 2026-05-24 | `config.py` | 忽略空白 `OPENAI_BASE_URL` 环境变量 | 避免 OpenAI SDK 将空字符串当作 base URL 导致连接错误 |
| 2026-05-24 | `.env` | 本地切换到阿里云百炼兼容接口，使用 `text-embedding-v4` 与 `qwen3.6-flash-2026-04-16` 跑通链路 | 验证国内兼容模型可完成 embedding、检索和 chat 闭环；`.env` 不提交 |
| 2026-05-24 | `.gitignore` | 忽略 `.venv311/` | 防止 Python 3.11 本地虚拟环境被误提交 |
| 2026-05-24 | `agent/ast_parser.py`, `agent/rag.py`, `agent/retriever.py` | 检索结果增加函数名、文件路径、行号、rank 和 score 等 metadata | 支持目标 1 检索命中率评测 |
| 2026-05-24 | `eval/questions.json`, `eval/run_eval.py`, `eval/results/` | 新增第一版检索评测闭环，包含 2 个样例、Recall@1/Recall@K 计算和结果输出 | 验证问题是否能在 top-k 中命中预期函数 |

---

## 使用方法

1. 确保 Python 3.11 环境已激活
2. 安装依赖：`pip install -r requirements.txt`
3. 复制 `.env.example` 为 `.env`，并设置 `OPENAI_API_KEY`
4. 放入测试代码到 `data/repo/` 目录，或在 `.env` 中设置 `REPO_PATH`
5. 运行：`python app.py`
