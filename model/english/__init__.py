# model/english/__init__.py
"""
English 模型模块
"""
from .words import Words
from .root import Root
from .affix import Affix
from .dialogue import Dialogue
from .living_speech import LivingSpeech

__all__ = ['Words', 'Root', 'Affix', 'Dialogue', 'LivingSpeech']
