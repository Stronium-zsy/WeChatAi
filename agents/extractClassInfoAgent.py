from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

from typing import TypeVar
from constrants.classes import *
import requests

notification_url = "http://211.71.76.144:8000/api/notification"


def extract_class_info(chat_content: str, class_type: str):
    payload = {"text": chat_content}

    if class_type == "Notification":
        response = requests.post(notification_url, json=payload)
    else:
        raise ValueError("Invalid class type")

    return response.json().get("result", "No result found")
