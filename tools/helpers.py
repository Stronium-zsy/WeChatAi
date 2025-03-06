import hashlib
import math
import os
import json
import subprocess
from datetime import datetime
import numpy as np


from persistance.events_database_api import get_all_emotions
from sklearn.cluster import KMeans

# 配置参数
wxdump_command = r"E:\wxdump\wxdump.exe decrypt"
key = "f3cc986c726d45aea8c96fae29f46c27da51b64497e94408b624ab77a0031b33"
input_dir = r"C:\Users\86133\Documents\WeChat Files\wxid_9xkfenvtiujd22\Msg"
decrypted_db = r"E:\PycharmProjects\WechatAi\decrypted\Multi"
task_status_file = "status/task_status.json"
import random
import requests
import urllib.parse


def translate_text(text, from_lang='zh', to_lang='en'):
    appid = '20250203002264464'  # 你的 APP ID
    key = 'ymNol_72tuWdUU2wxnxO'  # 你的密钥
    salt = str(random.randint(32768, 65536))  # 生成随机数作为 salt
    sign = generate_sign(appid, text, salt, key)  # 计算签名

    # 构造翻译 API 的请求 URL
    base_url = 'http://api.fanyi.baidu.com/api/trans/vip/translate'
    url = f"{base_url}?q={urllib.parse.quote(text)}&from={from_lang}&to={to_lang}&appid={appid}&salt={salt}&sign={sign}"

    try:
        # 发送请求
        response = requests.get(url)
        result = response.json()

        if 'error_code' in result:
            print(f"翻译失败: {result['error_msg']}")
            return None
        return result['trans_result'][0]['dst']  # 返回翻译结果

    except Exception as e:
        print(f"请求失败: {e}")
        return None


def generate_sign(appid, text, salt, key):
    # 签名计算方法：appid + q + salt + key，然后进行 MD5 加密
    sign_str = appid + text + salt + key
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()


def convert_to_timestamp(event_time):
    """
    将 YYYY-MM-DD HH:MM:SS 格式的时间字符串转换为时间戳
    """
    try:
        # 尝试将字符串转为时间戳
        dt = datetime.strptime(event_time, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp())
    except ValueError:
        # 无法转换，直接返回
        raise ValueError("event_time 必须是时间戳或 YYYY-MM-DD HH:MM:SS 格式的时间字符串")


def calculate_avg_emotions(group):
    """
    计算每组的平均情绪值。
    :param group: 当前组的情绪数据
    :return: 平均情绪值
    """
    return {
        "neutral": np.mean([e['neutral'] for e in group]),
        "joy": np.mean([e['joy'] for e in group]),
        "surprise": np.mean([e['surprise'] for e in group]),
        "anger": np.mean([e['anger'] for e in group]),
        "sadness": np.mean([e['sadness'] for e in group]),
        "disgust": np.mean([e['disgust'] for e in group]),
        "fear": np.mean([e['fear'] for e in group]),
        "timestamp": np.mean([e['timestamp'] for e in group])  # 使用该簇的平均时间戳作为时间
    }


def group_by_time_interval(timestamps, time_threshold_seconds=600):
    """
    根据时间间隔对时间戳进行分组。
    :param timestamps: 一个包含时间戳的数组
    :param time_threshold_seconds: 时间间隔阈值（单位：秒）
    :return: 分组后的时间戳组
    """
    grouped = []
    current_group = []
    group_start_time = timestamps[0]  # 第一个时间戳，作为当前组的开始时间

    for ts in timestamps:
        # 获取当前时间戳与当前组开始时间的差值（单位：秒）
        time_diff = ts - group_start_time

        # 判断是否在阈值时间范围内，若在范围内，则继续加入当前组
        if time_diff <= time_threshold_seconds:
            current_group.append(ts)
        else:
            # 否则，保存当前组，并重新开始一个新的组
            if current_group:
                grouped.append(current_group)

            current_group = [ts]
            group_start_time = ts  # 更新当前组的开始时间

    # 最后一个组处理
    if current_group:
        grouped.append(current_group)

    return grouped


