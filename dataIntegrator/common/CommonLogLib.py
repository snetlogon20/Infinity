import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from dataIntegrator.common.CommonParameters import CommonParameters


class CommonLogLib:

    @classmethod
    def getLog(self):
        try:
            # 创建一个logger实例并设置日志级别
            logger = logging.getLogger('alg_name')
            if not logger.hasHandlers():
                logger.setLevel(logging.DEBUG)

                # 配置handler，拟将日志记录输出至/log/文件夹
                file_name = CommonParameters.logFilePath
                # file_handler = TimedRotatingFileHandler\
                #     (filename=file_name,
                #      when='MIDNIGHT',
                #      interval=1,
                #      backupCount=10)  # 每天午夜生成alg_name_log.log文件，最多保留30天
                file_handler = RotatingFileHandler(
                    filename=file_name,
                    maxBytes=10 * 1024 * 1024,  # 10MB
                    backupCount=5,
                    encoding="utf-8"
                )

                # 配置formatter
                formatter = logging.Formatter('%(levelname)s - %(asctime)s [%(filename)s:%(lineno)d] %(message)s')
                file_handler.setFormatter(formatter)

                # 添加handler至logger
                logger.addHandler(file_handler)

                # 添加StreamHandler以将日志输出到控制台
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)

                logger.info('======== Application Log started ========')

            return logger

        except Exception as e:
            print('Exception', e)
            raise e

