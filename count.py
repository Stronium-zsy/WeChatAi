# -*- coding: utf-8 -*-

import json
import os
import threading
from datetime import datetime
from playwright.sync_api import sync_playwright

CONFIG = {
    'BROWSER_PATH': "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    'LOGIN_URL': "http://123.121.147.7:88/ve/Login_2.jsp",
    'DEFAULT_PASSWORD': 'Bjtu@',
    'LOGS_DIR': 'user_logs',  # 用于保存日志和统计结果的目录
}
JSESSIONID = 'EF547C67F7CBAA44D889F80D17AE6CA5'
session_lock = threading.Lock()
def update_jsessionid(new_jsessionid):
    """Thread-safe method to update JSESSIONID."""
    global JSESSIONID
    with session_lock:
        JSESSIONID = new_jsessionid


def get_jsessionid():
    """Thread-safe method to get current JSESSIONID."""
    with session_lock:
        return JSESSIONID
# 全部学号范围
STUDENT_RANGES = {
"30": {
        "start_id": 24261001,
        "end_id": 24261128
    },
    "8": {
        "start_id": 23261001,
        "end_id": 23261133
    },
    "17": {
        "start_id": 24271001,
        "end_id": 24271113
    },
    "9": {
        "start_id": 23271001,
        "end_id": 23271115
    },
    "18": {
        "start_id": 24281001,
        "end_id": 24281313
    },
    "10": {
        "start_id": 23281001,
        "end_id": 23281329
    },
    "19": {
        "start_id": 24291001,
        "end_id": 24291321
    },
    "11": {
        "start_id": 23291001,
        "end_id": 23291329
    },
    "21": {
        "start_id": 24311001,
        "end_id": 24311065
    },
    "20": {
        "start_id": 24301000,
        "end_id": 24301180
    },
    "22": {
        "start_id": 24321001,
        "end_id": 24321091
    },
    "23": {
        "start_id": 24331001,
        "end_id": 24331201
    },
    "24": {
        "start_id": 24341001,
        "end_id": 24341153
    },
    "12": {
        "start_id": 23301001,
        "end_id": 23301175
    },
    "13": {
        "start_id": 23311001,
        "end_id": 23311058
    },
    "14": {
        "start_id": 23321001,
        "end_id": 23321080
    },
    "15": {
        "start_id": 23331001,
        "end_id": 23331201
    },
    "16": {
        "start_id": 23341001,
        "end_id": 23341155
    },
    "25": {
        "start_id": 24211001,
        "end_id": 24211439
    },
    "26": {
        "start_id": 24221001,
        "end_id": 24221346
    },
    "4": {
        "start_id": 23221001,
        "end_id": 23221300
    },
    "27": {
        "start_id": 24231001,
        "end_id": 24231306
    },
    "5": {
        "start_id": 23231001,
        "end_id": 23231279
    },
    "28": {
        "start_id": 24241001,
        "end_id": 24241283
    },
    "6": {
        "start_id": 23241001,
        "end_id": 23241274
    },
    "29": {
        "start_id": 24251001,
        "end_id": 24251348
    },
    "7": {
        "start_id": 23251001,
        "end_id": 23251362
    },

    # ... 添加其余学号范围
}

def generate_usernames() -> list:
    """
    根据学号范围生成所有用户名列表。
    """
    usernames = []
    for grade, range_info in STUDENT_RANGES.items():
        start_id = range_info["start_id"]
        end_id = range_info["end_id"]
        usernames.extend([str(i) for i in range(start_id, end_id + 1)])
    return usernames

def check_user_homework(username: str) -> int:
    """
    检查用户的所有课程，统计未提交作业的数量。
    """
    unsubmitted_count = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=CONFIG['BROWSER_PATH']
        )
        context = browser.new_context()
        page = context.new_page()

        try:
            # 登录
            page.goto(CONFIG['LOGIN_URL'])
            captcha = page.goto('http://123.121.147.7:88/ve/confirmImg').text()
            page.go_back()
            page.get_by_placeholder("请输入工号/学号").fill(username)
            page.get_by_placeholder("请输入密码").fill(CONFIG['DEFAULT_PASSWORD'] + username)
            page.get_by_placeholder("请输入验证码").fill(captcha)
            page.get_by_role("button", name="登录").click()
            page.wait_for_load_state("networkidle")

            if not page.locator('text=个人信息').is_visible():
                print(f"用户 {username} 登录失败")
                return -1

            # 检查作业
            courses = page.locator(".courseItem").count()
            for i in range(courses):
                with page.expect_popup() as course_popup:
                    page.locator(".courseItem").nth(i).click()
                course_page = course_popup.value

                # 导航到作业页面
                try:
                    course_page.get_by_text("课程考核", exact=True).click()
                    course_page.get_by_text("作业", exact=True).click()
                    course_page.wait_for_load_state("networkidle")

                    # 检查作业
                    rows = course_page.locator("tbody#attendanceList").locator("tr")
                    for j in range(rows.count()):
                        row = rows.nth(j)
                        if row.get_by_text("查看", exact=True).is_visible():
                            unsubmitted_count += 1  # 未提交作业计数

                    course_page.close()
                except Exception as e:
                    print(f"检查课程失败：{e}")

        except Exception as e:
            print(f"用户 {username} 检查作业失败：{e}")
        finally:
            browser.close()

    return unsubmitted_count

def save_unsubmitted_count(username: str, unsubmitted_count: int):
    """
    保存未提交作业统计到 JSON 文件。
    """
    file_path = os.path.join(CONFIG['LOGS_DIR'], "unsubmitted_counts.json")
    os.makedirs(CONFIG['LOGS_DIR'], exist_ok=True)

    # 加载现有数据
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    # 更新数据
    data[username] = unsubmitted_count

    # 保存到文件
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    # 生成所有用户名
    usernames = generate_usernames()

    for username in usernames:
        print(f"开始检查用户 {username} 的作业情况...")
        unsubmitted_count = check_user_homework(username)
        if unsubmitted_count >= 0:  # -1 表示登录失败
            print(f"用户 {username} 未提交作业次数：{unsubmitted_count}")
            save_unsubmitted_count(username, unsubmitted_count)
        else:
            print(f"跳过用户 {username}，登录失败。")

    print("检查完成，结果已保存。")

if __name__ == "__main__":
    main()
