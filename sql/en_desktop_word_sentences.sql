-- en-desktop 单词例句表
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_word_sentences.sql

-- 一个词性（word_meanings 一行）对应一条例句，而不是一个单词一条：
-- 同一单词有多个词性时（如 book 的 n./v.），每个词性各生成一条例句。
CREATE TABLE IF NOT EXISTS word_sentences (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  word_meaning_id  INT UNSIGNED NOT NULL COMMENT '词性/释义ID（word_meanings.id）',
  en_text          VARCHAR(255) NOT NULL COMMENT '例句原文',
  zh_text          VARCHAR(255) NOT NULL COMMENT '例句中文翻译',
  audio_url        VARCHAR(255) NULL COMMENT '例句发音音频地址，TTS 方案确定后回填',
  created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at       DATETIME     NULL COMMENT '软删除时间',
  KEY idx_word_meaning_id (word_meaning_id),
  CONSTRAINT fk_word_sentences_word_meaning_id FOREIGN KEY (word_meaning_id) REFERENCES word_meanings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单词例句（按词性区分，含中文翻译，发音音频待补）';
