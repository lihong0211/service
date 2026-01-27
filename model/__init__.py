# model/__init__.py
"""
模型模块
"""
from .words_model import Words
from .root_model import Root
from .affix_model import Affix
from .dialogue_model import Dialogue
from .living_speech_model import LivingSpeech

__all__ = ['Words', 'Root', 'Affix', 'Dialogue', 'LivingSpeech']


