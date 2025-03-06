from enum import Enum

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from typing import List, Literal
from pydantic import BaseModel, Field
from tools.openaiClient import get_response


# 修改后的 EventSelector 类
class EventSelector(BaseModel):
    selected_events: List[Literal["CasualChat", "TaskAssignment", "Notification", "Appointment"]] = Field(
        description="List of selected event categories",
        example={
            "examples": [
                ["CasualChat", "TaskAssignment"],
                ["Notification", "Appointment"],
                ["CasualChat", "Notification"],
                ["TaskAssignment", "Appointment", "CasualChat"]
            ]
        }
    )


classify_parser = PydanticOutputParser(pydantic_object=EventSelector)
classify_template = """

# 提示任务描述

**角色**：你是一名专业的聊天记录类别提取人员。

**任务**：用户将上传聊天记录，你需要从中提取出类别。类别可以有多个，也可以没有。

---

#### 聊天记录：
```plaintext
{chat_content}
```

---

### 输出要求

#### 输出格式：
```json
{format_instructions}
```

---


### 注意事项
1. **准确性**：确保提取的类别与聊天记录内容匹配。
2. **灵活性**：支持多个类别或无类别的情况。
3. **标准化**：严格按照指定的输出格式。

---

请根据以上要求完成任务。


"""

classify_prompt = PromptTemplate.from_template(
    template=classify_template,
    partial_variables={"format_instructions": classify_parser.get_format_instructions()},
)


def classify_events(chat_content: str):
    prompt_text = classify_prompt.format(chat_content=chat_content)
    return get_response(prompt_text)
