-- en-desktop 词库（歌单式）两张表
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_word_libraries.sql
-- 注：word_library_items 比 en-elctron 仓库 schema.sql 的预留版本多一列 updated_at，
--     与 en-desktop 模块基础模型的字段约定保持一致。

CREATE TABLE IF NOT EXISTS word_libraries (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL COMMENT '词库归属用户',
  name        VARCHAR(50)  NOT NULL COMMENT '词库名称',
  description VARCHAR(255) COMMENT '词库介绍',
  is_public   TINYINT      NOT NULL DEFAULT 0 COMMENT '1公开 0私有，公开的可被其他用户浏览',
  created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at  DATETIME     NULL COMMENT '软删除时间',
  CONSTRAINT fk_word_libraries_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个人词库（类似歌单）';

CREATE TABLE IF NOT EXISTS word_library_items (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  word_library_id  INT NOT NULL COMMENT '词库ID',
  word_id          INT NOT NULL COMMENT '单词ID',
  created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '加入词库的时间',
  updated_at       DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at       DATETIME     NULL COMMENT '软删除时间（移出词库）',
  UNIQUE KEY uk_library_word (word_library_id, word_id),
  CONSTRAINT fk_word_library_items_library_id FOREIGN KEY (word_library_id) REFERENCES word_libraries(id) ON DELETE CASCADE,
  CONSTRAINT fk_word_library_items_word_id FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='词库与单词的多对多关联';
