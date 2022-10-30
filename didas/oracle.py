import os

import numpy as np
from sqlalchemy import String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DatabaseError
from tqdm import tqdm


def get_engine(
    oracle_username: str = None,
    oracle_password: str = None,
    oracle_hosts: set = set(),
    oracle_port: int = None,
    oracle_servicename: str = None,
) -> Engine:
    oracle_username = oracle_username or os.environ["ORACLE_USER"]
    oracle_password = oracle_password or os.environ["ORACLE_PASS"]
    oracle_hosts |= {v for k, v in os.environ.items() if k.startswith("ORACLE_HOST")}
    oracle_port = oracle_port or int(os.environ["ORACLE_PORT"])
    oracle_servicename = oracle_servicename or os.environ["ORACLE_SERVICE_NAME"]
    assert len(oracle_hosts) > 0
    excs = dict()
    for oracle_host in oracle_hosts:
        engine = create_engine(f"oracle+cx_oracle://{oracle_username}:{oracle_password}@{oracle_host}:{oracle_port}/?service_name={oracle_servicename}", max_identifier_length=128)
        try:
            with engine.begin():
                return engine
        except DatabaseError as e:
            excs[oracle_host] = e
    assert False, excs


def table_size(table_name, cur):
    r = cur.execute(
        f"""
    SELECT sum(BYTES)
    FROM DBA_SEGMENTS
    WHERE SEGMENT_NAME = '{table_name.upper()}'
    GROUP BY SEGMENT_NAME
    """
    )
    try:
        return next(r)[0]
    except StopIteration:
        return 0


def compress_table(table_name, cur, compress_for="ARCHIVE HIGH", force=False, raise_if_not_exists=True):
    r = cur.execute(
        f"""
        SELECT compression, compress_for
        FROM   user_tables
        WHERE  table_name = '{table_name.upper()}'
    """
    )
    try:
        compression, compress_for_now = next(r)
    except StopIteration:
        if raise_if_not_exists:
            raise ValueError(f"Table {table_name.upper()} does not exist")
        else:
            return
    if compress_for_now != compress_for or force:
        size_before = table_size(table_name, cur)
        cur.execute(f"ALTER TABLE {table_name} MOVE COMPRESS for {compress_for}")
        try:
            return table_size(table_name, cur) / size_before
        except ZeroDivisionError:
            return 1
    return 1


def get_columns(table_name, cur):
    r = cur.execute(
        f"""
        SELECT column_name
        FROM all_tab_cols
        WHERE table_name = '{table_name.upper()}'
    """
    )
    return [row[0] for row in r]


