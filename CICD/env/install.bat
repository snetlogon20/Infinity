cd D:\workspace_python\infinity\CICD\env\

conda deactivate
conda remove --name py312 --all

# Create a new conda environment
conda create -n py312 python=3.12
# Activate the environment
conda activate py312


pip install "chromadb>=0.4.20" --no-deps --find-links=https://whls.blob.core.windows.net/unstable/
pip install "arch>=5.5.0" --config-settings="--global-option=--no-cython"

# 一键安装
pip install -r requirements.txt

# Linux 额外依赖
sudo apt-get install -y libomp5 libgomp1  # Ubuntu/Debian

pip install sparkai
pip install pydevd-pycharm


# 验证脚本 compatibility_check.py
python compatibility_check.py