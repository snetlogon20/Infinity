setx /M PATH "%PATH%;D:\workspace_python\infinity\CICD\cmd;D:\workspace_python\infinity\CICD\env;D:\workspace_python\infinity\CICD\git"

cd D:\workspace_python\infinity\CICD\env\
d:

@REM remove environment if it exists
conda deactivate
conda remove --name py312 --all
rd /s C:\Users\ASUS\Anaconda3\envs\py312

@REM Create a new conda environment, then activate it
conda create -n py312 python=3.12
conda activate py312

@REM install chromadb and arch which are not able with requirment.txt
pip install "arch>=5.5.0" --config-settings="--global-option=--no-cython"
pip install "chromadb>=0.4.20" --no-deps --find-links=https://whls.blob.core.windows.net/unstable/
pip install chromadb[all] pandas sentence-transformers overrides
pip install posthog


@REM  一键安装
pip install -r D:\workspace_python\infinity\CICD\env\requirements.txt

@REM Linux 额外依赖
sudo apt-get install -y libomp5 libgomp1  # Ubuntu/Debian

@REM  validate the install compatibility_check.py
python D:\workspace_python\infinity\CICD\env\compatibility_check.py