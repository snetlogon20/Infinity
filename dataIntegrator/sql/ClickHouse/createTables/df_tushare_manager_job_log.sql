-- TuShare数据同步任务执行日志表
-- drop table indexsysdb.df_tushare_manager_job_log

CREATE TABLE indexsysdb.df_tushare_manager_job_log
(
    job_id             UInt64,
    job_name           String,
    job_status         String,
    start_time         DateTime,
    end_time           Nullable(DateTime),
    duration_seconds   Nullable(Float64),
    records_processed  UInt64,
    error_message      String,
    error_traceback    String,
    start_date_param   String,
    end_date_param     String,
    extra_params       String,
    create_time        DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (job_name, start_time)
SETTINGS index_granularity = 8192
COMMENT 'TuShare数据同步任务执行日志表';