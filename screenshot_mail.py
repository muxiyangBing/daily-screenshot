import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone, timedelta
import sys

# 从 GitHub Secrets 读取敏感配置
REPORT_URL = os.environ["REPORT_URL"]
USERNAME   = os.environ["FR_USERNAME"]
PASSWORD   = os.environ["FR_PASSWORD"]

def get_beijing_time():
    """获取当前北京时间"""
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz)

def take_screenshot():
    # 计算北京时间的今天和10天前
    now = get_beijing_time()
    end_date_str = now.strftime('%Y-%m-%d')          # 例如 2026-05-11
    start_date_str = (now - timedelta(days=10)).strftime('%Y-%m-%d')  # 例如 2026-05-01

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. 打开报表页面
        page.goto(REPORT_URL)
        page.wait_for_load_state("networkidle")

        # 2. 登录
        try:
            page.wait_for_selector('input[placeholder="用户名"]', timeout=10000)
            page.fill('input[placeholder="用户名"]', USERNAME)
            page.fill('input[placeholder="密码"]', PASSWORD)
            page.click('div.login-button')
            page.wait_for_load_state("networkidle")
            print("登录成功")
        except Exception as e:
            print(f"登录过程异常（可能已保持登录态）: {e}")

        # 3. 等待页面基础框架加载完毕（避免遮罩尚未出现）
        page.wait_for_timeout(2000)

        # 4. 修正日期并重新查询数据
        #    ⚠️ TODO: 请根据实际页面，替换下面三个选择器
        start_selector = 'input[placeholder="开始日期"]'   # 开始日期输入框的选择器
        end_selector   = 'input[placeholder="结束日期"]'   # 结束日期输入框的选择器
        query_selector = 'div:has-text("查询")'            # 查询按钮的选择器（可能不是唯一，尽量精确）

        try:
            # 等待日期输入框可见
            page.wait_for_selector(start_selector, timeout=5000)
            # 使用 JS 直接赋值并触发 input 事件，确保帆软框架能感知到变化
            page.evaluate(f'''
                (start, end) => {{
                    const s = document.querySelector('{start_selector}');
                    const e = document.querySelector('{end_selector}');
                    if (s && e) {{
                        s.value = '{start_date_str}';
                        e.value = '{end_date_str}';
                        // 手动触发 input 事件，通知框架数值已改变
                        s.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        e.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}
            ''')
            # 点击查询按钮
            page.click(query_selector)
            page.wait_for_load_state("networkidle")
            print(f"日期已更新为 {start_date_str} ~ {end_date_str}，并触发查询")
        except Exception as e:
            print(f"日期修正失败，将继续使用页面默认日期: {e}")

        # 5. 智能等待数据加载完成
        #    先等待“加载中”遮罩消失（如果存在）
        try:
            page.wait_for_selector('.loading-mask', state='hidden', timeout=20000)
            print("加载遮罩已消失")
        except Exception:
            print("未检测到加载遮罩，或等待超时")

        #    再等待报表表格中的“总计”行出现，确保数据已经渲染
        try:
            page.wait_for_selector('div[heavytd="light"]:has-text("总计")', timeout=30000)
            print("检测到总计行，数据加载完成")
        except Exception:
            print("等待总计行超时，继续截图（可能数据已加载）")

        #    最后额外等待2秒，确保样式完全渲染
        page.wait_for_timeout(2000)

        # 6. 执行全页截图
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

    # 构建图片附件，命名为 report_screenshot.png
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
