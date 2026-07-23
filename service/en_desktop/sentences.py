# service/en_desktop/sentences.py
"""
新增单词的例句自动生成：作为 FastAPI BackgroundTasks 在 /words/add 响应返回之后跑，
不影响"新增单词"接口本身的响应速度。

失败全部静默降级，不抛到调用方：
- LLM 生成失败/校验多次不过 -> 记日志跳过，这条 meaning 留给以后手动批量流程
  （fetch_batch.py 本来就会捞到所有缺例句的 word_meaning，不用额外处理）
- TTS 失败 -> 例句文字已经落库，audio_url 留空，generate_sentence_audio.py --apply
  按老逻辑本来就会捞出所有 audio_url 为空的例句去补
"""
import logging
import os

from app.database import SessionLocal, clear_request_session, db, set_request_session
from model.en_desktop import EnDesktopWord, EnDesktopWordMeaning, EnDesktopWordSentence
from service.en_desktop import sentences_llm
from service.en_desktop.tencent_tts import synthesize_speech

logger = logging.getLogger(__name__)

# 跟 scripts/generate_sentence_audio.py 用同一套环境变量：部署在生产服务器上跑，
# 自动读到服务器自己的 .env，不会出现本地生成、线上访问不到的路径不一致问题
STATIC_DIR = os.environ.get("SENTENCE_AUDIO_STATIC_DIR", "/lihong/static/word_sentences")
PUBLIC_BASE_URL = os.environ.get(
    "SENTENCE_AUDIO_PUBLIC_BASE_URL", "https://doctor-dog.com/static/word_sentences"
)

# 开头词分布现算取样窗口，跟人工批量流程的单批规模（200条）保持同一量级
RECENT_OPENERS_LIMIT = 200


def _recent_openers(limit: int = RECENT_OPENERS_LIMIT) -> list[str]:
    rows = (
        db.session.query(EnDesktopWordSentence.en_text)
        .where(EnDesktopWordSentence.deleted_at.is_(None))
        .order_by(EnDesktopWordSentence.id.desc())
        .limit(limit)
        .all()
    )
    openers = []
    for (en_text,) in rows:
        tokens = (en_text or "").strip().split()
        if tokens:
            openers.append(tokens[0].strip('.,!?"\''))
    return openers


def _save_audio(sentence_id: int, audio: bytes) -> str:
    os.makedirs(STATIC_DIR, exist_ok=True)
    file_path = os.path.join(STATIC_DIR, f"{sentence_id}.mp3")
    with open(file_path, "wb") as f:
        f.write(audio)
    return f"{PUBLIC_BASE_URL}/{sentence_id}.mp3"


def generate_and_attach_sentence(word_meaning_id: int) -> None:
    """给一条新增的 word_meaning 生成例句+音频并落库；不复用请求级 session
    （LLM+TTS 往返可能有几秒到几十秒，长期占着请求级连接不合适），自己开一个短生命周期的。"""
    session = SessionLocal()
    set_request_session(session)
    try:
        meaning = EnDesktopWordMeaning.get_by_id(word_meaning_id)
        if not meaning:
            return
        word = EnDesktopWord.get_by_id(meaning.word_id)
        if not word:
            return

        recent_openers = _recent_openers()
        sentence = sentences_llm.request_example_sentence(
            word.word, meaning.type, meaning.content, recent_openers
        )
        if sentence is None:
            logger.warning("新词例句生成失败：%s / %s", word.word, meaning.content)
            return

        sentence_id = EnDesktopWordSentence.insert(
            {
                "word_meaning_id": word_meaning_id,
                "en_text": sentence["en_text"],
                "zh_text": sentence["zh_text"],
            }
        )

        audio = synthesize_speech(sentence["en_text"])
        if audio is None:
            logger.warning("新词例句 TTS 失败：%s", sentence["en_text"])
            return

        audio_url = _save_audio(sentence_id, audio)
        EnDesktopWordSentence.update({"id": sentence_id, "audio_url": audio_url})
    except Exception:
        logger.exception("新词例句自动生成异常：word_meaning_id=%s", word_meaning_id)
    finally:
        clear_request_session()
        session.close()
