#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ClickHouse 数据库初始化脚本（幂等，可重复执行）

背景:
    旧的 init_clickhouse_database.sql 是把 createTables 下所有 SQL 拼接出来的快照,
    源文件一改就过期, 且库名硬编码无法参数化。本脚本改为运行时直接扫描源目录,
    逐文件执行, 每个文件的成功/失败都单独报告。

特性:
    1. 目标库:        默认在 test20261011 库中执行(--database 可覆盖)。源 SQL 中硬编码的
                      indexsysdb 前缀在执行前统一改写为目标库名, 保证所有表/视图都建到
                      test20261011, 绝不写入 indexsysdb (ClickHouse 不支持 MySQL 式
                      SET @var / 存储过程, 故在脚本层完成改写)
    2. 幂等可重跑:    CREATE TABLE 自动补 IF NOT EXISTS; CREATE VIEW 自动补 OR REPLACE;
                      已存在的表跳过不报错
    3. 数据安全:      源文件中未注释的 DROP TABLE / DROP VIEW / TRUNCATE 语句一律跳过,
                      避免重跑删表丢数据
    4. 种子数据:      INSERT 语句仅在对应表是"本次运行新建"时才执行, 避免重跑插入重复数据
    5. 依赖重试:      视图依赖底表时按文件名顺序可能失败(如 vw_tushare_opt_daily 依赖
                      vw_tushare_opt_basic_of_today), 失败文件自动进入下一轮重试,
                      直到一轮下来没有新对象产生为止
    6. 结果报告:      控制台实时输出 + CICD/env/database/ 下带时间戳的日志文件

用法:
    python init_clickhouse_database.py                        (默认目标库 test20261011)
    python init_clickhouse_database.py --database other_db    (指定其他目标库)
    python init_clickhouse_database.py --host 192.168.23.128 --port 9000

