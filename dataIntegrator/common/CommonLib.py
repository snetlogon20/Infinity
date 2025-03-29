import traceback
from dataIntegrator.common import CommonLogLib
import sys

class CommonLib():

    logger = CommonLogLib.CommonLogLib().getLog()

    def __init__(self, LogLib):

        try:
            self.logger.info("CommonLib __init__ started")

            self.logger.info("CommonLib __init__ completed")
        except Exception as e:
            print('Exception', e)

            print('==============================================')
            print("%s.%s:" % (CommonLogLib, "__init__"))
            print('Exception: ', e)
            info = traceback.format_exc()
            print(info)
            print('==============================================')

        raise e

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