def group_emotions_by_time_interval(emotions, time_threshold_seconds=600):
    """
    根据时间间隔对情绪数据进行分组，并计算每组的情绪平均值。
    :param emotions: 包含情绪数据的数组，每个元素有一个 timestamp 属性
    :param time_threshold_seconds: 时间间隔阈值（单位：秒），小于该时间差的聊天视为同一组
    :return: 每个时间段（组）的情绪平均值
    """
    # 按照时间戳将情绪数据排序
    emotions.sort(key=lambda x: x['timestamp'])

    # 提取时间戳
    timestamps = [e['timestamp'] for e in emotions]

    # 使用group_by_time_interval来获取分组后的时间戳
    time_groups = group_by_time_interval(timestamps, time_threshold_seconds)

    # 根据时间戳的分组来创建每组的情绪数据
    grouped_emotions = []

    for group in time_groups:
        # 获取当前组内的情绪数据
        group_emotions = [e for e in emotions if e['timestamp'] in group]

        # 计算该组的平均情绪并保存
        avg_emotions = calculate_avg_emotions(group_emotions)
        grouped_emotions.append(avg_emotions)

    return grouped_emotions


def get_emotions_for_period(wechat_id, time_length):
    # 获取数据库中的情感数据
    emotions = get_all_emotions(wechat_id, time_length)

    if not emotions:
        return None

    # 根据指定时间段对情绪进行分组和计算平均值
    grouped_emotions = group_emotions_by_time_interval(emotions=emotions)

    # 限制返回最多 50 个点
    return grouped_emotions


def decrypt_database():
    from persistance.build_events_database_api import create_index_on_msg
    """
    使用 wxdump 解密数据库。
    Returns:
        bool: 解密是否成功。
    """
    command = f'{wxdump_command} -k "{key}" -i "{input_dir}"'
    try:
        print(f"[{datetime.now()}] 正在执行命令：{command}")
        subprocess.run(command, shell=True, check=True)
        print(f"[{datetime.now()}] 数据库解密完成。")
        create_index_on_msg()
        print(f"[{datetime.now()}] 创建索引完成。")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] 数据库解密失败：{e}")
        return False


def find_latest_database():
    """
    查找最新的解密数据库文件。
    Returns:
        str: 最新数据库文件的路径，或 None 如果未找到。
    """
    try:
        db_files = [f for f in os.listdir(decrypted_db) if f.startswith("de_MSG") and f.endswith(".db")]
        if not db_files:
            print(f"[{datetime.now()}] 未找到任何数据库文件。")
            return None

        db_files.sort(key=lambda x: int(x.split("_MSG")[1].split(".db")[0]), reverse=True)
        latest_db = db_files[0]
        return os.path.join(decrypted_db, latest_db)
    except Exception as e:
        print(f"[{datetime.now()}] 查找最新数据库文件时出错：{e}")
        return None


def calculate_chat_temperature_log(message_count):
    """
    根据消息数量计算聊天温度（对数缩放方式）。

    参数:
        message_count (int): 消息总数

    返回:
        int: 聊天温度，范围在 0 到 100 之间
    """
    if message_count <= 0:
        return 0

    # 调整参数，确保温度在 0 到 100 之间
    max_message_count = 5000  # 假设最大5000条达到满温度
    scaled_value = min(message_count, max_message_count)

    # 计算对数缩放
    temperature = (math.log(scaled_value + 1) / math.log(max_message_count + 1)) * 500
    return round(temperature)


def save_task_status(last_run_time):
    """
    将任务状态保存到 JSON 文件。
    Args:
        last_run_time (float): 上次任务运行时间戳。
    """
    try:
        with open(task_status_file, "w") as f:
            json.dump({"last_run_time": last_run_time}, f)
    except Exception as e:
        print(f"[{datetime.now()}] 保存任务状态失败：{e}")


def read_task_status():
    """
    读取任务状态。
    Returns:
        dict: 包含上次任务运行时间的字典，或 None 如果任务状态不可用。
    """
    if not os.path.exists(task_status_file):
        return None

    try:
        with open(task_status_file, "r") as f:
            task_status = json.load(f)
            if "last_run_time" in task_status and isinstance(task_status["last_run_time"], (int, float)):
                return task_status
            else:
                print(f"[{datetime.now()}] 任务状态文件格式错误：{task_status}")
                return None
    except Exception as e:
        print(f"[{datetime.now()}] 读取任务状态失败：{e}")
        return None
