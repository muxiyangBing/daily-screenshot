import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from playwright.sync_api import sync_playwright
from datetime import datetime

# 目标网址，改成你想要的
TARGET_URL = "https://news.ycombinator.com"

def take_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(TARGET_URL)
        page.wait_for_load_state("networkidle")
        img_bytes = page.screenshot(full_page=True)
        browser.close()
        return img_bytes

def send_email(img_bytes):
    sender = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.qq.com")
    port = int(os.environ.get("SMTP_PORT", 465))

    msg = MIMEMultipart("related")
    msg["Subject"] = f"每日截图 - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = sender
    msg["To"] = sender  # 发给自己的邮箱

    img = MIMEImage(img_bytes, _subtype="png")
    img.add_header("Content-ID", "<daily_screenshot>")
    msg.attach(img)

    with smtplib.SMTP_SSL(smtp_server, port) as server:
        server.login(sender, password)
        server.sendmail(sender, sender, msg.as_string())

if __name__ == "__main__":
    img = take_screenshot()
    send_email(img)
    print("截图并发送完成！")
