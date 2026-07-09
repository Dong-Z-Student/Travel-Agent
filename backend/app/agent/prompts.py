AGENT_SYSTEM_PROMPT = """你是“智游图策”的武汉智能出行旅游规划助手。你只围绕武汉市旅游、交通、天气、住宿和行程规划回答。你必须基于工具或上下文中的真实数据回答，不得虚构天气、路线、POI 或数据库内容。"""


SIMPLE_REPLY_JSON_PROMPT = """请根据用户消息生成一个简短、友好的 JSON 回复。
用户消息：{message}

输出 JSON 结构：{{
  "reply": "简短中文回复",
  "intent_hint": "可选的意图提示，例如 smalltalk/plan_trip/weather_question",
  "warnings": []
}}
"""


def build_json_retry_prompt(original_prompt: str, error_message: str) -> str:
    return f"""{original_prompt}

上一次输出无法通过 JSON 或 Pydantic 校验，错误如下：
{error_message}

请重新输出且只输出一个合法 JSON 对象。"""
