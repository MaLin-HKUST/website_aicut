-- ============================================
-- 服务器 PostgreSQL 数据备份
-- 数据库: website_aicut
-- 时间: $(date)
-- ============================================

-- 1. companies 表 (1条)
INSERT INTO companies (id, name, created_at) VALUES
(1, '日标住建', '2026-04-02 09:19:22.44267+00');

-- 2. users 表 (2条)
INSERT INTO users (id, username, password_hash, role, company_id, created_at) VALUES
(1, 'admin', 'b77226ed621b7058f84d9a7578380cbe$487d577a8384b811b4e2327ae375009b84939e85d70be695f308d81fcc4b2b85', 'admin', NULL, '2026-04-02 07:57:08.148515+00'),
(2, 'rbzj', '98bbcdaaf5bdedac2ac13663c8133ea7$1b201812f9acd7fc2d2a0d7b357304cc391b4792f240800cfda0175ca1bf9022', 'user', 1, '2026-04-02 09:26:16.968331+00');

-- 3. materials 表 (0条)
-- 空表

-- 4. sessions 表 (17条)
INSERT INTO sessions (id, token, user_id, created_at) VALUES
(1, 'eJoQ9LJn_rvDLhujO8YuRytQdL8ODUEqQLh5TjdqFzM', 1, '2026-04-02 07:57:57.978521+00'),
(2, 'dscNcXJNchFb4E20OKfVUjlJ3GWnhxv7AmNHjRXones', 1, '2026-04-02 07:59:09.980982+00'),
(3, 'bYBPCQUAvrtxE-_cWzettZ7ci7G-HE2eMDjlURURNyU', 1, '2026-04-02 07:59:24.2367+00'),
(4, 'w7WFzQzmKKmZu6BxgWMTXOlKaVd1e-7Trtp7t1HdFQw', 1, '2026-04-02 09:19:06.365528+00'),
(5, 'OnIWrOfLtwTfRW5QJMCGSTUNemkxtz_JiAgMjrVxvGk', 1, '2026-04-02 09:19:22.289371+00'),
(6, 'B4oi4WapUB-_OzUMws-gpxY4b7Smrd6wbgxF25rsgKg', 1, '2026-04-02 09:19:32.784033+00'),
(7, 'tuUmmsSEKfHJD2aWuywV9Wt3yzEcDNkD7CYlbwWqVLY', 1, '2026-04-02 09:26:16.801155+00'),
(8, 'lFbHXLzmI8FZM9eDbH6CU7r2vkHQ-cIwBg_Y4LGC4bs', 2, '2026-04-02 09:40:45.989853+00'),
(9, 'XlWXKF2F2eMftXvg0OFByoUauQW34w4Y0s1Wh4LwEvo', 2, '2026-04-02 10:03:03.765168+00'),
(10, 'HgP9Y0VWQgkur9nK1RZk5bKj3gd4_XlIDx4h7yKUeM4', 1, '2026-04-02 10:07:16.097737+00'),
(11, 'ABd7I6G7wHX8wchZY3Okz7rGppbvCndbaGQl3Pjr5zc', 2, '2026-04-02 10:10:51.239469+00'),
(12, 'jppX9cdm6iT0Q-WSAACbg4737_laVoq13KX1ciRwo2E', 2, '2026-04-02 10:12:03.072884+00'),
(13, 'bRmwd17s_KPG9sa29zNiJoIZocQfMAxx4Z_jIRMJDVI', 2, '2026-04-02 10:14:49.074819+00'),
(14, 'KDK3aBN7zvtrM2cHWGXKZu6e8Ihfu5n31AHn0ZtsYb0', 2, '2026-04-02 10:22:00.28427+00'),
(15, '_Yte5SVS12RQUcWvuyjAdHoMakecfTTbTydiO35xLn8', 2, '2026-04-03 01:00:56.756465+00'),
(16, '6NY5bxEFv_dwN6sXSF-8FCKLUteIY-POqzSCfN1vR-U', 2, '2026-04-03 01:01:36.620464+00'),
(17, '1M7NUW-mz0pZ7B-5l6TAc01dLKqORmktqO0ym7ThdGg', 2, '2026-04-06 07:06:37.156681+00');

-- 5. user_usage_monthly 表 (2条)
INSERT INTO user_usage_monthly (id, user_id, year_month, credits_used, credits_limit, last_updated, created_at) VALUES
(1, 1, '2026-04', 52, NULL, '2026-04-02 08:00:01.421716+00', '2026-04-02 07:58:07.636259+00'),
(2, 2, '2026-04', 1036, NULL, '2026-04-06 07:14:00.536466+00', '2026-04-02 09:40:48.710217+00');
