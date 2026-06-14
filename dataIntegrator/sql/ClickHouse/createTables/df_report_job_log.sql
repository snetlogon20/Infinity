-- 报表生成任务执行日志表
-- drop table indexsysdb.df_report_job_log

CREATE TABLE indexsysdb.df_report_job_log
(
    job_id             UInt64,
    job_name           String,
    job_status         String,
    report_type        String,
    start_time         DateTime,
    end_time           Nullable(DateTime),
    duration_seconds   Nullable(Float64),
    records_processed  UInt64,
    error_message      String,
    error_traceback    String,
    extra_params       String,
    comment            String,
    create_time        DateTime DEFAULT now()
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(start_time)
ORDER BY (job_name, start_time)
SETTINGS index_granularity = 8192
COMMENT '报表生成任务执行日志表';
