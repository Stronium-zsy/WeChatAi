# -*- coding: utf-8 -*-
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import requests
import base64
import threading
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from playwright.sync_api import Playwright, sync_playwright
from openai import OpenAI
from waitress import serve
import gc

app = Flask(__name__)
CORS(app)

# Configuration
CONFIG = {
    'OPENAI_API_KEY': 'sk-gthc9a05d8d2f5996d064f1dd9e033011033151e2c6rOzeD',
    'OPENAI_BASE_URL': 'https://api.gptsapi.net/v1/',
    'EMAIL_SENDER': '1263718132@qq.com',
    'EMAIL_PASSWORD': 'fhctyllxaeduiecg',
    'DEFAULT_PASSWORD': 'Bjtu@',
    'BROWSER_PATH': "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    'LOGIN_URL': "http://123.121.147.7:88/ve/Login_2.jsp",
    'LOGS_DIR': 'user_logs',  # Base directory for user logs
}

session_lock = threading.Lock()
JSESSIONID = 'EF547C67F7CBAA44D889F80D17AE6CA5'


def update_jsessionid(new_jsessionid):
    """Thread-safe method to update JSESSIONID."""
    global JSESSIONID
    with session_lock:
        JSESSIONID = new_jsessionid


def get_jsessionid():
    """Thread-safe method to get current JSESSIONID."""
    with session_lock:
        return JSESSIONID


# Load major student ranges from JSON file
with open('students.json', 'r', encoding='utf-8') as f:
    MAJOR_STUDENT_RANGES = json.load(f)

# Initialize OpenAI client
client = OpenAI(
    api_key=CONFIG['OPENAI_API_KEY'],
    base_url=CONFIG['OPENAI_BASE_URL'],
)


