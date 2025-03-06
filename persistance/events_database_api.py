import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any


# 数据库连接函数
def get_db_connection():
    conn = sqlite3.connect("database/incidents.db")
    conn.row_factory = sqlite3.Row
    return conn


# 创建表结构
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            friend_name TEXT UNIQUE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            friend_id INTEGER,
            incident_time TEXT,
            incident_details TEXT,
            FOREIGN KEY (friend_id) REFERENCES friends (id)
        )
    """)
    conn.commit()
    conn.close()


def is_in_extract_friends(str_talker):
    """
    检查指定的 StrTalker 是否在 extract_friends 表中。

    Args:
        str_talker (str): 消息中的 StrTalker 字段值。

    Returns:
        bool: 如果存在于 extract_friends 表中，返回 True，否则返回 False。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM extract_friends WHERE str_talker = ?", (str_talker,))
        count = cursor.fetchone()[0]
        return count > 0
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 检查 extract_friends 表出错：{e}")
        return False
    finally:
        conn.close()


# 插入数据到 `friends` 表
def insert_friend(friend_name: str) -> int:
    """
    插入好友到 friends 表中。如果好友已经存在，则返回其 ID。

    Args:
        friend_name (str): 好友名称。

    Returns:
        int: 好友的 ID。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 检查好友是否已存在
        cursor.execute("SELECT id FROM friends WHERE friend_name = ?", (friend_name,))
        friend = cursor.fetchone()
        if friend:
            return friend["id"]

        # 插入新好友
        cursor.execute("INSERT INTO friends (friend_name) VALUES (?)", (friend_name,))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 插入好友出错：{e}")
        return -1
    finally:
        conn.close()


def update_friend_name(old_name: str, new_name: str):
    """
    更新好友的名称。

    Args:
        old_name (str): 原来的好友名称。
        new_name (str): 新的好友名称。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE friends SET friend_name = ? WHERE friend_name = ?", (new_name, old_name))
        conn.commit()
        print(f"[{datetime.now()}] 成功将好友名称从 {old_name} 更新为 {new_name}")
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 更新好友名称出错：{e}")
    finally:
        conn.close()


def get_all_emotions(wechat_id: str, time_length) -> List[Dict[str, Any]]:
    """
    获取指定wechat_id的所有情感数据。

    Args:
        wechat_id (str): 用户的wechat_id。

    Returns:
        List[Dict[str, Any]]: 情感数据列表。
        :param wechat_id:
        :param time_length:
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 获取当前时间戳和计算开始时间戳
        end_time_stamp = datetime.now().timestamp()
        start_time_stamp = end_time_stamp - time_length
        # 执行查询，查询指定时间范围内的数据
        cursor.execute("""
                    SELECT * FROM emotions 
                    WHERE wechat_id = ? 
                    AND timestamp >= ? 
                    AND timestamp <= ?
                """, (wechat_id, start_time_stamp, end_time_stamp))
        rows = cursor.fetchall()

        # 返回查询结果，转换为字典格式
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        # 捕获并打印错误
        print(f"[{datetime.now()}] 获取情感数据出错：{e}")
        return []
    finally:
        # 确保连接关闭
        conn.close()


def delete_friend(friend_name: str):
    """
    删除好友及其关联的数据。

    Args:
        friend_name (str): 好友名称。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM friends WHERE friend_name = ?", (friend_name,))
        conn.commit()
        print(f"[{datetime.now()}] 成功删除好友：{friend_name}")
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 删除好友出错：{e}")
    finally:
        conn.close()


def insert_extract_friends(str_talker: str):
    """
    插入 extract_friends 表。

    Args:
        friend_id (int): 好友 ID。
        str_talker (str): 消息中的 StrTalker 字段值。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        print(str_talker)
        # 检查是否已经插入
        cursor.execute("SELECT COUNT(*) FROM extract_friends WHERE str_talker = ?", (str_talker,))
        count = cursor.fetchone()[0]
        if count > 0:
            return

        # 插入新数据
        cursor.execute("INSERT INTO extract_friends (str_talker) VALUES (?)", (str_talker,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 插入 extract_friends 出错：{e}")
    finally:
        conn.close()


def get_all_friends() -> List[Dict[str, Any]]:
    """
    获取所有好友。

    Returns:
        List[Dict[str, Any]]: 好友列表。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM friends")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 获取好友列表出错：{e}")
        return []
    finally:
        conn.close()


def get_events_by_friend(friend_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    获取某个好友的所有事件。

    Args:
        friend_name (str): 好友名称。

    Returns:
        Dict[str, List[Dict[str, Any]]]: 包含所有事件的字典。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    tables = [
        "Notification"
    ]
    events = {}
    try:
        for table in tables:
            cursor.execute(f"SELECT * FROM {table} WHERE friend_name = ?", (friend_name,))
            rows = cursor.fetchall()
            events[table] = [dict(row) for row in rows]
        return events
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 查询好友事件出错：{e}")
        return {}
    finally:
        conn.close()


def delete_event(table_name: str, event_id: int):
    """
    删除某个表中的事件。

    Args:
        table_name (str): 表名。
        event_id (int): 事件的 ID。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (event_id,))
        conn.commit()
        print(f"[{datetime.now()}] 成功删除表 {table_name} 中的事件 ID：{event_id}")
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 删除事件出错：{e}")
    finally:
        conn.close()


def bulk_insert_events(table_name: str, events: List[Dict[str, Any]]):
    """
    批量插入事件到指定的表。

    Args:
        table_name (str): 表名。
        events (List[Dict[str, Any]]): 插入的事件列表。
    """
    if not events:
        print(f"[{datetime.now()}] 没有事件需要插入。")
        return

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        columns = ", ".join(events[0].keys())
        placeholders = ", ".join(["?"] * len(events[0]))
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        values = [tuple(event.values()) for event in events]

        cursor.executemany(sql, values)
        conn.commit()
        print(f"[{datetime.now()}] 成功批量插入 {len(events)} 条事件到表 {table_name}")
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 批量插入事件到表 {table_name} 出错：{e}")
    finally:
        conn.close()


# 插入数据到具体表
def insert_event(table_name: str, data: dict):
    """
    插入事件到指定的表中。

    Args:
        table_name (str): 表名。
        data (dict): 插入的数据，包括 friend_name、event_time 和其他字段。
    """
    print(f"[{datetime.now()}] 正在插入事件到表 {table_name}：{data}")
    conn = get_db_connection()
    try:
        # 构建 SQL 和参数
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        values = tuple(data.values())

        # 执行插入操作
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        print(f"[{datetime.now()}] 成功插入事件到表 {table_name}：{data}")
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 插入事件到表 {table_name} 出错：{e.with_traceback()}")
    finally:
        conn.close()


def insert_emotions(friend, data: dict):
    #friend 对应 emotions表的wechat_id字段
    conn = get_db_connection()
    try:
        # 构建 SQL 和参数
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT INTO emotions ({columns}) VALUES ({placeholders})"
        values = tuple(data.values())

        # 执行插入操作
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        print(f"[{datetime.now()}] 成功插入事件到表 {friend}：{data}")
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 插入事件到表 {friend} 出错：{e.with_traceback()}")
    finally:
        conn.close()


def get_all_events():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Notification")
        rows = cursor.fetchall()
        # 将 sqlite3.Row 转换为字典
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 查询事件出错：{e}")
        return []
    finally:
        conn.close()

