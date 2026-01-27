# routes/__init__.py
"""
路由模块
"""
from flask import Blueprint

# 导入服务函数
from service.words import add as words_add, delete as words_delete, update as words_update, list_words
from service.root import add as root_add, delete as root_delete, update as root_update, list_roots
from service.affix import add as affix_add, delete as affix_delete, update as affix_update, list_affixes
from service.dialogue import add as dialogue_add, delete as dialogue_delete, update as dialogue_update, list_dialogues
from service.livingSpeech import add as living_speech_add, delete as living_speech_delete, update as living_speech_update, list_speeches
from service.peach.pddReport import add_chat, list_chat, add_rp, list_rp, add_manual, list_manual
from service.peach.version import add_version, list_version
from service.peach.aliReport import add as ali_rp_add, get as ali_rp_get, update as ali_rp_update
from service.peach.check import add as check_add
from service.peach.config import list_config
from service.peach.pluginStatistic import add as plugin_statistics_add, list_statistics, detail as plugin_statistics_detail

# 创建蓝图
api_bp = Blueprint('api', __name__)

# 单词相关路由
api_bp.add_url_rule('/words/add', 'words_add', words_add, methods=['POST'])
api_bp.add_url_rule('/words/delete', 'words_delete', words_delete, methods=['POST'])
api_bp.add_url_rule('/words/update', 'words_update', words_update, methods=['POST'])
api_bp.add_url_rule('/words/list', 'words_list', list_words, methods=['POST'])

# 词根相关路由
api_bp.add_url_rule('/root/add', 'root_add', root_add, methods=['POST'])
api_bp.add_url_rule('/root/delete', 'root_delete', root_delete, methods=['POST'])
api_bp.add_url_rule('/root/update', 'root_update', root_update, methods=['POST'])
api_bp.add_url_rule('/root/list', 'root_list', list_roots, methods=['POST'])

# 词缀相关路由
api_bp.add_url_rule('/affix/add', 'affix_add', affix_add, methods=['POST'])
api_bp.add_url_rule('/affix/delete', 'affix_delete', affix_delete, methods=['POST'])
api_bp.add_url_rule('/affix/update', 'affix_update', affix_update, methods=['POST'])
api_bp.add_url_rule('/affix/list', 'affix_list', list_affixes, methods=['GET'])

# 对话相关路由
api_bp.add_url_rule('/dialogue/add', 'dialogue_add', dialogue_add, methods=['POST'])
api_bp.add_url_rule('/dialogue/delete', 'dialogue_delete', dialogue_delete, methods=['POST'])
api_bp.add_url_rule('/dialogue/update', 'dialogue_update', dialogue_update, methods=['POST'])
api_bp.add_url_rule('/dialogue/list', 'dialogue_list', list_dialogues, methods=['GET'])

# 生活用语相关路由
api_bp.add_url_rule('/living-speech/add', 'living_speech_add', living_speech_add, methods=['POST'])
api_bp.add_url_rule('/living-speech/delete', 'living_speech_delete', living_speech_delete, methods=['POST'])
api_bp.add_url_rule('/living-speech/update', 'living_speech_update', living_speech_update, methods=['POST'])
api_bp.add_url_rule('/living-speech/list', 'living_speech_list', list_speeches, methods=['POST'])

# 拼多多报告相关路由
api_bp.add_url_rule('/pddReport/chat/add', 'pdd_chat_add', add_chat, methods=['POST'])
api_bp.add_url_rule('/pddReport/chat/list', 'pdd_chat_list', list_chat, methods=['POST'])
api_bp.add_url_rule('/pddReport/rp/add', 'pdd_rp_add', add_rp, methods=['POST'])
api_bp.add_url_rule('/pddReport/rp/list', 'pdd_rp_list', list_rp, methods=['POST'])
api_bp.add_url_rule('/pddReport/manual/add', 'pdd_manual_add', add_manual, methods=['POST'])
api_bp.add_url_rule('/pddReport/manual/list', 'pdd_manual_list', list_manual, methods=['POST'])

# 版本相关路由
api_bp.add_url_rule('/jdReport/version/add', 'version_add', add_version, methods=['POST'])
api_bp.add_url_rule('/jdReport/version/list', 'version_list', list_version, methods=['POST'])
api_bp.add_url_rule('/peach/version/add', 'peach_version_add', add_version, methods=['POST'])

# 阿里报告相关路由
api_bp.add_url_rule('/aliReport/rp/add', 'ali_rp_add', ali_rp_add, methods=['POST'])
api_bp.add_url_rule('/aliReport/rp/get', 'ali_rp_get', ali_rp_get, methods=['POST'])
api_bp.add_url_rule('/aliReport/rp/update', 'ali_rp_update', ali_rp_update, methods=['POST'])

# 检查相关路由
api_bp.add_url_rule('/peach/check/add', 'check_add', check_add, methods=['POST'])

# 配置相关路由
api_bp.add_url_rule('/peach/config/list', 'config_list', list_config, methods=['GET'])

# 插件统计相关路由
api_bp.add_url_rule('/peach/plugin-statistics/add', 'plugin_statistics_add', plugin_statistics_add, methods=['POST'])
api_bp.add_url_rule('/peach/plugin-statistics/list', 'plugin_statistics_list', list_statistics, methods=['POST'])
api_bp.add_url_rule('/peach/plugin-statistics/detail', 'plugin_statistics_detail', plugin_statistics_detail, methods=['POST'])

