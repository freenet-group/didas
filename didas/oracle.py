import logging
import os
import warnings
from math import ceil
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

import numpy as np
import pandas as pd
from oracle_reseved_word_list import reserverd_words
from pandas import DataFrame
from sqlalchemy import String, create_engine, inspect, types
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import DatabaseError
from sqlalchemy.sql import text
from tqdm.auto import tqdm

logger = logging.getLogger(__name__)


def get_engine(
    oracle_username: Optional[str] = None,
    oracle_password: Optional[str] = None,
    oracle_hosts: Optional[Set[str]] = None,
    oracle_port: Optional[int] = None,
    oracle_servicename: Optional[str] = None,
    **kwargs: Any,
) -> Engine:
    """
    Get an Oracle engine with the given parameters. The parameters can be empty, in which case the environment variables

    Args:
        oracle_username (Optional[str], optional): The Oracle username. Defaults to None - in which case the environment variable ORACLE_USER is used.
        oracle_password (Optional[str], optional): The Oracle password. Defaults to None - in which case the environment variable ORACLE_PASS is used.
        oracle_hosts (Optional[Set[str]], optional): The Oracle hosts. Defaults to None - in which case the environment variables ORACLE_HOST* are used.
        oracle_port (int, optional): The Oracle port. Defaults to None - in which case the environment variable ORACLE_PORT is used.
        oracle_servicename (str, optional): The Oracle service name. Defaults to None - in which case the environment variable ORACLE_SERVICE_NAME is used.
        **kwargs (Any): Additional keyword arguments to pass to the create_engine function.

    Returns:
        Engine: The Oracle engine.
    """
    oracle_username = oracle_username if oracle_username else os.environ["ORACLE_USER"]
    oracle_password = oracle_password if oracle_password else os.environ["ORACLE_PASS"]
    if oracle_hosts is None:
        oracle_hosts = {v for k, v in os.environ.items() if k.startswith("ORACLE_HOST")}
    else:
        oracle_hosts |= {v for k, v in os.environ.items() if k.startswith("ORACLE_HOST")}
    oracle_port = oracle_port if oracle_port else int(os.getenv("ORACLE_PORT", "1521"))
    oracle_servicename = oracle_servicename if oracle_servicename else os.environ["ORACLE_SERVICE_NAME"]
    assert len(oracle_hosts) > 0
    excs: Dict[str, DatabaseError] = {}
    for oracle_host in oracle_hosts:
        engine = create_engine(
            f"oracle+oracledb://{oracle_username}:{oracle_password}@{oracle_host}:{oracle_port}/?service_name={oracle_servicename}",
            **kwargs,
        )
        try:
            with engine.begin():
                return engine
        except DatabaseError as e:
            excs[oracle_host] = e
    assert False, excs


def table_size(table_name: str, cur: Any) -> int:
    """Get the size of a table in bytes."""
    r = cur.execute(
        text(
            f"""
        SELECT sum(BYTES)
        FROM DBA_SEGMENTS
        WHERE SEGMENT_NAME = '{table_name.upper()}'
        GROUP BY SEGMENT_NAME
        """
        )
    )
    try:
        return next(r)[0]
    except StopIteration:
        return 0


def compress_table(
    table_name: str,
    cur: Any,
    compress_for: str = "ARCHIVE HIGH",
    force: bool = False,
    raise_if_not_exists: bool = True,
) -> Union[float, None]:
    """
    Compress a table.

    Args:
        table_name (str): The table name.
        cur (Any): The connection cursor.
        compress_for (str, optional): The compression level. Defaults to "ARCHIVE HIGH".
        force (bool, optional): Force the compression. Defaults to False.
        raise_if_not_exists (bool, optional): Raise if the table does not exist. Defaults to True.

    Returns:
        Union[float, None]: The compression ratio.
    """
    r = cur.execute(
        text(
            f"""
        SELECT compression, compress_for
        FROM   user_tables
        WHERE  table_name = '{table_name.upper()}'
    """
        )
    )
    try:
        _, compress_for_now = next(r)
    except StopIteration:
        if raise_if_not_exists:
            raise ValueError(f"Table {table_name.upper()} does not exist")
        return None

    if compress_for_now != compress_for or force:
        size_before = table_size(table_name, cur)
        cur.execute(text(f"ALTER TABLE {table_name} MOVE COMPRESS for {compress_for}"))
        try:
            return table_size(table_name, cur) / size_before
        except ZeroDivisionError:
            return 1.0
    return 1.0


def get_columns(table_name: str, cur: Any) -> List[str]:
    """Get the columns of a table."""
    r = cur.execute(
        text(
            f"""
        SELECT column_name
        FROM all_tab_cols
        WHERE table_name = '{table_name.upper()}'
    """
        )
    )
    return [row[0] for row in r]


def norm_str(k: str) -> str:
    """Normalize a string to a valid Oracle column name."""
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


def norm_cols(df: DataFrame) -> None:
    """Normalize the columns of a DataFrame to valid Oracle column names."""

    df.columns = [norm_str(c) for c in df.columns]


