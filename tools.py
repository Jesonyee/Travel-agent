import requests
import os
from typing import Callable
from tavily import TavilyClient

def get_weather(city: str) -> str:
    url = f'https://wttr.in/{city}?format=j1'

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        return f"{city}当前天气:{weather_desc},气温{temp_c}摄氏度"

    except requests.exceptions.RequestException as e:
        return f"网络错误-{e}"
    except (KeyError, IndexError) as e:
        return f"数据解析失败-{e}"

def get_attraction(city: str, weather: str)-> str:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "未配置环境变量"

    tavily = TavilyClient(api_key=api_key)

    query = f"'{city}'在'{weather}'天气最值得去的旅游景点推荐及理由"

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

available_tools: dict[str, Callable[..., str]] = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}
