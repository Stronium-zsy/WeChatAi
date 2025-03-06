import sqlite3
from tools.helpers import find_latest_database

def create_index_on_msg():
    """
    Creates an index on the MSG table in the latest found database.
    """
    try:
        conn = find_latest_database()  # 获取最新的数据库连接
        cursor = conn.cursor()

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_msg_strtalker ON MSG(StrTalker);')

        conn.commit()
        conn.close()
        print("Index 'idx_msg_strtalker' created successfully.")
    except sqlite3.Error as e:
        print(f"Error while creating index: {e}")

def transfer_and_create_index(source_db_path, target_db_path):
    """
    Transfers contact data from source database to target database.

    Args:
        source_db_path (str): Path to the source database.
        target_db_path (str): Path to the target database.
    """
    query = """
        SELECT 
            c.UserName AS wechat_id, 
            c.Alias AS alias, 
            c.remark AS remark, 
            c.NickName AS friend_name, 
            h.smallHeadImgUrl AS headImgUrl
        FROM Contact AS c
        LEFT JOIN ContactHeadImgUrl AS h ON c.UserName = h.usrName
        WHERE c.reserved1 = 1 AND c.reserved2 = 1;
    """

    try:
        # 连接源数据库
        source_conn = sqlite3.connect(source_db_path)
        source_cursor = source_conn.cursor()

        # 执行查询
        source_cursor.execute(query)
        results = source_cursor.fetchall()

        # 连接目标数据库
        target_conn = sqlite3.connect(target_db_path)
        target_cursor = target_conn.cursor()

        # 创建 friends 表（如果不存在）
        target_cursor.execute("""
            CREATE TABLE IF NOT EXISTS friends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wechat_id TEXT NOT NULL,
                alias TEXT,
                remark TEXT,
                friend_name TEXT,
                headImgUrl TEXT
            );
        """)

        # 预处理数据
        cleaned_results = [(wechat_id, alias, remark, friend_name, headImgUrl if headImgUrl else '')
                           for (wechat_id, alias, remark, friend_name, headImgUrl) in results]

        # 插入数据
        insert_query = """
            INSERT INTO friends (wechat_id, alias, remark, friend_name, headImgUrl) 
            VALUES (?, ?, ?, ?, ?);
        """
        target_cursor.executemany(insert_query, cleaned_results)

        # 提交事务
        target_conn.commit()
        print(f"Successfully inserted {len(results)} records into 'friends' table.")

        # 调用独立的创建索引函数
        create_index_on_msg()

    except sqlite3.Error as e:
        print(f"Database error: {e}")

    finally:
        # 关闭数据库连接
        if source_conn:
            source_conn.close()
        if target_conn:
            target_conn.close()
