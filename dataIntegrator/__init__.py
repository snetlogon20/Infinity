import os
from dataIntegrator.TuShareService.TuShareServiceManager import TuShareServiceManager
#20250401
def getEnv():
    print("PYTHONPATH:", os.environ.get('PYTHONPATH'))
    print("PATH:", os.environ.get('PATH'))

def main():
    tuShareServiceManger = TuShareServiceManager()
    tuShareServiceManger.callTuShareService()

if __name__ == '__main__':
    main()
