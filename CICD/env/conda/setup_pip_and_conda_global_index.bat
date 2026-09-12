pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
conda config --set show_channel_urls yes

REM notepad %USERPROFILE%\.condarc 用这条修改
REM channels:
REM   - defaults
REM show_channel_urls: true
REM default_channels:
REM   - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
REM   - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
REM   - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
REM custom_channels:
REM   conda-forge: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud
REM   pytorch: https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud

conda clean -i

conda config --show default_channels
conda info

conda config --show solver