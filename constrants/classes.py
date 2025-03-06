from typing import Optional, List

from pydantic import BaseModel
from pydantic.fields import Field


class CasualChat(BaseModel):
    summary: Optional[str] = Field(default=None, description="A brief summary of the chat message content")
    emotion: Optional[str] = Field(default=None,
                                   description="The emotion or sentiment of the chat (e.g., happy, sad, neutral)")


class TaskAssignment(BaseModel):
    task_name: str = Field(description="The name or description of the assigned task")
    assignee: str = Field(description="The person who is assigned the task")
    deadline: Optional[str] = Field(default=None, description="The deadline for completing the task")
    priority: Optional[str] = Field(default="Normal",
                                    description="The priority level of the task (e.g., High, Medium, Low)")


class Notification(BaseModel):
    notification_type: str = Field(description="The type of the notification (e.g., system, event, update)")
    content: str = Field(description="The content of the notification")
    timestamp: Optional[str] = Field(default=None, description="The time the notification was generated")


class Appointment(BaseModel):
    appointment_time: str = Field(description="The time of the appointment or meeting")
    location: Optional[str] = Field(default=None, description="The location of the appointment")
    participants: List[str] = Field(description="The list of participants involved in the appointment")
    purpose: Optional[str] = Field(default=None, description="The purpose or topic of the appointment")


class CasualChatList(BaseModel):
    casual_chats: List[CasualChat] = Field(
        description="A list of casual chat events."
    )


class TaskAssignmentList(BaseModel):
    task_assignments: List[TaskAssignment] = Field(
        description="A list of task assignments."
    )


class NotificationList(BaseModel):
    notifications: List[Notification] = Field(
        description="A list of notifications."
    )


class AppointmentList(BaseModel):
    appointments: List[Appointment] = Field(
        description="A list of appointments."
    )
