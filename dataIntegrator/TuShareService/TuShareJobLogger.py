import sys
from datetime import datetime
import traceback
import json
from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

class TuShareJobLogger:
    """TuShare任务执行日志记录器"""
    
    def __init__(self):
        self.clickhouseService = ClickhouseService()
        self.job_start_time = None
        self.job_name = None
        self.params = None
        
    def start_job(self, job_name, params=None):
        """开始记录任务"""
        self.job_name = job_name
        self.job_start_time = datetime.now()
        self.params = params
        
        logger.info(f"📝 开始记录任务: {job_name}")
        
        # 插入运行中状态的记录
        sql = """
        INSERT INTO indexsysdb.df_tushare_manager_job_log 
        (job_name, job_status, start_time, end_time, start_date_param, end_date_param, extra_params)
        VALUES
        ('%(job_name)s', 'RUNNING', '%(start_time)s', NULL, '%(start_date)s', '%(end_date)s', '%(extra_params)s')
        """

        try:
            start_date = params.get('start_date', '') if params else ''
            end_date = params.get('end_date', '') if params else ''
            extra_params = json.dumps({k: v for k, v in params.items() if k not in ['start_date', 'end_date']},
                                      ensure_ascii=False) if params else ''

            self.clickhouseService.execute_sql(sql % {
                'job_name': job_name,
                'start_time': self.job_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'start_date': start_date,
                'end_date': end_date,
                'extra_params': extra_params.replace("'", "\\'")
            })
        except Exception as e:
            logger.warning(f"⚠️ 记录任务开始状态失败: {e}")
    
    def end_job_success(self, records_processed=0):
        """记录任务成功完成"""
        if not self.job_start_time or not self.job_name:
            logger.warning("⚠️ 任务未开始，无法记录成功状态")
            return
            
        end_time = datetime.now()
        duration = (end_time - self.job_start_time).total_seconds()
        
        sql = """
        INSERT INTO indexsysdb.df_tushare_manager_job_log 
        (job_name, job_status, start_time, end_time, duration_seconds, records_processed)
        VALUES
        ('%(job_name)s', 'SUCCESS', '%(start_time)s', '%(end_time)s', %(duration)s, %(records)s)
        """
        
        try:
            self.clickhouseService.execute_sql(sql % {
                'job_name': self.job_name,
                'start_time': self.job_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': duration,
                'records': records_processed
            })
            logger.info(f"✅ 任务 {self.job_name} 执行成功，耗时 {duration:.2f} 秒，处理 {records_processed} 条记录")
        except Exception as e:
            logger.error(f"❌ 记录任务成功状态失败: {e}")
    
    def end_job_failed(self, error_message, error_traceback=None):
        """记录任务失败"""
        if not self.job_start_time or not self.job_name:
            logger.warning("⚠️ 任务未开始，无法记录失败状态")
            return
            
        end_time = datetime.now()
        duration = (end_time - self.job_start_time).total_seconds()
        
        sql = """
        INSERT INTO indexsysdb.df_tushare_manager_job_log 
        (job_name, job_status, start_time, end_time, duration_seconds, error_message, error_traceback)
        VALUES
        ('%(job_name)s', 'FAILED', '%(start_time)s', '%(end_time)s', %(duration)s, '%(error_msg)s', '%(error_tb)s')
        """
        
        try:
            self.clickhouseService.execute_sql(sql % {
                'job_name': self.job_name,
                'start_time': self.job_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': duration,
                'error_msg': str(error_message).replace("'", "\\'"),
                'error_tb': (error_traceback or '').replace("'", "\\'")
            })
            logger.error(f"❌ 任务 {self.job_name} 执行失败，耗时 {duration:.2f} 秒: {error_message}")
        except Exception as e:
            logger.error(f" 记录任务失败状态失败: {e}")
