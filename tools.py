import requests
import os
from typing import Callable
from tavily import TavilyClient
import re


# ============ 新增：记忆 / 售罄黑名单 / 拒绝计数（进程内状态） ============
MEMORY: dict[str, str] = {}       # 用户偏好画像
EXCLUDED: set[str] = set()        # 已售罄/被排除的景点黑名单
REJECT_COUNT = 0                  # 连续拒绝计数
REJECTED_LIST: list[str] = []     # 最近被拒的推荐
MAX_ALTERNATIVES = 3              # 售罄后最多尝试的备选次数


def get_weather(city: str) -> str:
    url = f'https://wttr.in/{city}?format=j1'

    try:
        response = requests.get(url,timeout=15)   # 加超时，防止挂起
        response.raise_for_status()
        data = response.json()

        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        return f"{city}当前天气:{weather_desc},气温 {temp_c} 摄氏度"

    except requests.exceptions.RequestException as e:
        return f"网络错误-{e}"
    except (KeyError, IndexError) as e:
        return f"数据解析失败-{e}"

def get_attraction(city: str, weather: str, preferences: str = "", exclude: str = "") -> str:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "未配置环境变量"

    tavily = TavilyClient(api_key=api_key)
    excluded = set(x.strip() for x in exclude.replace("，","、").split("、") if x.strip())
    excluded |= EXCLUDED
    exclude_note = f"请排除以下景点：{'、'.join(excluded)}" if excluded else ""
    preferences_note = f"用户偏好：{preferences}" if preferences else ""
    if not preferences and MEMORY:
        preferences_note = "，参考用户记忆：" + "； ".join([f"{k}:{v}" for k,v in MEMORY.items()])
    query = f"请推荐'{city}'在'{weather or '任意'}'天气最值得去的旅游景点推荐，并给出理由。{preferences_note} {exclude_note}"
    # query = f"'{city}'在'{weather}'天气最值得去的旅游景点推荐及理由"

    try:
        response = tavily.search(query=query, search_depth="basic",include_answer=True)

        if response.get("answer"):
            return response["answer"]

        formatted_results = []
        for result in response.get("results",[]):
            formatted_results.append(f"-{result['title']}:{result['content']}")

        if not formatted_results:
            return "抱歉，没有找到相关推荐"

        return "找到以下信息：\n" + "\n".join(formatted_results)
    except Exception as e:
        return f"执行Tavily出现错误-{e}"

def extract_preferences(text: str) -> list[tuple[str, str]]:
    """从用户一句话里启发式提取偏好，返回 [(key, value), ...]"""
    preferences = []
    budget_match = re.search(r"预算[^\d]{0,4}(\d+)\s*[-~至到]\s*(\d+)", text)
    if budget_match:
        preferences.append(("预算范围", f"{budget_match.group(1)}-{budget_match.group(2)}元"))
    else:
        budget_single_match = re.search(r"预算[^\d]{0,4}(\d+)\s*(以内|一下|左右)?", text)
        if budget_single_match:
            preferences.append(("预算上限", f"{budget_single_match.group(1)}元" + (budget_single_match.group(2) or "")))
    for kw, tag in[("历史","历史文化"),("古迹","历史文化"),("自然","自然风光"),("美食","美食"),("亲子","亲子"),("小众","小众/人少")]:
        if kw in text:
            preferences.append(("偏好类型", tag))
            break
    return preferences

def remember_preferences(fact: str) -> str:
    """LLM 在对话中发现用户偏好时调用，存入记忆。"""
    key = next((k for k in("预算","类型","偏好") if k in fact), "偏好")
    MEMORY[key] = fact
    return f"已记住：{key}={fact}"

def get_memory() -> str:
    """查看当前记忆。"""
    return "; ".join([f"{k}:{v}" for k,v in MEMORY.items()]) if MEMORY else "暂无用户偏好"

def check_ticket_availability(attraction: str) -> str:
    """检查景点门票是否有余票。售罄时自动拉黑，可替换为真实票务 API"""
    if not attraction:
        return "请提供景点名称"
    forced = [n.strip() for n in os.environ.get("SOLD_OUT_ATTRACTIONS", "").split(",") if n.strip()]
    is_sold_out = attraction in forced or (sum(ord(c) for c in attraction) % 100) <45
    if is_sold_out:
        EXCLUDED.add(attraction)   # 工具层强制拉黑，防止重复推荐
        return f"{attraction}门票已售罄,请推荐备选方案"
    return f"{attraction}门票有余票,可正常预定"

def record_feedback(rejected: str) -> str:
    """记录一次用户拒绝，驱动连续拒绝反思。"""
    global REJECT_COUNT
    REJECT_COUNT += 1
    REJECTED_LIST.append(rejected)
    hint = ",连续3次后触发策略反思" if REJECT_COUNT >= 3 else ""
    return f"已记录用户拒绝:{rejected},当前连续拒绝{REJECT_COUNT} 次{hint}"

def reset_reject_count() -> None:
    """重置连续拒绝计数器"""
    global REJECT_COUNT
    REJECT_COUNT = 0
    REJECTED_LIST.clear()

available_tools: dict[str, Callable[..., str]] = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
    "check_ticket_availability": check_ticket_availability,
    "remember_preferences": remember_preferences,
    "get_memory": get_memory,
    "record_feedback": record_feedback,
}