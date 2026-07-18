/* =========================================================
   0. 关闭自身写日志，防止清自己把自己打爆
   ========================================================= */
--SET log_queries = 0;


/* =========================================================
   1. 清理前：看一眼现在谁最占空间
   ========================================================= */
SELECT
    '📊 BEFORE_CLEANUP' AS stage,
    database,
    table,
    formatReadableSize(sum(bytes)) AS size
FROM system.parts
WHERE active AND database = 'system'
GROUP BY database, table
ORDER BY sum(bytes) DESC
LIMIT 20;

SELECT '--- STEP 1: snapshot taken ---' AS info;


/* =========================================================
   2. 批量清理（全部带 IF EXISTS，单条失败不阻断）
       注：如果自建实例，建议用 ALTER DROP PARTITION 更彻底
   ========================================================= */

-- 2-A
TRUNCATE TABLE IF EXISTS system.asynchronous_metric_log;
SELECT '✅  dropped: asynchronous_metric_log' AS action;

-- 2-B
TRUNCATE TABLE IF EXISTS system.query_log;
SELECT '✅  dropped: query_log' AS action;

-- 2-C
TRUNCATE TABLE IF EXISTS system.trace_log;
SELECT '✅  dropped: trace_log' AS action;

-- 2-D
TRUNCATE TABLE IF EXISTS system.part_log;
SELECT '✅  dropped: part_log' AS action;

-- 2-E
TRUNCATE TABLE IF EXISTS system.session_log;
SELECT '✅  dropped: session_log' AS action;

-- 2-F
TRUNCATE TABLE IF EXISTS system.query_thread_log;
SELECT '✅  dropped: query_thread_log' AS action;

-- 2-G
TRUNCATE TABLE IF EXISTS system.metric_log;
SELECT '✅  dropped: metric_log' AS action;


/* =========================================================
   3. 强制刷一下，让 parts 元数据立刻释放
   ========================================================= */
SYSTEM FLUSH LOGS;
SELECT '🔄  SYSTEM FLUSH LOGS executed' AS action;


/* =========================================================
   4. 清理后：再扫一次 system.parts 做对账
   ========================================================= */
SELECT
    '📊 AFTER_CLEANUP' AS stage,
    database,
    table,
    formatReadableSize(sum(bytes)) AS size_after
FROM system.parts
WHERE active
  AND database = 'system'
  AND table IN (
      'asynchronous_metric_log',
      'query_log',
      'trace_log',
      'part_log',
      'session_log',
      'query_thread_log',
      'metric_log'
  )
GROUP BY database, table
ORDER BY sum(bytes) DESC;


/* =========================================================
   5. 结束标记（DBeaver 看到这条说明全程没崩）
   ========================================================= */
SELECT
    now()                              AS finish_time,
    '🎉 ALL SYSTEM LOGS CLEARED'       AS final_status;