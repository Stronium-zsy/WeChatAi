import json
import sqlite3
from queue import Empty
from threading import Thread

from fastapi import FastAPI
from flask import jsonify, request
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from wcferry import Wcf, WxMsg
from datetime import datetime, timedelta

from agents.emotionAgent import calculate_emotions_grouped_chat
from agents.extractClassInfoAgent import extract_class_info
from persistance.events_database_api import is_in_extract_friends, insert_event, get_all_friends, insert_friend, \
    get_all_emotions, get_all_events
from persistance.wechat_database_api import fetch_count_messages_by_talker_and_time
from tools.helpers import find_latest_database, calculate_chat_temperature_log

app = FastAPI()

# 添加 CORS 支持，允许所有源（生产环境中建议限制 allowed origins）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名访问
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
wcf = Wcf()

# 用于存储每个发送者的消息块
sender_time_batches = {}  # 格式： {sender: [(timestamp, message), ...]}
# 预加载 JSON 数据到内存
with open("connections.json", "r", encoding="utf-8") as f:
    data = json.load(f)

connections = data.get("connections", {})
user_info = data.get("user_info", {})


def processMsg(msg: WxMsg):
    """处理消息（根据发送者和时间分块）"""
    sender = msg.sender
    current_time = datetime.now()
    print(sender)

    # 如果是需要的朋友列表中的消息
    if is_in_extract_friends(sender):
        # 获取当前发送者的时间块
        if sender not in sender_time_batches:
            sender_time_batches[sender] = []

        print(sender, msg.content)

        # 获取当前发送者的最后一条消息时间
        last_msg_time = sender_time_batches[sender][-1][0] if sender_time_batches[sender] else None

        # 如果最后一条消息时间存在，检查时间差
        if last_msg_time:
            time_diff = current_time - last_msg_time
            # 如果时间差小于1分钟，认为是同一时间块
            if time_diff <= timedelta(minutes=(1 / 6)):
                sender_time_batches[sender].append((current_time, msg))

            else:
                # 拼接当前时间块内的所有消息内容
                messages_content = "".join([msg_item[1].content for msg_item in sender_time_batches[sender]])
                # 提取事件信息
                event_info = extract_class_info(
                    chat_content=messages_content,
                    class_type="Notification")
                emotion_info = calculate_emotions_grouped_chat(sender_time_batches[sender])
                emotion_info['wechat_id'] = sender

                # 提取数据并构建 JSON 对象
                # 构造 notification_json
                notification_json = {
                    "notification_type": "Notification",  # 固定为"Notification"
                    "content": event_info[0].get('通知者', [{}])[0].get('text', ""),  # 获取"通知者"的text
                    "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "event_time": event_info[0].get('时间', [{}])[0].get('text', ""),  # 获取"时间"的text
                    "friend_name": event_info[0].get('通知者', [{}])[0].get('text', "")  # 获取"通知者"的text作为朋友的名字
                }

                # 统计非空字段数量（除去 "notification_type"）
                non_empty_fields = sum(
                    1 for key in ["content", "timestamp", "event_time", "friend_name"] if notification_json[key])

                # 只有非空字段数量至少为4，才插入
                if non_empty_fields >= 4:
                    insert_event("Notification", notification_json)
                insert_event("emotions", emotion_info)

                # 提取事件后清空当前时间块，重新开始新的时间块
                sender_time_batches[sender] = [(current_time, msg)]
        else:
            # 如果是该发送者的第一条消息，直接加入
            sender_time_batches[sender].append((current_time, msg))

        # 输出当前分块的消息
        print(f"Sender: {sender}, Message Time: {current_time}, Message: {msg.content}")


def enableReceivingMsg():
    """ 启动 Wcferry 消息监听 """

    def innerWcFerryProcessMsg():
        while wcf.is_receiving_msg():
            try:
                msg = wcf.get_msg()
                if msg:
                    processMsg(msg)
            except Empty:
                continue
            except Exception as e:
                print(f"ERROR: {e}")

    wcf.enable_receiving_msg()
    Thread(target=innerWcFerryProcessMsg, name="ListenMessageThread", daemon=True).start()


@app.get("/api/contacts")
def get_contacts():
    contacts = wcf.get_contacts()
    for contact in contacts:
        if is_in_extract_friends(contact['wxid']):
            contact['is_extracted'] = True
        else:
            contact['is_extracted'] = False
    return {"contacts": contacts}


@app.get("/")
def home():
    return {"message": "Wcferry Server is running!"}


@app.post("/send_message/")
def send_message(wxid: str, content: str):
    """ 发送消息接口 """
    success = wcf.send_text(wxid, content)
    return {"wxid": wxid, "content": content, "success": success}


@app.get("/api/emotions")
def get_emotions(period: str = 'day', wechat_id: str = ''):
    time_lengths = {
        "day": 86400,   # 1天的秒数
        "week": 604800,  # 7天的秒数
        "month": 2592000 # 30天的秒数
    }

    if not wechat_id:
        return JSONResponse(content={"error": "wechat_id is required"}, status_code=400)

    # 获取情绪数据并按时间范围聚集
    emotions = get_all_emotions(wechat_id, time_lengths[period])

    if not emotions:
        return JSONResponse(content={"message": "No data found for this wechat_id"}, status_code=404)

    # 返回 JSON 格式的情感数据
    return JSONResponse(content={"emotions": emotions})


@app.get("/api/search")
def search_connections(user: str):
    if not user:
        return JSONResponse(content={"error": "Missing 'user' parameter"}, status_code=400)

    # 检查是否为 UserName
    user_id = user if user in user_info else None

    # 如果不是 UserName，检查是否是 Remark 或 NickName
    if not user_id:
        for uid, display_name in user_info.items():
            if display_name.lower() == user.lower():  # 忽略大小写
                user_id = uid
                break

    if not user_id:
        return JSONResponse(content={"message": "User not found"}, status_code=404)

    # 遍历 connections 时，避免重复解析 JSON，同时捕获解析异常
    related_connections = {}
    for edge, weight in connections.items():
        try:
            parsed_edge = json.loads(edge)
        except json.JSONDecodeError:
            continue  # 如果 edge 不是有效 JSON，则跳过
        if user_id in parsed_edge:
            related_connections[edge] = weight

    display_connections = {}
    for edge, weight in related_connections.items():
        try:
            parsed_edge = json.loads(edge)
        except json.JSONDecodeError:
            continue
        # 使用 user_info 替换展示名称，如果不存在则直接使用原始 id
        display_edge = [
            user_info.get(parsed_edge[0], parsed_edge[0]),
            user_info.get(parsed_edge[1], parsed_edge[1])
        ]
        display_connections[json.dumps(display_edge)] = weight

    return JSONResponse(content={
        "user": {"id": user_id, "display_name": user_info.get(user_id, user_id)},
        "connections": display_connections
    })


@app.get("/api/allEvents")
def events():
    all_events = get_all_events()
    print(all_events)
    return JSONResponse(content={"events": all_events})


@app.get("/status/")
def status():
    """ 查询 Wcferry 运行状态 """
    return {"receiving_msg": wcf.is_receiving_msg()}


if __name__ == "__main__":
    enableReceivingMsg()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
