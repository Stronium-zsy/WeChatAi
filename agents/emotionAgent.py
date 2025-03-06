from datetime import datetime

from tools.helpers import translate_text


def calculate_emotions_single_chat(chat_records, message_times):
    from tools.emotionBertClient import EmoBERTaClient

    # 打印调试信息：chat_records 和 message_times 的长度

    # 创建 EmoBERTa 客户端实例
    client = EmoBERTaClient(url_emoberta="http://47.121.209.197:3001/")

    # 存储每条消息的情绪
    individual_emotions = []

    for i, chat in enumerate(chat_records):
        try:
            chat = translate_text(chat)
            # 获取每条消息的情绪
            result = client.run_text(chat)  # 获取情绪分析结果

            # 获取该消息的情绪得分
            avg_emotions = {
                "neutral": result.get("neutral", 0),
                "joy": result.get("joy", 0),
                "surprise": result.get("surprise", 0),
                "anger": result.get("anger", 0),
                "sadness": result.get("sadness", 0),
                "disgust": result.get("disgust", 0),
                "fear": result.get("fear", 0),
                "timestamp": message_times[i]  # 添加时间戳
            }

            # 将计算好的情绪添加到列表中
            individual_emotions.append(avg_emotions)

        except Exception as e:
            # 捕获异常并打印错误信息，继续处理下一个消息
            print(f"[{datetime.now()}]:{e}")

    return individual_emotions


def calculate_emotions_grouped_chat(group):
    print(group)
    from tools.emotionBertClient import EmoBERTaClient
    from datetime import datetime

    # 创建 EmoBERTa 客户端实例
    client = EmoBERTaClient(url_emoberta="http://47.121.209.197:3001/")

    try:
        # 提取该组聊天记录的内容，拼接成一段完整的聊天文本
        translated_chat = "\n".join([translate_text(record["chat_record"]) for record in group])
        # 调用情感分析模型，获取情绪得分
        result = client.run_text(translated_chat)
        # 计算情绪分布
        avg_emotions = {
            "neutral": result.get("neutral", 0),
            "joy": result.get("joy", 0),
            "surprise": result.get("surprise", 0),
            "anger": result.get("anger", 0),
            "sadness": result.get("sadness", 0),
            "disgust": result.get("disgust", 0),
            "fear": result.get("fear", 0),
            "timestamp": group[0]["timestamp"]  # 取该组的第一个时间戳作为该组的时间
        }
        return avg_emotions
    except Exception as e:
        # 捕获异常并打印错误信息
        print(f"[{datetime.now()}] Error: {e}")
        return None

