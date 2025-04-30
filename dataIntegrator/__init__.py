import os

from dataIntegrator.common.CommonLib import CommonLib
from dataIntegrator.common.CommonLogLib import CommonLogLib
from dataIntegrator.common.CommonParameters import CommonParameters
# from dataIntegrator.TuShareService.TuShareServiceManager import TuShareServiceManager

def getEnv():
    print("PYTHONPATH:", os.environ.get('PYTHONPATH'))
    print("PATH:", os.environ.get('PATH'))

def main():
    logger = CommonLogLib.getLog()
    logger.info("==============Application Started=============")
    # tuShareServiceManger = TuShareServiceManager()
    # tuShareServiceManger.callTuShareService()
    pass

if __name__ == '__main__':
    main()
