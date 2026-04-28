# Travel Agent - 智能旅行助手

一个基于 ReAct 模式的智能 Agent，能够根据用户需求查询天气并推荐旅游景点。

## 功能特性

- **天气查询**: 调用 wttr.in API 获取全球城市实时天气
- **景点推荐**: 调用 Tavily Search API 基于天气状况智能推荐景点
- **ReAct 循环**: 模拟 Agent 思考过程，Thought → Action → Observation

## 项目结构

```
Agent/
├── main.py         # 主程序入口
├── client.py       # LLM 客户端（OpenAI 兼容接口）
├── tools.py        # 工具函数定义
├── dictory.py      # 工具注册表
├── config.py       # 系统提示词配置
└── .env            # 环境变量配置（API 密钥）
```

## 快速开始

### 1. 安装依赖

```bash
pip install openai tavily requests python-dotenv
```

### 2. 配置 API 密钥

在项目根目录创建 `.env` 文件：

```env
MINIMAX_API_KEY=您的MiniMax密钥
TAVILY_API_KEY=您的Tavily密钥
```

### 3. 运行 Agent

```bash
python main.py
```

## 使用示例

**用户输入**: "你好，请帮我查询一下今天广州的天气，然后根据天气推荐一个合适的旅游景点。"

**Agent 执行流程**:

1. **Thought**: 用户想查询广州天气并获取景点推荐
2. **Action**: `get_weather(city="广州")`
3. **Observation**: 广州当前天气：多云，气温25摄氏度
4. **Thought**: 已获取天气信息，现在调用景点推荐工具
5. **Action**: `get_attraction(city="广州", weather="多云")`
6. **Observation**: 推荐白云山、越秀公园等景点
7. **Action**: `Finish[...]` 任务完成

## 工具说明

### get_weather(city: str)

查询指定城市的实时天气信息。

**参数**: `city` - 城市名称（英文或中文）

**返回**: 格式化的天气描述字符串

### get_attraction(city: str, weather: str)

根据城市和天气状况搜索推荐景点。

**参数**: 
- `city` - 城市名称
- `weather` - 天气状况描述

**返回**: 景点推荐列表或综合回答

## 配置说明

修改 `config.py` 中的 `AGENT_SYSTEM_PROMPT` 可自定义 Agent 行为和工具描述。

修改 `main.py` 中的 `MODEL_ID` 可切换不同的 LLM 模型（当前使用 MiniMax-M2）。

## 技术栈

- **Python 3.13**
- **OpenAI SDK** - LLM 接口调用
- **Tavily API** - 景点搜索
- **wttr.in** - 天气数据源