-- 词根/词缀从 english.root / english.affix 迁移到 english_new.roots / english_new.affixes
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_roots_affixes.sql
-- 注：跟旧表保持相同的存储格式（similar 逗号分隔字符串、cases 是 JSON 序列化后的文本），
--     只改了字段名（create_at/update_at -> created_at/updated_at）以匹配 en_desktop 模块约定。
--     source 库（english）和目标库（english_new）在同一台 MySQL 实例上，可以直接跨库 SELECT。

CREATE TABLE IF NOT EXISTS roots (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(255) NOT NULL COMMENT '词根名称',
  meaning     VARCHAR(255) COMMENT '含义',
  similar     VARCHAR(255) COMMENT '相似词根，逗号分隔',
  cases       VARCHAR(10000) COMMENT '例子，JSON 数组文本 [{word, meaning}]',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at  DATETIME NULL COMMENT '软删除时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='词根（从 english.root 迁移）';

CREATE TABLE IF NOT EXISTS affixes (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(255) NOT NULL COMMENT '词缀名称',
  meaning     VARCHAR(255) COMMENT '含义',
  similar     VARCHAR(255) COMMENT '相似词缀，逗号分隔',
  cases       VARCHAR(10000) COMMENT '例子，JSON 数组文本 [{word, meaning}]',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at  DATETIME NULL COMMENT '软删除时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='词缀（从 english.affix 迁移）';

-- 幂等：先清空（迁移脚本可能重复执行），再从源库整表复制
DELETE FROM roots;
INSERT INTO roots (id, name, meaning, similar, cases, created_at, updated_at, deleted_at)
SELECT id, name, meaning, similar, cases, create_at, update_at, deleted_at
FROM english.root;

DELETE FROM affixes;
INSERT INTO affixes (id, name, meaning, similar, cases, created_at, updated_at, deleted_at)
SELECT id, name, meaning, similar, cases, create_at, update_at, deleted_at
FROM english.affix;

-- 让 auto_increment 接着源表最大 id 走，避免后续新增撞号
SET @next_root_id = (SELECT COALESCE(MAX(id), 0) + 1 FROM roots);
SET @sql = CONCAT('ALTER TABLE roots AUTO_INCREMENT = ', @next_root_id);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @next_affix_id = (SELECT COALESCE(MAX(id), 0) + 1 FROM affixes);
SET @sql = CONCAT('ALTER TABLE affixes AUTO_INCREMENT = ', @next_affix_id);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
