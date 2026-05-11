import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from playwright.sync_api import sync_playwright
from datetime import datetime
import sys

REPORT_URL = os.environ["REPORT_URL"]
USERNAME   = os.environ["FR_USERNAME"]
PASSWORD   = os.environ["FR_PASSWORD"]

def take_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(REPORT_URL)
        page.wait_for_load_state("networkidle")

        # --- 登录 ---
        try:
            page.wait_for_selector('input[placeholder="用户名"]', timeout=10000)
            page.fill('input[placeholder="用户名"]', USERNAME)
            page.fill('input[placeholder="密码"]', PASSWORD)
            page.click('div.login-button')
            page.wait_for_load_state("networkidle")
        except Exception as e:
            print(f"登录过程异常（可能已保持登录态）: {e}")

        # --- 等待报表数据加载 ---
        page.wait_for_timeout(10000)

        img_bytes = page.screenshot(full_page=True)
        browser.close()
        return img_bytes

def send_email(img_bytes):
    sender = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 465))

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"每日报表截图 - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = sender
    msg["To"] = sender

    # 构建图片附件，指定文件名
    part = MIMEBase("application", "octet-stream")
    part.set_payload(img_bytes)
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        "attachment; filename=report_screenshot.png",
    )
    msg.attach(part)

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