def compressed_method(
    disable: bool = False, buffer_size: Union[int, float] = 1e4
) -> Callable[[pd.DataFrame, Connection, List[str], Iterator[Tuple[Any, ...]]], None]:
    """Create a method that inserts data into a table in compressed mode."""

    def compressed(pd_table: pd.DataFrame, conn: Connection, keys: List[str], data_iter: Iterator[Tuple[Any, ...]]) -> None:
        table_name = pd_table.name.upper()
        if pd_table.schema:
            table_name = f"{pd_table.schema}.{pd_table.name}".upper()
        cur = conn.connection.cursor()
        try:
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
        finally:
            cur.close()

    return compressed


def parallel(pd_table: Any, conn: Connection, keys: List[str], data_iter: Iterator[Tuple[Any, ...]]) -> None:
    warnings.warn(
        "The 'parallel' function is deprecated and will be removed in a future version. Please use 'execute_parallel_insert' or 'write_pandas_to_dwh' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return execute_parallel_insert(pd_table, conn, keys, data_iter)


def execute_parallel_insert(pd_table: Any, conn: Connection, keys: List[str], data_iter: Iterator[Tuple[Any, ...]]) -> None:
    """Insert data into a table in parallel mode."""
    table_name = pd_table.name.upper()
    if pd_table.schema:
        table_name = f"{pd_table.schema}.{pd_table.name}".upper()
    sql = f"""
        insert /*+ parallel (AUTO) */ into {table_name}
        ({', '.join(keys)})
        values (:{', :'.join([str(ix) for ix in range(len(keys))])})
    """
    cur = conn.connection.cursor()
    try:
        cur.executemany(sql, list(data_iter))
    finally:
        cur.close()


def typedict(df: DataFrame, string_length: int = 4000) -> Dict[str, String]:
    """Create a dictionary with the column names as keys and the types as values."""
    return {c: String(string_length) for c, t in df.dtypes.items() if t == np.dtype("O")}


def write_pandas_to_dwh(
    df: pd.DataFrame,
    table_name: str,
    schema: Optional[str] = None,
    create_table: bool = True,
    engine: Optional[Engine] = None,
    arraysize: int = 50000,
    compress_for: Optional[str] = None,
    grant_select_to: Optional[List[str]] = None,
) -> bool:
    """
    Write a pandas DataFrame to an Oracle table.

    Args:
        df (pd.DataFrame): The DataFrame to write.
        table_name (str): The table name to write to.
        schema (Optional[str], optional): The schema. Defaults to None.
                                          If None, the table is created in the default schema.
                                          If set, the table_name will be updated to schema.table_name.
        create_table (bool, optional): Create the table if it doesn't exist. Defaults to True.
        engine (Optional[Engine], optional): The Oracle engine. Defaults to None.
        arraysize (int, optional): The array size. Defaults to 50000.
        compress_for (Optional[str], optional): Compress the table. Defaults to None.
        grant_select_to (Optional[List[str]], optional): Grant select permissions to the given users. Defaults to None.

    Returns:
        bool: True if the operation was successful.
    """
    table_name = table_name.upper()
    df.columns = df.columns.str.upper()
    if engine is None:
        engine = get_engine(arraysize=arraysize)
    table_exists = inspect(engine).has_table(table_name)

    if table_exists and create_table:
        logger.error(f"Table {table_name} exists, please delete first.")
        return False

    elif create_table:
        d_types = {c: types.VARCHAR(min(df[c].str.len().max(), 127)) for c in df.columns[df.dtypes == "object"].tolist()}
        # Create the table if it doesn't exist
        df.head(0).to_sql(table_name, con=engine, schema=schema, if_exists="fail", index=False, dtype=d_types)
        logger.info(f"Table {table_name} created.")
        # Commit the transaction to ensure the table is created
        with engine.connect() as conn:
            conn.connection.commit()

    columns = df.columns
    column_names = ", ".join(str(c) for c in columns)
    column_values = ", ".join(f":{c}" for c in columns)

    if schema:
        table_name = f"{schema.upper()}.{table_name}"
    sql_insert = f"INSERT /*+ parallel (AUTO) */ INTO {table_name} ({column_names}) VALUES ({column_values})"
    batch_size = 100000
    number_of_batches = ceil(len(df) / batch_size)
    with engine.connect() as conn:
        cursor = conn.connection.cursor()

        for batch_df in tqdm(np.array_split(df, number_of_batches), total=number_of_batches):
            data_to_insert = batch_df.replace({np.nan: None}).to_dict(orient="records")
            try:
                cursor.executemany(sql_insert, data_to_insert)
            except Exception as e:
                logger.error(f"Failed Insert SQL: {sql_insert} with error: {e}")
                return False

            conn.connection.commit()

        if compress_for is not None:
            logger.info("Compressing table...")
            try:
                compress_table(table_name=table_name, cur=cursor, compress_for=compress_for)
            finally:
                cursor.close()
        else:
            cursor.close()
        # Optionally, grant select permissions
        if grant_select_to is not None:
            for user in grant_select_to:
                logger.info(f"Granting SELECT permissions to {user}")
                conn.execute(text(f"GRANT SELECT ON {table_name} TO {user}"))
    return True
