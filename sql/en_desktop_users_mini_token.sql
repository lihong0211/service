-- en-desktop users 表给小程序加独立的登录令牌列
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_users_mini_token.sql
-- 注：token/token_expires_at 原本是桌面端/网页扫码和小程序共用的单一登录令牌槽位，
--     账号绑定打通后桌面端和小程序变成同一条用户记录，谁登录谁顶掉对方的 token，
--     互相把对方挤下线。小程序改用独立的 mini_token 列，两边各用各的，互不影响。

SET @col_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'mini_token'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE users ADD COLUMN mini_token VARCHAR(64) NULL COMMENT ''登录令牌（en-mini 小程序）'' AFTER token_expires_at, ADD UNIQUE KEY uk_users_mini_token (mini_token)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @col_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'mini_token_expires_at'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE users ADD COLUMN mini_token_expires_at DATETIME NULL AFTER mini_token',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
