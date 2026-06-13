import json
from datetime import datetime
from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class ReportJobLogger:
    """报表生成任务执行日志记录器"""

    # 需要提取为 comment 的关键字段（按优先级排列）
    _COMMENT_KEYS = ['report_name', 'report_type', 'market_type', 'start_date', 'end_date',
                     'trade_dates_count', 'cases_count', 'benchmark', 'market_symbol']

    def __init__(self):
        self.clickhouseService = ClickhouseService()
        self.job_start_time = None
        self.job_name = None
        self.params = None
        self.comment = ''

    @staticmethod
    def _build_comment(params):
        """从 params 中提取关键字段，构建可读的 comment 字符串"""
        if not params:
            return ''
        parts = []
        for key in ReportJobLogger._COMMENT_KEYS:
            val = params.get(key)
            if val is not None and str(val).strip() != '':
                parts.append(f'{key}={val}')
        return ', '.join(parts)

    def start_job(self, job_name, report_type, params=None):
        """开始记录任务"""
        self.job_name = job_name
        self.job_start_time = datetime.now()
        self.params = params
        self.comment = self._build_comment(params)

        logger.info(f"📝 开始记录报表任务: {job_name} (type={report_type})")

        extra_params = json.dumps(params, ensure_ascii=False) if params else ''

        sql = """
        INSERT INTO indexsysdb.df_report_job_log 
        (job_name, job_status, report_type, start_time, end_time, extra_params, comment)
        VALUES
        ('%(job_name)s', 'RUNNING', '%(report_type)s', '%(start_time)s', NULL, '%(extra_params)s', '%(comment)s')
        """

        try:
            self.clickhouseService.execute_sql(sql % {
                'job_name': job_name,
                'report_type': report_type,
                'start_time': self.job_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'extra_params': extra_params.replace("'", "\\'"),
                'comment': self.comment.replace("'", "\\'")
            })
        except Exception as e:
            logger.warning(f"⚠️ 记录报表任务开始状态失败: {e}")

    def end_job_success(self, records_processed=0):
        """记录任务成功完成"""
        if not self.job_start_time or not self.job_name:
            logger.warning("⚠️ 任务未开始，无法记录成功状态")
            return

        end_time = datetime.now()
        duration = (end_time - self.job_start_time).total_seconds()

        sql = """
        INSERT INTO indexsysdb.df_report_job_log 
        (job_name, job_status, start_time, end_time, duration_seconds, records_processed, comment)
        VALUES
        ('%(job_name)s', 'SUCCESS', '%(start_time)s', '%(end_time)s', %(duration)s, %(records)s, '%(comment)s')
        """

        try:
            self.clickhouseService.execute_sql(sql % {
                'job_name': self.job_name,
                'start_time': self.job_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': duration,
                'records': records_processed,
                'comment': self.comment.replace("'", "\\'")
            })
            logger.info(f"✅ 报表任务 {self.job_name} 执行成功，耗时 {duration:.2f} 秒")
        except Exception as e:
            logger.error(f"❌ 记录报表任务成功状态失败: {e}")

    def end_job_failed(self, error_message, error_traceback=None):
        """记录任务失败"""
        if not self.job_start_time or not self.job_name:
            logger.warning("⚠️ 任务未开始，无法记录失败状态")
            return

        end_time = datetime.now()
        duration = (end_time - self.job_start_time).total_seconds()

        sql = """
        INSERT INTO indexsysdb.df_report_job_log 
        (job_name, job_status, start_time, end_time, duration_seconds, error_message, error_traceback, comment)
        VALUES
        ('%(job_name)s', 'FAILED', '%(start_time)s', '%(end_time)s', %(duration)s, '%(error_msg)s', '%(error_tb)s', '%(comment)s')
        """

        try:
            self.clickhouseService.execute_sql(sql % {
                'job_name': self.job_name,
                'start_time': self.job_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': duration,
                'error_msg': str(error_message).replace("'", "\\'"),
                'error_tb': (error_traceback or '').replace("'", "\\'"),
                'comment': self.comment.replace("'", "\\'")
            })
            logger.error(f"❌ 报表任务 {self.job_name} 执行失败，耗时 {duration:.2f} 秒: {error_message}")
        except Exception as e:
            logger.error(f"❌ 记录报表任务失败状态失败: {e}")