class UserLogger:
    """Custom logger class for managing per-user logging"""

    @staticmethod
    def get_logger(username: str) -> logging.Logger:
        """
        Creates or retrieves a logger for a specific user with daily rotation
        """
        logger = logging.getLogger(f"user_{username}")

        # Only add handlers if they don't exist
        if not logger.handlers:
            # Create user-specific directory
            user_log_dir = os.path.join(CONFIG['LOGS_DIR'], username)
            os.makedirs(user_log_dir, exist_ok=True)

            # Set up daily rotating file handler
            log_file = os.path.join(user_log_dir, f"{username}.log")
            file_handler = TimedRotatingFileHandler(
                log_file,
                when='midnight',
                interval=1,
                backupCount=30,  # Keep 30 days of logs
                encoding='utf-8'
            )

            # Create formatter with detailed information
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] - %(message)s\n'
                'Function: %(funcName)s - Line: %(lineno)d\n'
                'Additional Info: %(extra)s\n',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # Add stream handler for console output in development
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            logger.setLevel(logging.INFO)

        return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Custom adapter to add extra context to log messages"""

    def process(self, msg, kwargs):
        extra = kwargs.get('extra', {})
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs





class EmailService:
    @staticmethod
    def send_homework_notification(receiver: str, content: str) -> bool:
        try:
            msg = MIMEText(content, 'plain', 'utf-8')
            msg['From'] = f'Homework Notification <{CONFIG["EMAIL_SENDER"]}>'
            msg['To'] = f"{receiver}@bjtu.edu.cn"
            msg['Subject'] = 'Upcoming Homework Notification'

            with smtplib.SMTP_SSL('smtp.qq.com', 465) as smtp:
                smtp.login(CONFIG['EMAIL_SENDER'], CONFIG['EMAIL_PASSWORD'])
                smtp.sendmail(CONFIG['EMAIL_SENDER'], msg['To'], msg.as_string())
            return True
        except Exception as e:
            logging.error(f"Email sending failed: {e}")
            return False


class CaptchaRecognitionTool:
    @staticmethod
    def recognize_captcha(image_path: str) -> str:
        try:
            # 读取本地图片文件并转换为base64
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "识别此图片中的数字并给出结果，只返回结果"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_string}"}}
                    ]
                }],
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Captcha recognition failed: {e}")
            return ""


class HomeworkChecker:
    def __init__(self, username: str):
        self.username = username
        self.logger = self._setup_logger()

    def _setup_logger(self):
        base_logger = UserLogger.get_logger(self.username)
        return LoggerAdapter(base_logger, {'extra': {'username': self.username}})

    def check_homework(self, page, browser):
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            self.logger.info(f"Starting homework check", extra={'session': session_id})
            page.wait_for_load_state("networkidle")

            courses = page.locator(".courseItem").count()
            self.logger.info(f"Found {courses} courses", extra={'session': session_id})

            homeworks = []
            current_time = datetime.now()

            for i in range(courses):
                try:
                    with page.expect_popup() as page4_info:
                        page.locator(".courseItem").nth(i).click()

                    course_page = page4_info.value
                    course_name = course_page.locator("div.courseplatform-logo").text_content()

                    self.logger.info(f"Checking course: {course_name}",
                                     extra={'session': session_id, 'course_index': i})

                    # Navigate to homework section
                    course_page.get_by_text("课程考核", exact=True).click()
                    course_page.get_by_text("作业", exact=True).click()
                    course_page.wait_for_load_state("networkidle")

                    if course_page.get_by_text("暂无数据").is_visible():
                        self.logger.info(f"No homework found for course: {course_name}",
                                         extra={'session': session_id, 'course_index': i})
                        course_page.close()
                        continue

                    homework_count = course_page.locator("tbody#attendanceList").locator("tr").count()
                    self._process_course_homeworks(course_page, homework_count, course_name,
                                                   current_time, homeworks, session_id, i)
                    course_page.close()

                except Exception as e:
                    self.logger.error(f"Error processing course {i}: {str(e)}",
                                      extra={'session': session_id, 'error_type': type(e).__name__})

            if homeworks:
                self._send_homework_notification(homeworks, session_id)
                self.logger.info(f"Successfully processed {len(homeworks)} homework items",
                                 extra={'session': session_id})
            else:
                self.logger.info("No upcoming homework found", extra={'session': session_id})

            return "作业已提醒" if homeworks else "无待提醒作业"

        except Exception as e:
            self.logger.error(f"Critical error in homework check: {str(e)}",
                              extra={'session': session_id, 'error_type': type(e).__name__})
            return "检查作业失败"
        finally:
            self.logger.info("Completing homework check session",
                             extra={'session': session_id})
            browser.close()
            gc.collect()

    def _process_course_homeworks(self, page, homework_count, course_name, current_time,
                                  homeworks, session_id, course_index):
        for j in range(homework_count):
            try:
                row = page.locator("tbody#attendanceList").locator("tr").nth(j)

                if row.get_by_text("查看", exact=True).is_visible():
                    continue

                homework_name = row.locator("td").nth(0).text_content()
                deadline_cell = row.locator("td").nth(2)

                if not deadline_cell.is_visible() or deadline_cell.text_content() == '':
                    continue

                deadline_str = deadline_cell.text_content()
                deadline = datetime.strptime(deadline_str, "%Y-%m-%d %H:%M")

                if current_time < deadline <= current_time + timedelta(days=3):
                    homeworks.append({
                        "course_name": course_name,
                        "homework_name": homework_name,
                        "homework_deadline": deadline_str
                    })
                    self.logger.info(
                        f"Found upcoming homework: {homework_name} in {course_name}",
                        extra={
                            'session': session_id,
                            'course_index': course_index,
                            'homework_index': j,
                            'deadline': deadline_str
                        }
                    )

            except Exception as e:
                self.logger.error(
                    f"Error processing homework {j} in course {course_name}: {str(e)}",
                    extra={
                        'session': session_id,
                        'course_index': course_index,
                        'homework_index': j,
                        'error_type': type(e).__name__
                    }
                )

    def _send_homework_notification(self, homeworks, session_id):
        try:
            homework_text = "\n".join(
                f"{hw['course_name']}\n课程的 {hw['homework_name']}作业已临期三天\n"
                f"截止日期为：{hw['homework_deadline']}\n"
                for hw in homeworks
            )
            homework_text = f"同学您好，\n{homework_text}\n请注意提交\n如有疑问，请联系1263718132@qq.com"

            if EmailService.send_homework_notification(self.username, homework_text):
                self.logger.info("Successfully sent homework notification email",
                                 extra={'session': session_id, 'homework_count': len(homeworks)})
            else:
                self.logger.error("Failed to send homework notification email",
                                  extra={'session': session_id, 'homework_count': len(homeworks)})

        except Exception as e:
            self.logger.error(f"Error sending notification: {str(e)}",
                              extra={'session': session_id, 'error_type': type(e).__name__})


def handle_login(page, username, logger, max_attempts=10):
    for attempt in range(max_attempts):
        try:
            captcha = page.goto('http://123.121.147.7:88/ve/confirmImg').text()
            page.wait_for_load_state("networkidle")
            page.go_back()
            page.get_by_placeholder("请输入工号/学号").fill(username)
            page.get_by_placeholder("请输入密码").fill(CONFIG['DEFAULT_PASSWORD']+username)
            page.locator("img[src^='GetImg']").screenshot(path=f"./captcha_images/{username}_captcha.png")
            page.get_by_placeholder("请输入验证码").fill(captcha)
            page.get_by_role("button", name="登录").click()
            page.wait_for_load_state("networkidle")

            if page.locator('text=个人信息').is_visible():
                logger.info(f"Login successful for user {username}")
                update_jsessionid(page.context.cookies()[0]['value'])
                return True

            logger.warning(f"Login attempt {attempt + 1} failed for user {username}")

        except Exception as e:
            logger.error(f"Login error on attempt {attempt + 1}: {e}")

    return False


def run_homework_check(username: str) -> str:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=CONFIG['BROWSER_PATH']
        )
        context = browser.new_context()
        page = context.new_page()

        checker = HomeworkChecker(username)

        try:
            page.goto(CONFIG['LOGIN_URL'])
            if not handle_login(page, username, checker.logger):
                return "登录失败"

            return checker.check_homework(page, browser)

        except Exception as e:
            checker.logger.error(f"Error in homework check: {e}")
            return "检查失败"


def add_user_to_scheduler(scheduler: BackgroundScheduler, username: str, trigger_time: timedelta):
    """Add a user's homework check job to the scheduler"""
    if not scheduler.get_job(f"homework_checker_{username}"):
        scheduler.add_job(
            lambda: run_homework_check(username),
            'interval',
            hours=48,
            start_date=datetime.now() + trigger_time,
            max_instances=2,
            misfire_grace_time=60,
            id=f"homework_checker_{username}",
            coalesce=True
        )
        logging.info(f"Added homework check job for user: {username}")


def main():
    # Create base logs directory
    os.makedirs(CONFIG['LOGS_DIR'], exist_ok=True)

    # Set up global logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Initialize and start the scheduler
    scheduler = BackgroundScheduler()
    scheduler.start()

    # Add all users to the scheduler, distributing tasks evenly across 24 hours
    total_students = sum(
        range_info['end_id'] - range_info['start_id'] + 1 for range_info in MAJOR_STUDENT_RANGES.values())
    time_interval = timedelta(hours=48 / total_students)
    current_interval = timedelta(seconds=0)

    for major, range_info in MAJOR_STUDENT_RANGES.items():
        for user_id in range(range_info['start_id'], range_info['end_id'] + 1):
            username = str(user_id)
            add_user_to_scheduler(scheduler, username, current_interval)
            current_interval += time_interval

    # Start the Flask server
    serve(app, host='0.0.0.0', port=5000)


if __name__ == "__main__":
    main()
