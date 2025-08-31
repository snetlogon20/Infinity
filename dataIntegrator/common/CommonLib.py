import traceback
from dataIntegrator.common import CommonLogLib
from dataIntegrator.common.CustomError import CustomError


class CommonLib():

    logger = CommonLogLib.CommonLogLib().getLog()
    customError = CustomError("000000","")

    #def __init__(self, LogLib):
    def __init__(self):
        pass

    @classmethod
    def raise_custom_error(self, error_code, custom_error_message, e=None, log_error=True):
        error_message = self.customError.get_error_message(error_code, custom_error_message)
        if log_error == True:
            self.logger.error(error_message, exc_info=e)
        raise CustomError(error_code, error_message)


    @classmethod
    def writeLogInfo(self, className ="unknown", functionName="unknown", event="unknown"):
        print("%s.%s: %s" % (className, functionName, event))
        self.logger.info("%s.%s: %s" % (className, functionName, event))

    @classmethod
    def writeWarning(self, className ="unknown", functionName="unknown", event="unknown"):
        print("%s.%s: %s" % (className, functionName, event))
        self.logger.warning("%s.%s: %s" % (className, functionName, event))

    @classmethod
    def writeLogError(self, e, className ="unknown", functionName="unknown", event="unknown"):

        self.logger.error("%s.%s: %s" % (className, functionName, event))

        self.logger.error('==============================================')
        self.logger.error("%s.%s:" % (className, functionName))
        self.logger.error('Exception: ', e)
        info = traceback.format_exc()
        self.logger.error(info)
        self.logger.error('==============================================')

    @staticmethod
    def setPandasPrintOptions():
        import pandas as pd
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)  # 根据你的屏幕宽度调整