from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import re
import os
from prompts import AGENT_SYSTEM_PROMPT
from tools import available_tools
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

user_prompt = "你好，请帮我查询⼀下今天西安的天⽓，然后根据天⽓推荐⼀个合适的旅游景点。"
prompt_history = [f"用户请求：{user_prompt}"]

for i in range(5):
    print(f"---循环{i+1}---\n")

    full_prompt = "\n".join(prompt_history)

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
    
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "="*40)
    prompt_history.append(observation_str)