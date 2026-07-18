-- 词根/词缀的"例子"改成关联 words 表的 word_id，不再维护 roots.cases / affixes.cases 里的自由文本
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_root_affix_words.sql
-- 注：roots.cases / affixes.cases 两列先保留不删（历史数据留作后续人工回填参考），
--     代码只是不再读写这两列了。
-- 注：本地库 words.id 是 int（有符号），生产库 words.id 是 int unsigned——历史遗留的
--     schema 漂移，不是这次改动引入的。下面 word_id 按本地库的 int 写，在生产库跑会因为
--     FK 类型不兼容报错（ERROR 3780），生产环境要把 word_id 的类型换成 INT UNSIGNED 后再跑。

CREATE TABLE IF NOT EXISTS root_words (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  root_id     INT NOT NULL COMMENT '词根ID',
  word_id     INT NOT NULL COMMENT '例词ID',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at  DATETIME NULL COMMENT '软删除时间',
  UNIQUE KEY uk_root_word (root_id, word_id),
  CONSTRAINT fk_root_words_root FOREIGN KEY (root_id) REFERENCES roots(id) ON DELETE CASCADE,
  CONSTRAINT fk_root_words_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='词根关联的例词';

CREATE TABLE IF NOT EXISTS affix_words (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  affix_id    INT NOT NULL COMMENT '词缀ID',
  word_id     INT NOT NULL COMMENT '例词ID',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at  DATETIME NULL COMMENT '软删除时间',
  UNIQUE KEY uk_affix_word (affix_id, word_id),
  CONSTRAINT fk_affix_words_affix FOREIGN KEY (affix_id) REFERENCES affixes(id) ON DELETE CASCADE,
  CONSTRAINT fk_affix_words_word FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='词缀关联的例词';
