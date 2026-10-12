from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import re
import os
from prompts import AGENT_SYSTEM_PROMPT ,REFLECTION_BLOCK ,user_prompt
from tools import available_tools, extract_preferences ,MEMORY, EXCLUDED, MAX_ALTERNATIVES ,REJECT_COUNT, REJECTED_LIST, reset_reject_count
from dotenv import load_dotenv


load_dotenv()


class OpenAICompatibleClient:
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str)-> str:
        print("正在调用大语言模型。。。")

        try:
            messages: list[ChatCompletionMessageParam] = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
            response = self.client.chat.completions.create(
                model = self.model,
                messages = messages,
                stream = False
            )
            answer = response.choices[0].message.content or ""
            print("模型响应成功")
            return answer
        except Exception as e:
            print(f"调用模型，API出现错误：{e}")
            return("大模型服务出错")

llm = OpenAICompatibleClient(
    model = os.environ["OPENAI_MODEL"],
    api_key = os.environ["OPENAI_API_KEY"],
    base_url = os.environ["OPENAI_BASE_URL"]
)

# user_prompt = "你好，请帮我查询⼀下今天西安的天⽓，然后根据天⽓推荐⼀个合适的旅游景点。"
prompt_history = [f"用户请求：{user_prompt}"]

# 循环前：从用户请求启发式提取偏好，写入记忆
for _key, _value in extract_preferences(user_prompt):
    MEMORY[_key] = _value
    print(f"[记忆]提取偏好：{_key} -> {_value}")

for i in range(10):    # 原为 range(5)，查票+备选需要更多轮
    print(f"---循环{i+1}---\n")

    # ③ 连续拒绝反思：>=3 时在 Thought 之前注入反思指令
    if REJECT_COUNT >= 3:
        reflection_prompt = REFLECTION_BLOCK.format(rejected="、".join(REJECTED_LIST))
        prompt_history.append(reflection_prompt)
        reset_reject_count()     # 反思指令已注入，清零计数（黑名单与记忆保留）
        print(f"已触发连续拒绝反思，注入反思指令：\n{reflection_prompt}\n")
    # ① 记忆/状态注入：每轮重建，不写入历史（避免上下文膨胀与截断丢失）
    ctx = "；".join([f"{k}:{v}" for k,v in MEMORY.items()]) if MEMORY else ""
    if EXCLUDED:
        ctx += f"；已售罄，排除景点：{'、'.join(EXCLUDED)}"
    full_prompt = "\n".join(prompt_history)
    if ctx:
        full_prompt = f"【当前状态】{ctx}\n\n" + full_prompt
    print(f"本轮完整Prompt：\n{full_prompt}\n")

    llm_output = llm.generate(full_prompt,system_prompt=AGENT_SYSTEM_PROMPT)

    match = re.search(
        r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)',
        llm_output,
        re.DOTALL
    )
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("已截断多余Thought-Action对")
    print(f"模型输出：\n{llm_output}\n")
    prompt_history.append(llm_output)

    action_match = re.search(r"Action:(.*)", llm_output, re.DOTALL)
    if not action_match:
        observation = "未解析到Action字段"
        observation_str = f"Observation:{observation}"
        print(f"{observation_str}\n"+ "="*40)
        prompt_history.append(observation_str)
        continue
    action_str = action_match.group(1).strip()

    if action_str.startswith("Finish"):
        finish_match = re.match(r"Finish\[(.*)\]", action_str, re.DOTALL)
        if not finish_match:
            observation_str = "Observation: Finish格式错误，应为 Finish[最终答案]"
            print(f"{observation_str}\n" + "="*40)
            prompt_history.append(observation_str)
            continue
        final_answer = finish_match.group(1)
        print(f"最终答案：{final_answer}")
        break

    tool_match = re.search(r"(\w+)\((.*)\)", action_str, re.DOTALL)
    if not tool_match:
        observation_str = "Observation: Action格式错误，应为 function_name(arg_name=\"arg_value\")"
        print(f"{observation_str}\n" + "="*40)
        prompt_history.append(observation_str)
        continue
    tool_name = tool_match.group(1)
    args_str = tool_match.group(2)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"错误:未定义工具'{tool_name}'"

    # ② 售罄兜底：Observation 后处理（工具层已自动拉黑，这里补提示）
    if "售罄" in observation:
        if len(EXCLUDED) >= MAX_ALTERNATIVES:
            observation += f"；已排除{len(EXCLUDED)}个景点，达到最大备选数{MAX_ALTERNATIVES}，请调整推荐策略,不在继续推荐同类。"
        else:
            observation += "；已将该景点加入排除列表，后续推荐将避开。"

    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "=" * 40)
    prompt_history.append(observation_str)