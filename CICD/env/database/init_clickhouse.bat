@echo off
chcp 65001 >nul
setlocal

REM ============================================================================
REM  ClickHouse 数据库初始化 (幂等, 可重复执行)
REM
REM  直接双击或无参数运行即可, 默认参数:
REM    --database test20261011 --host 192.168.23.128 --port 9000 --user default
REM  (默认值定义在 init_clickhouse_database.py 顶部的 DEFAULT_* 常量)
REM
REM  也可覆盖任意参数, 原样透传, 例如:
REM    init_clickhouse.bat --database other_db
REM    init_clickhouse.bat --host 10.0.0.1 --port 9000 --user default --password xxx
REM
REM  日志输出: 本目录下 init_clickhouse_yyyyMMdd_HHmmss.log
REM ============================================================================

python "%~dp0init_clickhouse_database.py" %*
exit /b %ERRORLEVEL%

endlocal