reserverd_words = {
    "ABORT",
    "ACCEPT",
    "ACCESS",
    "ADD",
    "ADMIN",
    "AFTER",
    "ALL",
    "ALLOCATE",
    "ALTER",
    "ANALYZE",
    "AND",
    "ANY",
    "ARCHIVE",
    "ARCHIVELOG",
    "ARRAY",
    "ARRAYLEN",
    "AS",
    "ASC",
    "ASSERT",
    "ASSIGN",
    "AT",
    "AUDIT",
    "AUTHORIZATION",
    "AVG",
    "BACKUP",
    "BASE_TABLE",
    "BECOME",
    "BEFORE",
    "BEGIN",
    "BETWEEN",
    "BINARY_INTEGER",
    "BLOCK",
    "BODY",
    "BOOLEAN",
    "BY",
    "CACHE",
    "CANCEL",
    "CASCADE",
    "CASE",
    "CHANGE",
    "CHAR",
    "CHARACTER",
    "CHAR_BASE",
    "CHECK",
    "CHECKPOINT",
    "CLOSE",
    "CLUSTER",
    "CLUSTERS",
    "COBOL",
    "COLAUTH",
    "COLUMN",
    "COLUMNS",
    "COMMENT",
    "COMMIT",
    "COMPILE",
    "COMPRESS",
    "CONNECT",
    "CONSTANT",
    "CONSTRAINT",
    "CONSTRAINTS",
    "CONTENTS",
    "CONTINUE",
    "CONTROLFILE",
    "COUNT",
    "CRASH",
    "CREATE",
    "CURRENT",
    "CURRVAL",
    "CURSOR",
    "CYCLE",
    "DATABASE",
    "DATAFILE",
    "DATA_BASE",
    "DATE",
    "DBA",
    "DEBUGOFF",
    "DEBUGON",
    "DEC",
    "DECIMAL",
    "DECLARE",
    "DEFAULT",
    "DEFINITION",
    "DELAY",
    "DELETE",
    "DELTA",
    "DESC",
    "DIGITS",
    "DISABLE",
    "DISMOUNT",
    "DISPOSE",
    "DISTINCT",
    "DO",
    "DOUBLE",
    "DROP",
    "DUMP",
    "EACH",
    "ELSE",
    "ELSIF",
    "ENABLE",
    "END",
    "ENTRY",
    "ESCAPE",
    "EVENTS",
    "EXCEPT",
    "EXCEPTION",
    "EXCEPTIONS",
    "EXCEPTION_INIT",
    "EXCLUSIVE",
    "EXEC",
    "EXECUTE",
    "EXISTS",
    "EXIT",
    "EXPLAIN",
    "EXTENT",
    "EXTERNALLY",
    "FALSE",
    "FETCH",
    "FILE",
    "FLOAT",
    "FLUSH",
    "FOR",
    "FORCE",
    "FOREIGN",
    "FORM",
    "FORTRAN",
    "FOUND",
    "FREELIST",
    "FREELISTS",
    "FROM",
    "FUNCTION",
    "GENERIC",
    "GO",
    "GOTO",
    "GRANT",
    "GROUP",
    "GROUPS",
    "HAVING",
    "IDENTIFIED",
    "IF",
    "IMMEDIATE",
    "IN",
    "INCLUDING",
    "INCREMENT",
    "INDEX",
    "INDEXES",
    "INDICATOR",
    "INITIAL",
    "INITRANS",
    "INSERT",
    "INSTANCE",
    "INT",
    "INTEGER",
    "INTERSECT",
    "INTO",
    "IS",
    "KEY",
    "LANGUAGE",
    "LAYER",
    "LEVEL",
    "LIKE",
    "LIMITED",
    "LINK",
    "LISTS",
    "LOCK",
    "LOGFILE",
    "LONG",
    "LOOP",
    "MANAGE",
    "MANUAL",
    "MAX",
    "MAXDATAFILES",
    "MAXEXTENTS",
    "MAXINSTANCES",
    "MAXLOGFILES",
    "MAXLOGHISTORY",
    "MAXLOGMEMBERS",
    "MAXTRANS",
    "MAXVALUE",
    "MIN",
    "MINEXTENTS",
    "MINUS",
    "MINVALUE",
    "MLSLABEL",
    "MOD",
    "MODE",
    "MODIFY",
    "MODULE",
    "MOUNT",
    "NATURAL",
    "NEW",
    "NEXT",
    "NEXTVAL",
    "NOARCHIVELOG",
    "NOAUDIT",
    "NOCACHE",
    "NOCOMPRESS",
    "NOCYCLE",
    "NOMAXVALUE",
    "NOMINVALUE",
    "NONE",
    "NOORDER",
    "NORESETLOGS",
    "NORMAL",
    "NOSORT",
    "NOT",
    "NOTFOUND",
    "NOWAIT",
    "NULL",
    "NUMBER",
    "NUMBER_BASE",
    "NUMERIC",
    "O",
    "OF",
    "OFF",
    "OFFLINE",
    "OLD",
    "ON",
    "ONLINE",
    "ONLY",
    "OPEN",
    "OPTIMAL",
    "OPTION",
    "OR",
    "ORDER",
    "OTHERS",
    "OUT",
    "OWN",
    "PACKAGE",
    "PARALLEL",
    "PARTITION",
    "PCTFREE",
    "PCTINCREASE",
    "PCTUSED",
    "PLAN",
    "PLI",
    "POSITIVE",
    "PRAGMA",
    "PRECISION",
    "PRIMARY",
    "PRIOR",
    "PRIVATE",
    "PRIVILEGES",
    "PROCEDURE",
    "PROFILE",
    "PUBLIC",
    "QUOTA",
    "RAISE",
    "RANGE",
    "RAW",
    "READ",
    "REAL",
    "RECORD",
    "RECOVER",
    "REFERENCES",
    "REFERENCING",
    "RELEASE",
    "REMR",
    "RENAME",
    "RESETLOGS",
    "RESOURCE",
    "RESTRICTED",
    "RETURN",
    "REUSE",
    "REVERSE",
    "REVOKE",
    "ROLE",
    "ROLES",
    "ROLLBACK",
    "ROW",
    "ROWID",
    "ROWLABEL",
    "ROWNUM",
    "ROWS",
    "ROWTYPE",
    "RUN",
    "S",
    "SAVEPOINT",
    "SCHEMA",
    "SCN",
    "SECTION",
    "SEGMENT",
    "SELECT",
    "SEPARATE",
    "SEQUENCE",
    "SESSION",
    "SET",
    "SHARE",
    "SHARED",
    "SIZE",
    "SMALLINT",
    "SNAPSHOT",
    "SOME",
    "SORT",
    "SPACE",
    "SQL",
    "SQLBUF",
    "SQLCODE",
    "SQLERRM",
    "SQLERROR",
    "SQLSTATE",
    "START",
    "STATEMENT",
    "STATEMENT_ID",
    "STATISTICS",
    "STDDEV",
    "STOP",
    "STORAGE",
    "SUBTYPE",
    "SUCCESSFUL",
    "SUM",
    "SWITCH",
    "SYNONYM",
    "SYSDATE",
    "SYSTEM",
    "TABAUTH",
    "TABLE",
    "TABLES",
    "TABLESPACE",
    "TASK",
    "TEMPORARY",
    "TERMINATE",
    "THEN",
    "THREAD",
    "TIME",
    "TO",
    "TRACING",
    "TRANSACTION",
    "TRIGGER",
    "TRIGGERS",
    "TRUE",
    "TRUNCATE",
    "TYPE",
    "UID",
    "UNDER",
    "UNION",
    "UNIQUE",
    "UNLIMITED",
    "UNTIL",
    "UPDATE",
    "USE",
    "USER",
    "USING",
    "VALIDATE",
    "VALUES",
    "VARCHAR",
    "VARCHAR2",
    "VARIANCE",
    "VIEW",
    "VIEWS",
    "WHEN",
    "WHENEVER",
    "WHERE",
    "WHILE",
    "WITH",
    "WORK",
    "WRITE",
    "XA",
    "XOR",
}


