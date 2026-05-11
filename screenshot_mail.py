import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from playwright.sync_api import sync_playwright
from datetime import datetime
import sys

# ── 配置从环境变量读取 ──
REPORT_URL = os.environ["REPORT_URL"]
USERNAME   = os.environ["FR_USERNAME"]
PASSWORD   = os.environ["FR_PASSWORD"]

def take_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. 访问报表地址（通常会自动跳转到登录页）
        page.goto(REPORT_URL)
        page.wait_for_load_state("networkidle")

        # 2. 登录表单：请根据实际页面调整选择器
        #    常见 FineReport 登录页：
        #    用户名字段: input[name="username"] 或 input[placeholder*="用户名"]
        #    密码字段:   input[name="password"] 或 input[type="password"]
        #    登录按钮:   button[type="submit"] 或 button:has-text("登录")
        #
        #    ⚠️ 下面的选择器是通用猜测，若无效请按注释修改
        try:
            page.wait_for_selector('input[name="username"]', timeout=10000)
            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')
            # 等待登录完成并跳转回报表
            page.wait_for_load_state("networkidle")
        except Exception as e:
            # 可能已经登录或页面无登录表单，继续往下
            print(f"登录流程异常（可能已登录）: {e}")

        # 3. 等待报表数据加载完成
        #    方案A：等待报表内容容器出现（需要你根据实际替换选择器）
        #    方案B：直接等待固定秒数，比如10秒
        #    下面使用等待固定时间，如果数据加载慢可调大
        page.wait_for_timeout(10000)  # 等待10秒，确保动态数据渲染完毕

        # 4. 截图
        img_bytes = page.screenshot(full_page=True)
        browser.close()
        return img_bytes

def send_email(img_bytes):
    sender = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 465))

    msg = MIMEMultipart("related")
    msg["Subject"] = f"每日报表截图 - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = sender
    msg["To"] = sender

    img = MIMEImage(img_bytes, _subtype="png")
    img.add_header("Content-ID", "<daily_report>")
    msg.attach(img)

    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(sender, password)
        server.sendmail(sender, sender, msg.as_string())

if __name__ == "__main__":
    try:
        img = take_screenshot()
        send_email(img)
        print("截图并发送完成")
    except Exception as e:
        print(f"运行失败: {e}", file=sys.stderr)
        raise
