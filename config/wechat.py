# config/wechat.py
"""
微信小程序配置：环境变量；若已安装 python-dotenv，自动加载项目根目录 .env。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "")

# en-desktop 模块：微信开放平台"网站应用"（扫码登录），与上面小程序的凭据是两套
EN_DESKTOP_WECHAT_APP_ID = os.environ.get("EN_DESKTOP_WECHAT_APP_ID", "")
EN_DESKTOP_WECHAT_APP_SECRET = os.environ.get("EN_DESKTOP_WECHAT_APP_SECRET", "")

# en-mini 小程序登录（code2session），与上面两套都不是同一个 appid
EN_MINI_WECHAT_APP_ID = os.environ.get("EN_MINI_WECHAT_APP_ID", "")
EN_MINI_WECHAT_APP_SECRET = os.environ.get("EN_MINI_WECHAT_APP_SECRET", "")