def norm_str(k):
    K = k.replace(" ", "_").upper()
    K = K.replace(".", "")
    K = K.replace(":", "")
    K = K.replace("-", "_")
    K = K.replace("Ü", "UE")
    K = K.replace("Ö", "OE")
    K = K.replace("Ä", "AE")
    K = "".join(filter(lambda x: x in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_0123456789", K))
    assert K not in reserverd_words
    return K


def norm_cols(df):
    df.columns = [norm_str(c) for c in df.columns]


def compressed_method(disable=False, buffer_size=1e4):
    def compressed(pd_table, conn, keys, data_iter):
        table_name = pd_table.name.upper()
        if pd_table.schema:
            table_name = f"{pd_table.schema}.{pd_table.name}".upper()
        with conn.connection.cursor() as cur:
            compress_table(table_name, cur, raise_if_not_exists=False)
            columns = get_columns(table_name, cur)
            KEYS = [k.upper() for k in keys]
            if len(set(KEYS) & set(columns)) > 0:
                columns_in_keys = [c for c in columns if c in KEYS]
                ix_pos = [KEYS.index(c) for c in columns_in_keys]
                sql = f"""
                    insert /*+ append, parallel (AUTO) */ into {table_name}
                    ({', '.join(columns_in_keys)})
                    values (:{', :'.join([str(ix) for ix in range(len(columns_in_keys))])})"""
                data = []
                for d in tqdm(data_iter, disable=disable):
                    data.append([d[ix] for ix in ix_pos])
                    if len(data) >= buffer_size:
                        cur.executemany(sql, data)
                        data = []
                if len(data) > 0:
                    cur.executemany(sql, data)

    return compressed


def parallel(pd_table, conn, keys, data_iter):
    table_name = pd_table.name.upper()
    if pd_table.schema:
        table_name = f"{pd_table.schema}.{pd_table.name}".upper()
    sql = f"""
        insert /*+ parallel (AUTO) */ into {table_name}
        ({', '.join(keys)})
        values (:{', :'.join([str(ix) for ix in range(len(keys))])})
    """
    with conn.connection.cursor() as cur:
        cur.executemany(sql, list(data_iter))


def typedict(df, string_length=4000):
    return {c: String(string_length) for c, t in df.dtypes.items() if t == np.dtype("O")}
