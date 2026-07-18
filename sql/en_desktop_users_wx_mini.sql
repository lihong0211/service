-- en-desktop users 表加小程序 openid 列
-- 用法：mysql -h <host> -u <user> -p english_new < sql/en_desktop_users_wx_mini.sql
-- 注：en-mini 小程序 code2session 拿到的 openid 和 en-desktop 网页扫码登录（wx 列，
--     微信开放平台 appid）不是同一个 appid 空间，不能共用同一列，否则同一个物理
--     微信用户在两边登录会被当成不同账号也没关系，但字段语义会混乱，所以单独开一列。

SET @col_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'wx_mini'
);
SET @sql = IF(@col_exists = 0,
  'ALTER TABLE users ADD COLUMN wx_mini VARCHAR(64) NULL COMMENT ''微信openid（en-mini小程序）'' AFTER wx, ADD UNIQUE KEY uk_users_wx_mini (wx_mini)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
