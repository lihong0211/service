-- en-desktop 词库（歌单式）两张表
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_word_libraries.sql
-- 注：word_library_items 比 en-elctron 仓库 schema.sql 的预留版本多一列 updated_at，
--     与 en-desktop 模块基础模型的字段约定保持一致。
-- 注：id/外键列用 INT UNSIGNED，匹配 users/words 表实际的主键类型（无符号）。

-- 音标列加宽：ECDICT 多读音音标超过原 varchar(20)
ALTER TABLE words MODIFY en_pronunciation VARCHAR(64), MODIFY us_pronunciation VARCHAR(64);

CREATE TABLE IF NOT EXISTS word_libraries (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id     INT UNSIGNED NOT NULL COMMENT '词库归属用户',
  name        VARCHAR(50)  NOT NULL COMMENT '词库名称',
  description VARCHAR(255) COMMENT '词库介绍',
  is_public   TINYINT      NOT NULL DEFAULT 0 COMMENT '1公开 0私有，公开的可被其他用户浏览',
  created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at  DATETIME     NULL COMMENT '软删除时间',
  CONSTRAINT fk_word_libraries_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个人词库（类似歌单）';

CREATE TABLE IF NOT EXISTS word_library_favorites (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id          INT UNSIGNED NOT NULL COMMENT '收藏人',
  word_library_id  INT UNSIGNED NOT NULL COMMENT '被收藏的（公共）词库',
  created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at       DATETIME     NULL COMMENT '软删除时间（取消收藏）',
  UNIQUE KEY uk_user_library (user_id, word_library_id),
  CONSTRAINT fk_wlf_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_wlf_library_id FOREIGN KEY (word_library_id) REFERENCES word_libraries(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户收藏的词库';

CREATE TABLE IF NOT EXISTS word_library_items (
  id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  word_library_id  INT UNSIGNED NOT NULL COMMENT '词库ID',
  word_id          INT UNSIGNED NOT NULL COMMENT '单词ID',
  created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '加入词库的时间',
  updated_at       DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at       DATETIME     NULL COMMENT '软删除时间（移出词库）',
  UNIQUE KEY uk_library_word (word_library_id, word_id),
  CONSTRAINT fk_word_library_items_library_id FOREIGN KEY (word_library_id) REFERENCES word_libraries(id) ON DELETE CASCADE,
  CONSTRAINT fk_word_library_items_word_id FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='词库与单词的多对多关联';

-- 补丁：word_library_items 若是从 en-elctron 仓库 schema.sql 的旧"预留版本"建的
-- （没有 updated_at），CREATE TABLE IF NOT EXISTS 不会补这一列——这里用
-- information_schema 判断，缺列才补，MySQL 5.7/8.0 通用，可安全重复执行。
SET @col_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'word_library_items' AND COLUMN_NAME = 'updated_at'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE word_library_items ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
