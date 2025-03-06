import sqlite3
import datetime


def get_connection(db_path: str):
    """
    获取数据库连接
    """
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 数据库连接失败：{e}")
        return None


def fetch_messages_between_time(conn, start_time, end_time):
    """
    查询指定时间范围内的消息
    """
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM MSG WHERE CreateTime BETWEEN ? AND ? AND Type = 1"
        cursor.execute(query, (int(start_time), int(end_time)))
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        return results, columns
    except sqlite3.Error as e:
        print(f"[{datetime.datetime.now()}] 查询消息时出错：{e}")
        return [], []


def fetch_count_messages_by_talker_and_time(conn, str_talker, time_length):
    """
    根据 StrTalker 和 event_time 查询消息数据
    Args:
        conn: 数据库连接对象
        str_talker: 消息的发送方或接收方标识
        event_time: 查询的结束时间（时间戳，单位：秒）

    Returns:
        (results, columns): 查询到的消息记录列表和字段名称列表
        :param conn:
        :param str_talker:
        :param time_length:
    """
    try:

        end_time = datetime.datetime.now().timestamp()
        start_time = end_time - time_length

        # 构造 SQL 查询
        query = """
            SELECT COUNT(*) FROM MSG
            WHERE StrTalker = ? AND CreateTime BETWEEN ? AND ? AND Type = 1
        """

        # 执行查询
        cursor = conn.cursor()
        cursor.execute(query, (str_talker, start_time, end_time))

        # 获取查询结果
        results = cursor.fetchall()
        return results
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 查询消息时出错：{e}")
        return []


def fetch_messages_by_talker_and_time(conn, str_talker, event_time):
    """
    根据 StrTalker 和 event_time 查询消息数据
    Args:
        conn: 数据库连接对象
        str_talker: 消息的发送方或接收方标识
        event_time: 查询的结束时间（时间戳，单位：秒）

    Returns:
        (results, columns): 查询到的消息记录列表和字段名称列表
    """
    try:
        # 计算时间范围
        start_time = int(event_time) - 6 * 60 * 60  # 6 小时前
        end_time = int(event_time)  # 结束时间

        # 构造 SQL 查询
        query = """
            SELECT IsSender,StrContent
            FROM MSG
            WHERE StrTalker = ? AND CreateTime BETWEEN ? AND ? AND Type = 1
        """

        # 执行查询
        cursor = conn.cursor()
        cursor.execute(query, (str_talker, start_time, end_time))

        # 获取查询结果
        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        # 返回结果和字段名称
        return results, columns

    except ValueError as ve:
        print(f"[{datetime.now()}] 参数错误：{ve}")
        return [], []
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 数据库查询错误：{e}")
        return [], []
    finally:
        # 可选：如果函数内管理连接，确保关闭
        # conn.close()
        pass


def fetch_contact_info(conn, user_name):
    """
    查询联系人信息
    """
    try:
        cursor = conn.cursor()
        query = """
            SELECT UserName, 
                   CASE 
                       WHEN Remark IS NOT NULL AND Remark != '' THEN Remark 
                       ELSE NickName 
                   END AS DisplayName
            FROM Contact
            WHERE UserName = ?
        """
        cursor.execute(query, (user_name,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(f"[{datetime.now()}] 查询联系人信息时出错：{e}")
        return None
