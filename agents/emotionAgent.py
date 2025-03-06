from datetime import datetime

from tools.helpers import translate_text


def calculate_emotions_single_chat(chat_records, message_times):
    from tools.emotionBertClient import EmoBERTaClient

    # ��ӡ������Ϣ��chat_records �� message_times �ĳ���

    # ���� EmoBERTa �ͻ���ʵ��
    client = EmoBERTaClient(url_emoberta="http://47.121.209.197:3001/")

    # �洢ÿ����Ϣ������
    individual_emotions = []

    for i, chat in enumerate(chat_records):
        try:
            chat = translate_text(chat)
            # ��ȡÿ����Ϣ������
            result = client.run_text(chat)  # ��ȡ�����������

            # ��ȡ����Ϣ�������÷�
            avg_emotions = {
                "neutral": result.get("neutral", 0),
                "joy": result.get("joy", 0),
                "surprise": result.get("surprise", 0),
                "anger": result.get("anger", 0),
                "sadness": result.get("sadness", 0),
                "disgust": result.get("disgust", 0),
                "fear": result.get("fear", 0),
                "timestamp": message_times[i]  # ���ʱ���
            }

            # ������õ�������ӵ��б���
            individual_emotions.append(avg_emotions)

        except Exception as e:
            # �����쳣����ӡ������Ϣ������������һ����Ϣ
            print(f"[{datetime.now()}]:{e}")

    return individual_emotions


def calculate_emotions_grouped_chat(group):
    print(group)
    from tools.emotionBertClient import EmoBERTaClient
    from datetime import datetime

    # ���� EmoBERTa �ͻ���ʵ��
    client = EmoBERTaClient(url_emoberta="http://47.121.209.197:3001/")

    try:
        # ��ȡ���������¼�����ݣ�ƴ�ӳ�һ�������������ı�
        translated_chat = "\n".join([translate_text(record["chat_record"]) for record in group])
        # ������з���ģ�ͣ���ȡ�����÷�
        result = client.run_text(translated_chat)
        # ���������ֲ�
        avg_emotions = {
            "neutral": result.get("neutral", 0),
            "joy": result.get("joy", 0),
            "surprise": result.get("surprise", 0),
            "anger": result.get("anger", 0),
            "sadness": result.get("sadness", 0),
            "disgust": result.get("disgust", 0),
            "fear": result.get("fear", 0),
            "timestamp": group[0]["timestamp"]  # ȡ����ĵ�һ��ʱ�����Ϊ�����ʱ��
        }
        return avg_emotions
    except Exception as e:
        # �����쳣����ӡ������Ϣ
        print(f"[{datetime.now()}] Error: {e}")
        return None

