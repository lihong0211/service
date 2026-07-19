-- en-desktop 单词拼读拆分表（字母段-音素对应关系，AI 生成，供拼读教学功能使用）
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_word_phonics.sql
-- word_id 用 INT UNSIGNED，匹配 words.id 实际列类型（DESCRIBE words 验证过，本地库就是
-- unsigned；en_desktop_word_sentences.sql 里说"本地库是有符号 int"是过时的说法，以此为准）

CREATE TABLE IF NOT EXISTS word_phonics (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  word_id     INT UNSIGNED NOT NULL COMMENT '单词ID',
  segments    JSON NOT NULL COMMENT '字母段-音素拆分，如 [{"letters":"c","ipa":"k"},...]',
  created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at  DATETIME     NULL COMMENT '软删除时间',
  UNIQUE KEY uk_word_id (word_id),
  CONSTRAINT fk_word_phonics_word_id FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='单词拼读拆分（字母段-音素对应，AI 生成）';
