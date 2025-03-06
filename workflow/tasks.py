# -*- coding: utf-8 -*-

import os
import json
import pandas as pd
from datetime import datetime

from agents.emotionAgent import calculate_emotions_grouped_chat
from persistance.build_events_database_api import transfer_and_create_index
from tools.helpers import decrypt_database, find_latest_database, save_task_status, read_task_status, \
    group_by_time_interval
from persistance.events_database_api import is_in_extract_friends, insert_event, insert_emotions
from agents.classifyAgent import classify_events
from agents.extractClassInfoAgent import extract_class_info
from persistance.wechat_database_api import get_connection, fetch_messages_between_time, fetch_contact_info

event_db_path = r"database/incidents.db"
contact_db_path = r"decrypted/de_MicroMsg.db"
# 定义一个映射关系，将 event_name 对应到 key
key_map = {
    "CasualChat": "casual_chats",
    "TaskAssignment": "task_assignments",
    "Notification": "notifications",
    "Appointment": "appointments",
}


def get_incremental_messages(start_time, end_time):
    """
    查询增量消息
    """
    output_db = find_latest_database()
    if not output_db or not os.path.exists(output_db):
        print(f"[{datetime.now()}] 数据库文件不存在，无法查询数据。")
        return pd.DataFrame()

    print(f"使用数据库文件：{output_db}")
    conn_msg = get_connection(output_db)
    conn_contact = get_connection(contact_db_path)
    if not conn_msg or not conn_contact:
        return pd.DataFrame()

    try:
        results, columns = fetch_messages_between_time(conn_msg, start_time, end_time)
        if not results:
            print(f"[{datetime.now()}] 未查询到增量消息。")
            return pd.DataFrame()

        df = pd.DataFrame(results, columns=columns)

        categorized_messages = []
        for _, row in df.iterrows():
            talker = row['StrTalker']
            if not is_in_extract_friends(talker):
                continue
            categorized_messages.append(row)

        return pd.DataFrame(categorized_messages)

    finally:
        conn_msg.close()
        conn_contact.close()


def process_task():
    """
    主任务逻辑：解密数据库、提取增量信息并调用事件提取模块
    """
    print(f"任务开始，当前时间：{datetime.now()}")
    now_timestamp = datetime.now().timestamp()
    task_status = read_task_status()
    last_run_time = task_status["last_run_time"] if task_status else now_timestamp - 3 * 60 * 60

    if not decrypt_database():
        print(f"[{datetime.now()}] 数据库解密失败，跳过本次任务。")
        return

    df = get_incremental_messages(last_run_time, now_timestamp)
    if df.empty:
        print(f"[{datetime.now()}] 没有增量消息，本次任务结束。")
        save_task_status(now_timestamp)
        return

    grouped = df.groupby("StrTalker")
    for friend, group in grouped:
        try:
            messages = group.to_dict(orient="records")

            # 创建 chat_records 和 message_times 合并后的数据
            merged_records = [
                {
                    "chat_record": f"{'我' if row['IsSender'] == 1 else friend}: {row['StrContent']}",
                    "timestamp": row['CreateTime']
                }
                for row in messages
            ]
            # 提取时间戳并进行排序
            timestamps = [record["timestamp"] for record in merged_records]
            timestamps.sort()

            # 调用 group_by_time_interval 方法对时间戳进行分组
            grouped_timestamps = group_by_time_interval(timestamps)
            print(grouped_timestamps)

            # 根据分组的时间戳，将聊天记录按时间分组
            grouped_records = []
            for group in grouped_timestamps:
                group_records = [record for record in merged_records if record["timestamp"] in group]
                grouped_records.append(group_records)

            emotions_batches = calculate_emotions_grouped_chat(grouped_records)
            for batch in emotions_batches:
                # 为每组分配 wechat_id
                batch["wechat_id"] = friend
                # 插入到 emotions 表中
                insert_event("emotions", batch)

        except Exception as e:
            print(f"Error processing {friend}: {str(e)}")

    save_task_status(now_timestamp)
    print("任务完成。\n")
