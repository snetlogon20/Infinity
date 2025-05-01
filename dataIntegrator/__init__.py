import os

from dataIntegrator.common.CommonLib import CommonLib
from dataIntegrator.common.CommonLogLib import CommonLogLib
from dataIntegrator.common.CommonParameters import CommonParameters

logger = CommonLogLib.getLog()
def getEnv():
    print("PYTHONPATH:", os.environ.get('PYTHONPATH'))
    print("PATH:", os.environ.get('PATH'))

def main():
    logger.info("==============Application Started=============")

if __name__ == '__main__':
    main()
