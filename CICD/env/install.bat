@REM ======== 可配置变量 ========
set WIN_USER=Samuel
set ANACONDA_HOME=C:\Users\%WIN_USER%\Anaconda3
set PROJECT_ROOT=D:\workspace_python\infinity
set CICD_DIR=%PROJECT_ROOT%\CICD
set ENV_DIR=%CICD_DIR%\env
set CONDA_ENV_NAME=py312
set ENV_YML=%ENV_DIR%\environment.yml
@REM ============================

setx /M PATH "%PATH%;%CICD_DIR%\cmd;%ENV_DIR%;%CICD_DIR%\git"

cd %ENV_DIR%
d:

@REM remove environment if it exists
conda deactivate
conda remove --name %CONDA_ENV_NAME% --all
rd /s %ANACONDA_HOME%\envs\%CONDA_ENV_NAME%

@REM Create the conda environment from environment.yml
@REM environment.yml 中已写好 channels，并把 pip 段放在最后，conda 保证「先 conda 后 pip」
@REM 注意：这里的 %CONDA_ENV_NAME% 必须和 environment.yml 里的 name: 保持一致
conda env create -f %ENV_YML%
conda activate %CONDA_ENV_NAME%

@REM  一键安装：其余依赖由 requirements.txt 用 pip 锁死版本
python -m pip freeze > %PROJECT_ROOT%\dataIntegrator\test\cicd\requirements_20250517.txt
python -m pip install -r %ENV_DIR%\requirements.txt

@REM Windows 额外依赖
python -m pip install cx_Oracle

@REM Linux 额外依赖（这行是 Linux 命令，在 Windows 的 .bat 中无效，需要时请在 Linux 侧脚本里取消注释）
@REM sudo apt-get install -y libomp5 libgomp1
@REM Windows 侧的 OpenMP 运行时由 conda 的 llvm-openmp 自动带入，无需手工安装

@REM  validate the install compatibility_check.py
python %ENV_DIR%\compatibility_check.py

@REM 在安装后，将 conda 添加到 PATH，这样可以直接用py312.bat 和jlab.bat
setx /M PATH "%PATH%;D:\workspace_python\infinity\CICD\env\conda"