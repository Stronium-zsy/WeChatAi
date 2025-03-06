import sqlite3
from collections import defaultdict
import datetime
import json
from flask import Flask, request, jsonify
from flask_cors import CORS

# 数据库路径
feed_db_path = r"/decrypted/de_Sns.db"  # 替换为 Feed 数据库路径
contact_db_path = r"/decrypted/de_MicroMsg.db"  # 替换为 Contact 数据库路径

def build_user_connections(feed_db_path, contact_db_path):
    """
    从两个 SQLite 数据库中分别读取数据并合并，建立用户之间的连接及权重。
    """
    connections = defaultdict(int)
    user_info = {}

    try:
        # 计算三个月前的日期
        three_months_ago = (datetime.datetime.now() - datetime.timedelta(days=360)).timestamp()

        # 连接 Feed 数据库
        feed_conn = sqlite3.connect(feed_db_path)
        feed_cursor = feed_conn.cursor()

        # 从 FeedsV20 表中读取 FeedId 和 UserName
        feed_cursor.execute("SELECT FeedId, UserName FROM FeedsV20")
        feed_user_mapping = {row[0]: row[1] for row in feed_cursor.fetchall()}

        # 从 CommentV20 表中读取 FeedId、CommentType 和 FromUserName
        feed_cursor.execute("""
            SELECT FeedId, CommentType, FromUserName 
            FROM CommentV20 
            WHERE CreateTime >= ?
        """, (three_months_ago,))
        comments = feed_cursor.fetchall()

        for feed_id, comment_type, from_user_name in comments:
            if feed_id not in feed_user_mapping:
                continue

            # 获取 FeedId 对应的 UserName
            user_name = feed_user_mapping[feed_id]

            # 如果 UserName 和 FromUserName 不同，累加互动行为
            if user_name != from_user_name:
                # 确保连接是无向的：两者之间的互动都累加到同一条边上
                edge = tuple(sorted([user_name, from_user_name]))

                # 根据 CommentType 计算连接强度
                strength = 1 if comment_type == 1 else 3 if comment_type == 2 else 0
                connections[edge] += strength

        feed_conn.close()

        # 连接 Contact 数据库
        contact_conn = sqlite3.connect(contact_db_path)
        contact_cursor = contact_conn.cursor()

        # 查询联系人信息
        contact_cursor.execute("""
            SELECT UserName, 
                   CASE 
                       WHEN Remark IS NOT NULL AND Remark != '' THEN Remark 
                       ELSE NickName 
                   END AS DisplayName
            FROM Contact 
        """)
        user_info = {row[0]: row[1] for row in contact_cursor.fetchall()}

        contact_conn.close()

    except sqlite3.Error as e:
        print(f"数据库操作失败：{e}")

    return connections, user_info


def save_connections_to_file(connections, user_info, output_file):
    """
    保存连接数据到 JSON 文件，将元组键转换为字符串。
    """
    # 转换元组键为字符串
    serializable_connections = {
        json.dumps(key): value for key, value in connections.items()
    }

    data = {
        "connections": serializable_connections,
        "user_info": user_info
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)



