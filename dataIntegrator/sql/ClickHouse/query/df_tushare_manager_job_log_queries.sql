-- =====================================================
-- TuShare Task Execution Log Common Query SQL
-- ================================= ====================

select today()

select * from indexsysdb.df_tushare_manager_job_log

DESCRIBE TABLE indexsysdb.df_tushare_manager_job_log;


-- 1. View execution status of all tasks today
SELECT
    job_name, job_status, start_time, end_time,
    duration_seconds, records_processed, error_message
FROM indexsysdb.df_tushare_manager_job_log
WHERE
    start_time >= toDateTime('2026-05-04 00:00:00', 'Asia/Shanghai')
    AND start_time < toDateTime('2026-05-05 00:00:00', 'Asia/Shanghai')
ORDER BY start_time;

-- 1. View execution status of all tasks today, order by task name
SELECT
    job_name, job_status, start_time, end_time,
    duration_seconds, records_processed, error_message
FROM indexsysdb.df_tushare_manager_job_log
WHERE
    start_time >= toDateTime('2026-05-04 00:00:00', 'Asia/Shanghai')
    AND start_time < toDateTime('2026-05-05 00:00:00', 'Asia/Shanghai')
ORDER BY job_name, start_time;

-- 2. Calculate today's task success rate
SELECT
    job_status,
    count() AS cnt,
    round(count() / (SELECT count()
                     FROM indexsysdb.df_tushare_manager_job_log
                     WHERE toYYYYMMDD(start_time) = toYYYYMMDD(today()) -- 缂佺喍绔寸猾璇茬��
                    ) * 100, 2) AS percentage
FROM indexsysdb.df_tushare_manager_job_log
WHERE
    start_time >= toDateTime('2026-05-04 00:00:00', 'Asia/Shanghai')
    AND start_time < toDateTime('2026-05-05 00:00:00', 'Asia/Shanghai')
GROUP BY job_status;


