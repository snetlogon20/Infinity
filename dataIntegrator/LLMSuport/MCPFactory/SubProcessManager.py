from dataIntegrator.common.CommonLib import CommonLib
from dataIntegrator.common.CommonLogLib import CommonLogLib
import subprocess
import sys
import os

class SubProcessManager(CommonLib):

    def __init__(self):
        self.logger = CommonLogLib().getLog()
    def run_python_script(self, program_path):

        env = os.environ.copy()
        env["MPLBACKEND"] = "Agg"  # 强制使用非交互式后端
        result = subprocess.run(
            ["python", program_path],
            stdin=sys.stdin,  # 直接使用父进程的输入
            stdout=sys.stdout,  # 直接输出到父进程终端
            stderr=sys.stderr,
            text=True,
            env=env
        )

        self.logger.info(rf"程序 B 的输出：{result.stdout}" )
        self.logger.info(rf"程序 B 的错误（如果有）：{result.stderr}")