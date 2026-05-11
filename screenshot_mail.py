import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone, timedelta
import sys

REPORT_URL = os.environ["REPORT_URL"]
USERNAME   = os.environ["FR_USERNAME"]
PASSWORD   = os.environ["FR_PASSWORD"]

def get_beijing_time():
    """获取当前北京时间"""
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz)

def take_screenshot():
    now = get_beijing_time()
    end_date_str = now.strftime('%Y-%m-%d')          # 例如 2026-05-11
    start_date_str = (now - timedelta(days=10)).strftime('%Y-%m-%d')  # 例如 2026-05-01

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(REPORT_URL)
        page.wait_for_load_state("networkidle")

        # 1. 登录
        try:
            page.wait_for_selector('input[placeholder="用户名"]', timeout=10000)
            page.fill('input[placeholder="用户名"]', USERNAME)
            page.fill('input[placeholder="密码"]', PASSWORD)
            page.click('div.login-button')
            page.wait_for_load_state("networkidle")
            print("登录成功")
        except Exception as e:
            print(f"登录过程异常（可能已保持登录态）: {e}")

        page.wait_for_timeout(2000)

        # 2. 用键盘模拟输入修改开始日期和结束日期
        #    定位开始日期的输入区域（div.sign-editor-text）
        start_locator = page.locator(
            'div.report-main-parameter-container-controller-label:has-text("开始日期") '
            '+ div.report-main-parameter-container-controller-datetime '
            'div.sign-editor-text'
        )
        end_locator = page.locator(
            'div.report-main-parameter-container-controller-label:has-text("结束日期") '
            '+ div.report-main-parameter-container-controller-datetime '
            'div.sign-editor-text'
        )

        try:
            # 修改开始日期
            start_locator.click()
            page.keyboard.press('Control+A')   # 全选
            page.keyboard.type(start_date_str)
            page.keyboard.press('Enter')       # 确认输入
            page.wait_for_timeout(500)         # 稍等控件反应
            print(f"开始日期已输入: {start_date_str}")
        except Exception as e:
            print(f"修改开始日期失败: {e}")

        try:
            # 修改结束日期
            end_locator.click()
            page.keyboard.press('Control+A')
            page.keyboard.type(end_date_str)
            page.keyboard.press('Enter')
            page.wait_for_timeout(500)
            print(f"结束日期已输入: {end_date_str}")
        except Exception as e:
            print(f"修改结束日期失败: {e}")

        # 3. 点击查询按钮
        try:
            page.click('#fr-btn-SEARCH')
            page.wait_for_load_state("networkidle")
            print("已点击查询按钮")
        except Exception as e:
            print(f"点击查询按钮失败: {e}")

        # 4. 等待数据加载完成（遮罩 + 总计行）
        try:
            page.wait_for_selector('.loading-mask', state='hidden', timeout=20000)
            print("加载遮罩已消失")
        except Exception:
            print("未检测到加载遮罩，或等待超时")

        try:
            page.wait_for_selector('div[heavytd="light"]:has-text("总计")', timeout=30000)
            print("检测到总计行，数据加载完成")
        except Exception:
            print("等待总计行超时，继续截图")

        page.wait_for_timeout(2000)

        img_bytes = page.screenshot(full_page=True)
        browser.close()
        return img_bytes

def send_email(img_bytes):
    sender = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_PASSWORD"]
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 465))

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"每日报表截图 - {get_beijing_time().strftime('%Y-%m-%d')}"
    msg["From"] = sender
    msg["To"] = sender

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
