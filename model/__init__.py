# model/__init__.py
"""
模型模块

不在此处 eager import 子模块（如 .english）：那样会在 app.app 完全加载之前
把 model.english.words 拉起来，而它自己又要 import app.app，形成循环导入。
各子模块（model.english.words / model.chess 等）已经是可以直接导入的完整路径，
调用方应直接 `from model.english.words import Words` 而不是 `from model import Words`。
"""

