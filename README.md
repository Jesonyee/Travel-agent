<<<<<<< HEAD
# 智能旅行助手

一个基于 **ReAct（Thought-Action-Observation）** 范式的分步任务智能体示例。用户只需给出一个模糊的目标，智能体就会自动拆解任务、调用工具、理解观察结果，并合成最终答案。

示例任务：

> 你好，请帮我查询一下今天西安的天气，然后根据天气推荐一个合适的旅游景点。

## 工作原理

智能体通过「思考 -> 行动 -> 观察」的循环不断迭代，把模糊的用户意图转化为一系列具体、可执行的步骤：

1. **Thought（思考）**：分析当前已知信息，规划下一步做什么。
2. **Action（行动）**：调用某个工具，或使用 `Finish[...]` 结束任务。
3. **Observation（观察）**：把工具返回的结果追加到对话历史中，供下一轮参考。

循环最多执行 5 轮，直到模型输出 `Action: Finish[最终答案]`。

模型每次必须严格按照以下格式回复：

```
Thought: [你的思考过程和下一步计划]
Action: [你要执行的具体行动]
```

其中 `Action` 只能是以下两种形式之一：

- 调用工具：`function_name(arg_name="arg_value")`
- 结束任务：`Finish[最终答案]`

## 项目结构

```
agent/
├── llm.py          # 入口：OpenAI 兼容客户端 + ReAct 主循环
├── prompts.py      # 系统提示词（AGENT_SYSTEM_PROMPT）
├── tools.py        # 可用工具：get_weather / get_attraction
├── requirements.txt
└── .env            # 本地环境变量（已在 .gitignore 中忽略）
```

## 可用工具

| 工具 | 签名 | 说明 |
| --- | --- | --- |
| `get_weather` | `get_weather(city: str)` | 通过 [wttr.in](https://wttr.in) 查询指定城市的实时天气 |
| `get_attraction` | `get_attraction(city: str, weather: str)` | 通过 Tavily 搜索，结合城市与天气推荐旅游景点 |

## 快速开始

### 1. 安装依赖

需要 Python 3.10 及以上版本（开发环境为 Python 3.11）。

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件，填入以下内容：

```dotenv
# 大模型服务（使用 OpenAI 兼容接口，这里以 DeepSeek 为例）
OPENAI_API_KEY=你的模型 API Key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# Tavily 搜索服务，用于景点推荐
TAVILY_API_KEY=你的 Tavily API Key
```

- `OPENAI_BASE_URL` 可替换为任意 OpenAI 兼容服务地址（如 `https://api.openai.com/v1`）。
- `OPENAI_MODEL` 需填写该服务实际支持的模型名。
- Tavily 的 Key 可在 [tavily.com](https://tavily.com) 免费申请。

### 3. 运行

```bash
python llm.py
```

终端会按轮次打印模型的思考、行动、工具观察结果，最终输出 `最终答案`。若要更换提问，修改 `llm.py` 中的 `user_prompt` 变量即可。

## 运行示例

```
---循环1---
Thought: 用户想知道西安今天的天气，我需要先查询天气。
Action: get_weather(city="西安")
Observation: 西安当前天气:多云,气温 18 摄氏度
========================================
---循环2---
Thought: 已拿到天气，接下来根据天气推荐景点。
Action: get_attraction(city="西安", weather="多云")
Observation: 找到以下信息：...
========================================
---循环3---
Thought: 信息已足够，可以给出最终推荐。
Action: Finish[今天西安多云，气温 18℃，适合游览 ...]
最终答案：今天西安多云，气温 18℃，适合游览 ...
```

## 说明与注意事项

- `.env` 已被 `.gitignore` 忽略，请勿把 API Key 提交到仓库。
- `get_weather` 依赖第三方接口 `wttr.in`，网络异常或城市名无法识别时会返回错误提示。
- `get_attraction` 依赖 Tavily 返回的搜索结果，未配置 `TAVILY_API_KEY` 时会提示「未配置环境变量」。
- 若模型输出不符合约定格式，循环会把错误信息作为 `Observation` 回传，让模型自我纠正；达到最大轮次仍未结束则会退出。
=======
构建⼀个能处理分步任务的智能旅⾏助⼿。需要解决的⽤户任务定义为："你好，请帮我查询⼀下今天city的天⽓，然后根据天⽓推荐⼀个合适的旅游景点。"
基于Thought-Action-Observation 范式的智能体所具备的四项基本能⼒：任务分解、⼯具调⽤、上下⽂理解和结果合成。正是通过这个循环的不断迭代，智能体才得以将⼀个模糊的⽤户意图，转化为⼀系列具体、可执⾏的步骤，并最终达成⽬标
>>>>>>> a975e5f928b51aeebe57d74848c659e314fea002