退出码: 0=全部成功(含跳过/空文件警告)  1=存在失败文件  2=配置或连接错误
"""

import argparse
import datetime
import glob
import logging
import os
import re
import sys

try:
    from clickhouse_driver import Client as ClickhouseClient
    from clickhouse_driver import errors as ch_errors
except ImportError:
    print("[FATAL] 缺少依赖 clickhouse-driver, 请先执行: pip install clickhouse-driver")
    sys.exit(2)

# ---------------------------------------------------------------------------
# 路径与常量
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
DEFAULT_SQL_DIR = os.path.join(PROJECT_ROOT, "dataIntegrator", "sql", "ClickHouse", "createTables")

DEFAULT_HOST = "192.168.23.128"
DEFAULT_PORT = 9000
DEFAULT_USER = "default"
DEFAULT_PASSWORD = ""
DEFAULT_DATABASE = "test20261011"  # 默认目标库, 所有表/视图都建在这里

# 建库语句(幂等, 可重复执行)。目标库默认取 DEFAULT_DATABASE, 可被 --database 参数覆盖
CREATE_DATABASE_SQL = "CREATE DATABASE IF NOT EXISTS %s"

# 源 SQL 文件中硬编码的库名前缀(如 CREATE TABLE indexsysdb.df_xxx)。
# 执行前统一改写为目标库名, 确保所有对象都建到目标库, 绝不写入 indexsysdb。
HARDCODED_SOURCE_DB = "indexsysdb"

# ClickHouse 错误码: 60=UNKNOWN_TABLE, 81=UNKNOWN_DATABASE (视图依赖底表未建时出现)
DEPENDENCY_ERROR_CODES = {60, 81}

RE_DROP = re.compile(r"^\s*drop\s+(?:table|view|dictionary|database)\b", re.I)
RE_TRUNCATE = re.compile(r"^\s*truncate\b", re.I)
RE_INSERT = re.compile(r"^\s*insert\s+into\b", re.I)
RE_OBJECT_NAME = re.compile(
    r"^\s*(?:create\s+(?:or\s+replace\s+)?(?:table|view)|insert\s+into)\s+"
    r"(?:if\s+not\s+exists\s+)?(?:[A-Za-z0-9_]+\.\"?)?([A-Za-z0-9_]+)",
    re.I,
)

# 文件状态常量
ST_OK = "OK"
ST_FAIL = "FAIL"
ST_EMPTY = "EMPTY"
ST_RETRY = "RETRY"  # 内部状态: 依赖缺失, 等待下一轮重试


# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
def setup_logging(log_path):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    logger = logging.getLogger("init_clickhouse")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def replace_source_db(stmt, target_db):
    """把源文件中硬编码的 indexsysdb 前缀改写为目标库名, 保证对象建到目标库。"""
    return re.sub(r"\b%s\b" % HARDCODED_SOURCE_DB, target_db, stmt, flags=re.I)


def split_statements(sql_text):
    """按分号拆分 SQL 语句。
    - 丢弃 -- 行注释与 /* */ 块注释(注释中的分号不会产生碎片)
    - 正确跳过 '...'、"..."、`...` 内部的分号
    - 兼容无结尾分号的最后一条语句
    """
    statements = []
    buf = []
    i, n = 0, len(sql_text)
    quote = None  # "'", '"', '`'
    in_line_comment = False
    in_block_comment = False
    while i < n:
        ch = sql_text[i]
        nxt = sql_text[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                buf.append(ch)
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == "'":
                if nxt:
                    buf.append(nxt)
                    i += 2
                    continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch == "-" and nxt == "-":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def normalize_statement(stmt):
    """幂等改造, 返回 (stmt, kind)。kind: table/view/insert/drop/truncate/other"""
    if RE_DROP.match(stmt):
        return stmt, "drop"
    if RE_TRUNCATE.match(stmt):
        return stmt, "truncate"
    if RE_INSERT.match(stmt):
        return stmt, "insert"
    if re.match(r"\s*create\s+table\s+if\s+not\s+exists\b", stmt, re.I):
        return stmt, "table"
    if re.match(r"\s*create\s+table\b", stmt, re.I):
        stmt = re.sub(r"^(\s*create\s+table\s+)", r"\1IF NOT EXISTS ", stmt, count=1, flags=re.I)
        return stmt, "table"
    if re.match(r"\s*create\s+or\s+replace\s+view\b", stmt, re.I):
        return stmt, "view"
    if re.match(r"\s*create\s+view\b", stmt, re.I):
        stmt = re.sub(r"^(\s*create\s+)view\b", r"\1OR REPLACE VIEW", stmt, count=1, flags=re.I)
        return stmt, "view"
    return stmt, "other"


def extract_object_name(stmt):
    m = RE_OBJECT_NAME.match(stmt)
    return m.group(1) if m else None


def is_dependency_error(exc):
    """判断异常是否因依赖对象(表/视图)尚不存在, 这类失败可等下一轮重试。"""
    if isinstance(exc, ch_errors.ServerException) and exc.code in DEPENDENCY_ERROR_CODES:
        return True
    msg = str(exc).lower()
    return ("doesn't exist" in msg) or ("does not exist" in msg) or \
           ("unknown_table" in msg) or ("unknown_database" in msg)


def first_line(text, limit=300):
    """错误信息压缩成单行(ClickHouse 异常消息常含换行), 便于日志展示。"""
    s = " ".join(str(text).split())
    return s if len(s) <= limit else s[:limit] + "..."


# ---------------------------------------------------------------------------
# 单文件执行
# ---------------------------------------------------------------------------
def execute_sql_file(client, path, target_db, existing_objects, created_objects):
    """执行单个 SQL 文件。
    返回 (status, detail):
        ST_OK    全部语句执行成功(含跳过)
        ST_FAIL  存在无法恢复的失败, detail 为错误信息
        ST_RETRY 依赖缺失, 建议下一轮重试, detail 为错误信息
        ST_EMPTY 文件无有效 SQL 语句
    """
    with open(path, encoding="utf-8-sig") as f:
        raw = f.read()

    statements = [replace_source_db(s, target_db) for s in split_statements(raw)]
    if not statements:
        return ST_EMPTY, "no executable SQL statement (empty or comments only)"

    actions = []
    for stmt in statements:
        stmt, kind = normalize_statement(stmt)
        obj = extract_object_name(stmt)

        if kind in ("drop", "truncate"):
            actions.append("ignored %s (data safety)" % kind.upper())
            continue

        if kind == "insert":
            if obj in created_objects:
                result = client.execute(stmt)
                rows = result[0][0] if result and isinstance(result[0], tuple) else "?"
                actions.append("seed INSERT %s rows into %s" % (rows, obj))
            else:
                actions.append("INSERT into %s skipped (table existed before this run)" % obj)
            continue

        existed_before = obj in existing_objects if obj else False
        try:
            client.execute(stmt)
        except ch_errors.ServerException as e:
            if is_dependency_error(e):
                return ST_RETRY, first_line(e)
            return ST_FAIL, first_line(e)
        except Exception as e:  # 网络断开等
            return ST_FAIL, first_line(e)

        if kind == "view":
            actions.append("view %s refreshed (OR REPLACE)" % obj)
        elif obj and existed_before:
            actions.append("table %s already exists, skipped" % obj)
        elif obj:
            created_objects.add(obj)
            existing_objects.add(obj)
            actions.append("table %s created" % obj)
        else:
            actions.append("ok")

    return ST_OK, "; ".join(actions)


def sort_key(path):
    """视图文件(vw_)排最后, 其余按文件名排序。视图之间的依赖由重试机制兜底。"""
    name = os.path.basename(path).lower()
    return (1 if name.startswith("vw_") else 0, name)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Scan createTables/*.sql and execute them one by one into the target ClickHouse database.")
    parser.add_argument("--database", default=DEFAULT_DATABASE,
                        help="target database name, all objects go here (default: %s)" % DEFAULT_DATABASE)
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help="ClickHouse host (default: %s)" % DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="ClickHouse native port (default: %d)" % DEFAULT_PORT)
    parser.add_argument("--user", default=DEFAULT_USER, help="ClickHouse user (default: %s)" % DEFAULT_USER)
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="ClickHouse password (default: empty)")
    parser.add_argument("--sql-dir", default=DEFAULT_SQL_DIR,
                        help="directory containing the .sql files (default: dataIntegrator/sql/ClickHouse/createTables)")
    args = parser.parse_args()

    target_db = args.database.strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", target_db):
        print("[FATAL] 非法数据库名: %r" % target_db)
        sys.exit(2)

    if not os.path.isdir(args.sql_dir):
        print("[FATAL] SQL 目录不存在: %s" % args.sql_dir)
        sys.exit(2)

    files = sorted(glob.glob(os.path.join(args.sql_dir, "*.sql")), key=sort_key)
    if not files:
        print("[FATAL] SQL 目录下没有 .sql 文件: %s" % args.sql_dir)
        sys.exit(2)

    log_path = os.path.join(SCRIPT_DIR, "init_clickhouse_%s.log" %
                            datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    logger = setup_logging(log_path)

    logger.info("=" * 70)
    logger.info("ClickHouse database init started")
    logger.info("  host     : %s:%s (user=%s)" % (args.host, args.port, args.user))
    logger.info("  database : %s  (source prefix '%s' rewritten to target db)" % (target_db, HARDCODED_SOURCE_DB))
    logger.info("  sql dir  : %s" % args.sql_dir)
    logger.info("  files    : %d" % len(files))
    logger.info("  log file : %s" % log_path)
    logger.info("=" * 70)

    # ---- 连接并建库 ----
    try:
        bootstrap_client = ClickhouseClient(host=args.host, port=args.port,
                                            user=args.user, password=args.password)
        create_db_sql = CREATE_DATABASE_SQL % target_db
        logger.info("execute: %s" % create_db_sql)
        bootstrap_client.execute(create_db_sql)
        bootstrap_client.disconnect()
        client = ClickhouseClient(host=args.host, port=args.port, user=args.user,
                                  password=args.password, database=target_db)
        existing_objects = {row[0] for row in
                            client.execute("SELECT name FROM system.tables WHERE database = %(db)s",
                                           {"db": target_db})}
    except Exception as e:
        logger.error("[FATAL] 无法连接 ClickHouse 或建库失败: %s" % first_line(e))
        sys.exit(2)

    logger.info("database ready, %d object(s) already exist in '%s'" % (len(existing_objects), target_db))

    # ---- 多轮执行, 依赖缺失的文件自动重试 ----
    created_objects = set()
    results = {}  # path -> (status, detail)
    pending = list(files)
    pass_no = 0
    while pending:
        pass_no += 1
        logger.info("---- pass %d: %d file(s) to execute ----" % (pass_no, len(pending)))
        next_pending = []
        for path in pending:
            name = os.path.basename(path)
            try:
                status, detail = execute_sql_file(client, path, target_db,
                                                  existing_objects, created_objects)
            except Exception as e:
                status, detail = ST_FAIL, first_line(e)
            if status == ST_RETRY:
                logger.warning("[RETRY ] %-50s deferred (dependency missing): %s" % (name, detail))
                next_pending.append((path, detail))
            elif status == ST_OK:
                results[path] = (ST_OK, detail)
                logger.info("[OK    ] %-50s %s" % (name, detail))
            elif status == ST_EMPTY:
                results[path] = (ST_EMPTY, detail)
                logger.warning("[EMPTY ] %-50s %s" % (name, detail))
            else:
                results[path] = (ST_FAIL, detail)
                logger.error("[FAIL  ] %-50s %s" % (name, detail))

        if not next_pending:
            break
        # 只有本轮真的新建了对象, 重试才有意义
        if not created_objects:
            for path, detail in next_pending:
                results[path] = (ST_FAIL, "dependency unresolved after retries; last error: %s" % detail)
                logger.error("[FAIL  ] %-50s dependency unresolved after retries" % os.path.basename(path))
            break
        pending = [p for p, _ in next_pending]

    # ---- 汇总 ----
    ok_files = [p for p, (s, _) in results.items() if s == ST_OK]
    empty_files = [p for p, (s, _) in results.items() if s == ST_EMPTY]
    fail_files = [p for p, (s, _) in results.items() if s == ST_FAIL]

    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("  total files : %d" % len(files))
    logger.info("  ok          : %d" % len(ok_files))
    logger.info("  empty(warn) : %d" % len(empty_files))
    logger.info("  failed      : %d" % len(fail_files))
    logger.info("  objects created this run : %d %s" %
                (len(created_objects), sorted(created_objects) if created_objects else ""))
    if empty_files:
        logger.warning("  empty files: %s" % ", ".join(os.path.basename(p) for p in empty_files))
    if fail_files:
        logger.error("  failed files:")
        for p in fail_files:
            logger.error("    - %s : %s" % (os.path.basename(p), results[p][1]))
    logger.info("log saved to: %s" % log_path)
    logger.info("=" * 70)

    try:
        client.disconnect()
    except Exception:
        pass

    sys.exit(1 if fail_files else 0)


if __name__ == "__main__":
    main()
