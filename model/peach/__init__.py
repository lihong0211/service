# model/peach/__init__.py
"""
Peach模型模块
"""
from .chat_model import Chat
from .rp_model import Rp
from .manual_model import Manual
from .version_model import Version
from .ali_rp_check_model import AliRpCheck
from .plugin_statistic_model import PluginStatistic
from .check_report_model import CheckReport
from .config_model import Config

__all__ = [
    "Chat",
    "Rp",
    "Manual",
    "Version",
    "AliRpCheck",
    "PluginStatistic",
    "CheckReport",
    "Config",
]

