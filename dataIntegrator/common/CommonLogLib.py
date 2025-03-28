import logging
from logging.handlers import TimedRotatingFileHandler
from dataIntegrator.common.CommonParameters import CommonParameters


class CommonLogLib:

    @classmethod
    def getLog(self):
        try:
            # 创建一个logger实例并设置日志级别
            logger = logging.getLogger('alg_name')
            logger.setLevel(logging.DEBUG)

            # 配置handler，拟将日志记录输出至/log/文件夹
            file_name = CommonParameters.logFilePath
            file_handler = TimedRotatingFileHandler\
                (filename=file_name,
                 when='MIDNIGHT',
                 interval=1,
                 backupCount=10)  # 每天午夜生成alg_name_log.log文件，最多保留30天

            # 配置formatter
            formatter = logging.Formatter('%(levelname)s - %(asctime)s [%(filename)s:%(lineno)d] %(message)s \n')
            file_handler.setFormatter(formatter)

            # 添加handler至logger
            logger.addHandler(file_handler)

            logger.debug('debug message')

            return logger

        except Exception as e:
            print('Exception', e)
            raise e

