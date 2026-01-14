#! /usr/bin/env python3

import json
import urllib.parse
from multiprocessing import Lock, Value
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, List, Tuple, Union

from _tool_helpers import print_debug, print_error, print_info, print_warning

SUPPORTED_DBS = (
    "AURORAPOSTGRESQL",
    "MSSQL",
    "MYSQL",
    "OCI",
    "POSTGRESQL",
    "SQLITE3",
)


class SzDatabase:
    _aurora_clean_up_msg_flag = Value("b", False)
    _aurora_clean_up_msg_lock = Lock()

    @classmethod
    def get_aurora_clean_up_msg_flag(cls):
        with cls._aurora_clean_up_msg_lock:
            return cls._aurora_clean_up_msg_flag.value

    @classmethod
    def set_aurora_clean_up_msg_flag(cls, value):
        cls._aurora_clean_up_msg_flag.value = value

    def __init__(
        self,
        engine_configuration: Union[Dict[str, Any], str],
        debug: bool = False,
        print_import_messages: bool = True,
    ) -> None:
        self.connections = {"MAIN": {}}
        self.connection_string = ""
        self.main_db_type = ""
        self.debug = debug
        self.print_import_messages = print_import_messages
        self.statement_cache = {}
        self.success = False
        self.tables_by_connection = {}

        self.aws_wrapper: ModuleType | None = None
        self.cx_oracle: ModuleType | None = None
        self.mssql_connect: Callable[..., Any] | None = None
        self.mysql_connector: ModuleType | None = None
        self.psycopg_connection: ModuleType | None = None
        self.psycopg2: ModuleType | None = None
        self.pyodbc: ModuleType | None = None
        self.sqlite3: ModuleType | None = None

        self.imported_aws_wrapper = False
        self.imported_aws_wrapper_error: ImportError | None = None
        self.imported_cx_oracle = False
        self.imported_cx_oracle_error: ImportError | None = None
        self.imported_mssql = False
        self.imported_mssql_error: ImportError | None = None
        self.imported_mysql = False
        self.imported_mysql_error: ImportError | None = None
        self.imported_psycopg = False
        self.imported_psycopg_error: ImportError | None = None
        self.imported_psycopg2 = False
        self.imported_psycopg2_error: ImportError | None = None
        self.imported_pyodbc = False
        self.imported_pyodbc_error: ImportError | None = None
        self.imported_sqlite3 = False
        self.imported_sqlite3_error: ImportError | None = None

        if isinstance(engine_configuration, str):
            try:
                engine_configuration = json.loads(engine_configuration)
            except json.JSONDecodeError as err:
                print("ERROR: trying to parse connection settings as JSON", flush=True)
                raise err

        # # Check early if there is the expected stanza and supported DB type
        if not (connection_string := engine_configuration.get("SQL").get("CONNECTION")):
            raise LookupError(f"Database connection settings appear to be missing or invalid")

        self.main_db_type, _ = connection_string.split("://") if "://" in connection_string else ("UNKNOWN_DB", "")
        if (main_db_type_upper := self.main_db_type.upper()) not in SUPPORTED_DBS:
            raise LookupError(f"Unsupported database type: {self.main_db_type}")

        self.connection_string = connection_string
        self.imports(main_db_type_upper, "MAIN")
        self.dburi_parse("MAIN", self.connection_string)
        self.connect("MAIN")

        for table_name in engine_configuration.get("HYBRID", {}).keys():
            node = engine_configuration["HYBRID"][table_name]  # type: ignore
            if node not in self.connections:
                self.connections[node] = {}
                # self.connect(node, engine_configuration[node]["DB_1"])
            self.tables_by_connection[table_name] = node

        self.success = True

    def connect(self, node: str) -> None:
        """Connect to the database defined in the connection string in the Senzing Engine Configuration"""
        try:
            if self.connections[node]["dbtype"] == "AURORAPOSTGRESQL":
                if self.connections[node]["iam_auth"]:
                    if self.debug:
                        print_debug("Using AWS Advanced Wrapper with IAM authentication", end_str="\n")

                    self.connections[node]["dbo"] = self.aws_wrapper.connect(
                        self.psycopg_connection.connect,
                        host=self.connections[node]["host"],
                        database=self.connections[node]["dsn"],
                        iam_region=self.connections[node]["region"],
                        user=self.connections[node]["userid"],
                        plugins="iam",
                        wrapper_dialect="aurora-pg",
                        autocommit=True,
                    )

                    # NOTE Tried using the AWS driver for password authentication but it caused errors when used, psycopg2
                    # NOTE is used for password for now.
                    # Connect using password authentication when iam_auth == False
                    # if not self.connections[node]["iam_auth"]:
                    #     if self.debug:
                    #         print_debug("Using AWS Advanced Wrapper - with password", end_str="\n")

                    #     self.connections[node]["dbo"] = self.aws_wrapper.connect(
                    #         self.psycopg_connection.connect,
                    #         host=self.connections[node]["host"],
                    #         database=self.connections[node]["dsn"],
                    #         user=self.connections[node]["userid"],
                    #         password=self.connections[node]["password"],
                    #         wrapper_dialect="aurora-pg",
                    #         autocommit=True,
                    #     )

                else:
                    if self.debug:
                        print_debug(
                            "Using psycopg2 with password authentication",
                            end_str="\n",
                        )

                    self.connections[node]["dbo"] = self.psycopg2.connect(
                        host=self.connections[node]["host"],
                        port=self.connections[node]["port"],
                        dbname=self.connections[node]["dsn"],
                        user=self.connections[node]["userid"],
                        password=self.connections[node]["password"],
                    )
                    self.connections[node]["dbo"].set_session(autocommit=True)

            if self.connections[node]["dbtype"] == "POSTGRESQL":
                if self.imported_psycopg2:
                    if self.debug:
                        print_debug("Using psycopg2", end_str="\n")

                    options = (
                        (f"-c search_path={self.connections[node]['schema']}")
                        if self.connections[node].get("schema")
                        else ""
                    )

                    self.connections[node]["dbo"] = self.psycopg2.connect(
                        host=self.connections[node]["host"],
                        port=self.connections[node]["port"],
                        dbname=self.connections[node]["dsn"],
                        user=self.connections[node]["userid"],
                        password=self.connections[node]["password"],
                        options=options,
                    )
                    self.connections[node]["dbo"].set_session(autocommit=True)
                else:
                    if self.debug:
                        print_debug("Using pyodbc", end_str="\n")

                    conn_str = (
                        f"DRIVER={{{self.connections[node]['dbtype']}}};"
                        f"SERVER={self.connections[node]['host']};"
                        f"PORT={self.connections[node]['port']};"
                        f"DATABASE={self.connections[node]['dsn']};"
                        f"UID={self.connections[node]['userid']};"
                        f"PWD={self.connections[node]['password']};"
                        "autocommit=True"
                    )
                    if self.connections[node].get("schema"):
                        conn_str = f"{conn_str};search_path={self.connections[node]['schema']}"

                    self.connections[node]["dbo"] = self.pyodbc.connect(conn_str)

            if self.connections[node]["dbtype"] == "MYSQL":
                # NOTE Errors with MYSQL connector using next and previous in sz_explorer, only pyodbc support currently
                # # if self.mysql_connector:
                # if self.imported_mysql:
                #     if self.debug:
                #         print_debug("Using MYSQL connector", end_str="\n")

                #     connector_config = {
                #         "host": self.connections[node]["host"],
                #         "port": self.connections[node]["port"],
                #         "database": self.connections[node]["schema"],
                #         "user": self.connections[node]["userid"],
                #         "password": self.connections[node]["password"],
                #         "autocommit": True,
                #     }
                #     self.connections[node]["dbo"] = self.mysql_connector.connect(**connector_config)
                # else:
                #     if self.debug:
                #         print_debug("Using pyodbc", end_str="\n")

                #     conn_str = (
                #         f"DRIVER={{{self.connections[node]['dbtype']}}};"
                #         f"Server={self.connections[node]['host']};"
                #         f"Port={self.connections[node]['port']};"
                #         f"Database={self.connections[node]['schema']};"
                #         f"Uid={self.connections[node]['userid']};"
                #         f"Pwd={self.connections[node]['password']};"
                #         f"autocommit=True"
                #     )
                #     self.connections[node]["dbo"] = self.pyodbc.connect(conn_str)
                if self.debug:
                    print_debug("Using pyodbc", end_str="\n")

                conn_str = (
                    f"DRIVER={{{self.connections[node]['dbtype']}}};"
                    f"Server={self.connections[node]['host']};"
                    f"Port={self.connections[node]['port']};"
                    f"Database={self.connections[node]['schema']};"
                    f"Uid={self.connections[node]['userid']};"
                    f"Pwd={self.connections[node]['password']};"
                    f"autocommit=True"
                )
                self.connections[node]["dbo"] = self.pyodbc.connect(conn_str)

            if self.connections[node]["dbtype"] == "MSSQL":
                # Python connector for engine config: CONNECTION=mssql://username:password@server:port:database/?driver=mssqldriver
                if not self.connections[node]["host"] == self.connections[node]["dsn"] and self.connections[node][
                    "query_params"
                ].get("driver"):
                    if self.debug:
                        print_debug("Using MSSQL connector", end_str="\n")

                    conn_str = (
                        f"SERVER={self.connections[node]['host']},{self.connections[node]['port']};"
                        f"DATABASE={self.connections[node]['dsn']};"
                        f"UID={self.connections[node]['userid']};"
                        f"PWD={self.connections[node]['password']}"
                    )

                    if self.connections[node]["query_params"]:
                        conn_str = self.append_uri_query_params(
                            conn_str, self.connections[node]["query_params"], ["driver"]
                        )

                    self.connections[node]["dbo"] = self.mssql_connect(conn_str)  # type: ignore

                # pyodbc for engine config: CONNECTION=mssql://username:password@database
                else:
                    if self.debug:
                        print_debug("Using pyodbc", end_str="\n")

                    conn_str = (
                        f"DSN={{{self.connections[node]['dsn']}}};"
                        f"UID={self.connections[node]['userid']};"
                        f"PWD={self.connections[node]['password']};"
                    )

                    if self.connections[node]["query_params"]:
                        conn_str = self.append_uri_query_params(conn_str, self.connections[node]["query_params"])

                    self.connections[node]["dbo"] = self.pyodbc.connect(conn_str)

            if self.connections[node]["dbtype"] == "SQLITE3":
                if self.debug:
                    print_debug("Using sqlite3", end_str="\n")

                if not Path(self.connections[node]["dsn"]).is_file():
                    raise Exception(f"ERROR: sqlite3 database file not found {self.connections[node]['dsn']}")

                self.connections[node]["dbo"] = self.sqlite3.connect(
                    self.connections[node]["dsn"], isolation_level=None
                )
                self.connections[node]["dbo"].text_factory = str
                c = self.connections[node]["dbo"].cursor()
                c.execute("PRAGMA journal_mode=wal")
                c.execute("PRAGMA synchronous=0")

            if self.connections[node]["dbtype"] == "OCI":
                self.connections[node]["dbo"] = self.cx_Oracle.connect(
                    user=self.connections[node]["userid"],
                    password=self.connections[node]["password"],
                    dsn=f"{self.connections[node]['host']}:{self.connections[node]['port']}/{self.connections[node]['schema']}",
                    encoding="UTF-8",
                )

        except Exception as err:
            raise Exception(err)

        if self.connections[node]["schema"] is not None and len(self.connections[node]["schema"]) != 0:
            if self.connections[node]["dbtype"] == "SQLITE3":
                raise Exception("""WARNING: SQLITE3 doesn't support schema URI argument""")
            try:
                if self.connections[node]["dbtype"] == "MYSQL":
                    self.sql_exec("use " + self.connections[node]["schema"])
                if self.connections[node]["dbtype"] in ("AURORAPOSTGRESQL", "POSTGRESQL"):
                    self.sql_exec("SET search_path TO " + self.connections[node]["schema"])
            except Exception as err:
                raise Exception(err)

    def set_node(self, sql: str) -> str:
        if len(self.connections) == 1:
            return "MAIN"

        node_list = []
        for table in self.tables_in_query(sql):
            node_list.append(self.tables_by_connection.get(table.upper(), "MAIN"))

        if len(node_list) == 0:
            raise Exception(f"Could not determine tables from sql statement: {sql}")
        if len(set(node_list)) > 1:
            raise Exception(
                f"Cannot query across nodes in hybrid setup\n{sql}\n{self.tables_in_query(sql)}\n{node_list}"
            )
        return node_list[0]

    def tables_in_query(self, sql: str) -> List[str]:
        result = []
        tokens = sql.split()
        i = 0
        while True:
            if tokens[i].upper() in ("FROM", "JOIN"):
                i += 1
                result.append(tokens[i])
            i += 1
            if i >= len(tokens):
                break
        return result

    def close(self) -> None:
        """
        Close database connections

        NOTE: Logic for Aurora is because the connector (https://github.com/aws/aws-advanced-python-wrapper
              currently v1.4.0 takes a minute or 2 to free up the connection resources and it makes it look
              like sz_explorer and sz_snapshot hang. This prints a single message notifying users this is
              expected. Moreover, without calling release_resources() when the connector does exit it outputs
              a trace stack that mentions it ignored an exception; must call release_resources().
        """
        for node in self.connections.keys():
            self.connections[node]["dbo"].close()

        # Check if ANY connection is Aurora PostgreSQL
        if any(conn["dbtype"] == "AURORAPOSTGRESQL" and conn["iam_auth"] for conn in self.connections.values()):
            # Double-checked locking to print message only once across processes
            if not SzDatabase.get_aurora_clean_up_msg_flag():
                with SzDatabase._aurora_clean_up_msg_lock:
                    if not SzDatabase._aurora_clean_up_msg_flag.value:
                        SzDatabase._aurora_clean_up_msg_flag.value = True
                        print_info(
                            "Cleaning up Aurora database resources, this can take a minute or two...", end_str="\n"
                        )

            # Release resources for all Aurora nodes with IAM auth
            for node in self.connections.keys():
                if self.connections[node]["dbtype"] == "AURORAPOSTGRESQL" and self.connections[node]["iam_auth"]:
                    self.connections[node]["dbo"].release_resources()

    def sql_prep(self, sql: str, return_node: bool = False) -> Union[str, Tuple[str, str]]:
        node = self.set_node(sql)

        if (
            (self.main_db_type.upper() == "POSTGRESQL" and self.imported_psycopg2)
            or self.main_db_type.upper() == "AURORAPOSTGRESQL"
            # or (self.main_db_type.upper() == "MYSQL" and self.imported_mysql)
        ):
            sql = sql.replace("?", "%s")
        elif self.connections[node]["dbtype"] == "OCI":
            i = 0
            while "?" in sql:
                i += 1
                sql = sql.replace("?", f":{i}", 1)

        if return_node:
            return sql, node
        return sql

    def sql_exec(self, raw_sql: str, param_list=None, **kwargs):
        """Make a database call"""
        if raw_sql in self.statement_cache:
            sql = self.statement_cache[raw_sql]["sql"]
            node = self.statement_cache[raw_sql]["node"]
        else:
            sql, node = self.sql_prep(raw_sql, return_node=True)  # type: ignore
            self.statement_cache[raw_sql] = {"sql": sql, "node": node}

        if param_list and type(param_list) not in (list, tuple):
            param_list = [param_list]

        # --name and itersize are postgres server side cursor settings
        cursor_data = {}
        cursor_data["NAME"] = kwargs["name"] if "name" in kwargs else None
        cursor_data["ITERSIZE"] = kwargs["itersize"] if "itersize" in kwargs else None

        try:
            # if cursorData["NAME"] and self.connections[node]["psycopg2"]:
            if (
                cursor_data["NAME"]
                and self.main_db_type.upper() in ("AURORAPOSTGRESQL", "POSTGRESQL")
                and self.imported_psycopg2
            ):
                exec_cursor = self.connections[node]["dbo"].cursor(cursor_data["NAME"])
                if cursor_data["ITERSIZE"]:
                    exec_cursor.itersize = cursor_data["ITERSIZE"]
            else:
                exec_cursor = self.connections[node]["dbo"].cursor()
            if param_list:
                exec_cursor.execute(sql, param_list)
            else:
                exec_cursor.execute(sql)
        except Exception as err:
            raise Exception(f"sqlerror: {err} - {sql}")

        if exec_cursor:
            cursor_data["CURSOR"] = exec_cursor
            cursor_data["ROWS_AFFECTED"] = exec_cursor.rowcount
            if exec_cursor.description:
                cursor_data["COLUMN_HEADERS"] = [columnData[0].upper() for columnData in exec_cursor.description]

        return cursor_data

    def fetch_next(self, cursor_data):
        """Fetch the next row from a cursor"""
        if "COLUMN_HEADERS" in cursor_data:
            row_values = cursor_data["CURSOR"].fetchone()
            if row_values:
                type_fixed_row = tuple([el.decode("utf-8") if type(el) is bytearray else el for el in row_values])
                row_data = dict(list(zip(cursor_data["COLUMN_HEADERS"], type_fixed_row)))
            else:
                row_data = None
        else:
            raise Exception("WARNING: Previous SQL was not a query.")

        return row_data

    def fetch_row(self, cursor_data):
        """Fetch the next row from a cursor"""
        if "COLUMN_HEADERS" in cursor_data:
            row_data = cursor_data["CURSOR"].fetchone()
        else:
            raise Exception("WARNING: Previous SQL was not a query.")

        return row_data

    def fetch_all_rows(self, cursor_data):
        """Fetch all the rows without column names"""
        return cursor_data["CURSOR"].fetchall()

    def fetch_all_dicts(self, cursor_data):
        """Fetch all the rows with column names"""
        row_list = []
        for row_values in cursor_data["CURSOR"].fetchall():
            type_fixed_row = tuple([el.decode("utf-8") if type(el) is bytearray else el for el in row_values])
            row_data = dict(list(zip(cursor_data["COLUMN_HEADERS"], type_fixed_row)))
            row_list.append(row_data)

        return row_list

    def fetch_many_rows(self, cursor_data, row_count):
        """Fetch all the rows without column names"""
        return cursor_data["CURSOR"].fetchmany(row_count)

    def fetch_many_dicts(self, cursor_data, row_count):
        """Fetch all the rows with column names"""
        row_list = []
        for row_values in cursor_data["CURSOR"].fetchmany(row_count):
            type_fixed_row = tuple([el.decode("utf-8") if type(el) is bytearray else el for el in row_values])
            row_data = dict(list(zip(cursor_data["COLUMN_HEADERS"], type_fixed_row)))
            row_list.append(row_data)

        return row_list

    def dburi_parse(self, node: str, db_uri: str) -> None:
        """Parse the database URI"""
        uri_dict: dict[str, Any] = {}

        try:
            uri_dict["TABLE"] = uri_dict["SCHEMA"] = uri_dict["PORT"] = uri_dict["DBURI_PARMS"] = uri_dict[
                "IAM_AUTH"
            ] = uri_dict["REGION"] = None

            db_uri_parse = urllib.parse.urlparse(db_uri)
            db_uri_query_dict = urllib.parse.parse_qs(db_uri_parse.query)
            uri_dict["DBTYPE"] = db_uri_parse.scheme.upper()
            uri_dict["HOST"] = db_uri_parse.hostname
            uri_dict["PASSWORD"] = db_uri_parse.password
            uri_dict["USERID"] = db_uri_parse.username

            # Collect parameters for decisions if any supplied
            db_uri_query_dict_copy = db_uri_query_dict.copy()
            for query_key, query_value in db_uri_query_dict_copy.items():
                query_key_lower = query_key.lower()
                last_query_value = query_value[-1]

                # Remove keys/values for the engine not to be sent to DB drivers as parameters
                if query_key_lower == "table":
                    uri_dict["TABLE"] = last_query_value
                    db_uri_query_dict.pop(query_key)

                if query_key_lower == "schema":
                    uri_dict["SCHEMA"] = last_query_value
                    db_uri_query_dict.pop(query_key)

                if query_key_lower == "iam_auth":
                    uri_dict["IAM_AUTH"] = True if last_query_value.lower() == "true" else False
                    db_uri_query_dict.pop(query_key)

                if query_key_lower == "region":
                    uri_dict["REGION"] = last_query_value
                    db_uri_query_dict.pop(query_key)

                uri_dict["QUERY_PARAMS"] = db_uri_query_dict

            # SQLITE3
            if uri_dict["DBTYPE"] == "SQLITE3":
                uri_dict["DSN"] = db_uri_parse.path

            netloc_split = db_uri_parse.netloc.split(":")

            if uri_dict["DBTYPE"] in ("AURORAPOSTGRESQL", "POSTGRESQL"):
                if len(netloc_split) < 4:
                    # Without password using iam_auth
                    # "CONNECTION":"aurorapostgresql://user@host:port:db/?iam_auth=true&region=us-east-2"
                    uri_dict["DSN"] = netloc_split[2]
                    uri_dict["PORT"] = netloc_split[1]
                else:
                    # With password
                    # "CONNECTION":"aurorapostgresql://user:password@host:port:db/?iam_auth=false&region=us-east-2"
                    uri_dict["DSN"] = netloc_split[3]
                    uri_dict["PORT"] = netloc_split[2]

            if uri_dict["DBTYPE"] == "MYSQL":
                uri_dict["DSN"] = uri_dict["SCHEMA"]
                uri_dict["PORT"] = netloc_split[2]

            if uri_dict["DBTYPE"] == "MSSQL":
                if len(netloc_split) < 4:  # CONNECTION=mssql://user:password@db
                    uri_dict["DSN"] = db_uri_parse.hostname
                else:  # CONNECTION=mssql://user:password@host:port:db/?TrustServerCertificate=yes
                    uri_dict["DSN"] = netloc_split[3]
                    uri_dict["PORT"] = netloc_split[2]

        except (IndexError, ValueError) as err:
            raise Exception(f"Failed to parse connection URI, check the engine settings: {err}") from err

        if not uri_dict["DSN"]:
            raise Exception("Missing database DSN")

        self.connections[node]["dbtype"] = uri_dict.get("DBTYPE", None)
        self.connections[node]["dsn"] = uri_dict.get("DSN", None)
        self.connections[node]["host"] = uri_dict.get("HOST", None)
        self.connections[node]["port"] = uri_dict.get("PORT", None)
        self.connections[node]["userid"] = urllib.parse.unquote(uri_dict["USERID"]) if "USERID" in uri_dict else None
        # Might not have password for AURORAPOSTGRESQL and iam_auth=true
        self.connections[node]["password"] = (
            urllib.parse.unquote(uri_dict["PASSWORD"]) if "PASSWORD" in uri_dict and uri_dict["PASSWORD"] else None
        )
        self.connections[node]["table"] = uri_dict.get("TABLE", None)
        self.connections[node]["schema"] = uri_dict.get("SCHEMA", None)
        self.connections[node]["iam_auth"] = uri_dict.get("IAM_AUTH", None)
        self.connections[node]["region"] = uri_dict.get("REGION", None)
        self.connections[node]["query_params"] = uri_dict.get("QUERY_PARAMS", {})

    def imports(self, db_type: str, node: str) -> None:
        """Import module(s) required for the database type"""
        if self.debug:
            print_debug(f"Database type: {db_type}", end_str="")
            print_debug(f"Node: {node}", end_str="\n")

        if db_type in ("AURORAPOSTGRESQL", "POSTGRESQL"):
            if db_type == "POSTGRESQL":
                self.import_psycopg2()
                if not self.imported_psycopg2:
                    self.import_pyodbc()

                if not self.imported_psycopg2 and not self.imported_pyodbc:
                    if self.print_import_messages:
                        print_error(f"Could not import either psycopg2 or pyodbc for database access", end_str="")
                        print_error(f"  psycopg2 import error: {self.imported_psycopg2_error}", end_str="")
                        print_error(f"  pyodbc import error: {self.imported_pyodbc_error}", end_str="\n")
                    raise ImportError

                if not self.imported_psycopg2:
                    if self.print_import_messages:
                        print_warning(
                            f"Could not import psycopg2, trying pyodbc as a backup (ideally install psycopg2): {self.imported_psycopg2_error}",
                            end_str="\n",
                        )

            # NOTE Tried using the AWS driver for password authentication but it caused errors when used, psycopg2
            # NOTE is used for password for now.
            if db_type == "AURORAPOSTGRESQL":
                if "iam_auth=true" in self.connection_string.lower():
                    self.import_aws_wrapper()
                    if self.imported_aws_wrapper:
                        self.import_psycopg()

                    if not self.imported_aws_wrapper or not self.imported_psycopg:
                        print_error(
                            f"Could not import either AWS connector and/or psycopg for database access, these are required for IAM authentication",
                            end_str="",
                        )
                        print_error(f"  AWS connector import error: {self.imported_aws_wrapper_error}", end_str="")
                        print_error(f"  psycopg import error: {self.imported_psycopg_error}", end_str="\n")
                        raise ImportError
                else:
                    self.import_psycopg2()

                    if not self.imported_psycopg2:
                        raise ImportError(
                            f"Could not import psycopg2 for database access, this is required for password authentication: {self.imported_psycopg2_error}"
                        )

        elif db_type in ("MSSQL"):
            self.import_mssql()
            self.import_pyodbc()

            if not self.imported_mssql and not self.imported_pyodbc:
                print_error(
                    f"Could not import either mssql-python connector or pyodbc for database access",
                    end_str="",
                )
                print_error(f"mssql-python connector import error: {self.imported_mssql_error}", end_str="")
                print_error(f"pyodbc import error: {self.imported_pyodbc_error}", end_str="\n")
                raise ImportError

            # Connection strings for MSSQL can be either for TCP or DSN, check which is specified and check for required modules
            connection_string_len = len(self.connection_string.split(":"))
            if connection_string_len <= 3 and not self.imported_pyodbc:
                print_error(
                    f"Could not import pyodbc for database access and the connection string appears to be using a DSN",
                    end_str="",
                )
                print_error(f"pyodbc import error: {self.imported_pyodbc_error}", end_str="\n")
                raise ImportError

            if connection_string_len > 3 and not self.imported_mssql:
                print_error(
                    f"Could not import mssql-python connector for database access and the connection string appears to be using TCP not DSN",
                    end_str="",
                )
                print_error(f"mssql-python connector import error: {self.imported_mssql_error}", end_str="\n")
                raise ImportError

        elif db_type == "MYSQL":
            # NOTE Errors with MYSQL connector using next and previous in sz_explorer, only pyodbc support currently
            # self.import_mysql_connector()
            self.import_pyodbc()

            # if not self.imported_mysql and not self.imported_pyodbc:
            #     print_error(
            #         f"Could not import either MySQL connector or pyodbc for database access",
            #         end_str="",
            #     )
            #     print_error(f"MySQL connector import error: {self.imported_mysql_error}", end_str="")
            #     print_error(f"pyodbc import error: {self.imported_pyodbc_error}", end_str="\n")
            #     raise ImportError

            # if not self.imported_mysql:
            #     print_warning(
            #         f"Could not import MySQL connector, trying pyodbc as a backup (ideally install MySQL connector): {self.imported_mysql_error}",
            #         end_str="\n",
            #     )

            if not self.imported_pyodbc:
                raise ImportError(f"Could not import pyodbc for database access: {self.imported_pyodbc_error}")

        elif db_type == "OCI":
            self.import_cx_oracle()

            if not self.imported_cx_oracle:
                print_error(f"Could not import cx_Oracle for database access", end_str="")
                print_error(f"cx_Oracle import error: {self.imported_cx_oracle_error}", end_str="")
                raise ImportError

        elif db_type == "SQLITE3":
            self.import_sqlite3()

            if not self.imported_sqlite3:
                print_error(f"Could not import sqlite3 for database access", end_str="")
                print_error(f"sqlite3 import error: {self.imported_sqlite3_error}", end_str="")
                raise ImportError

    # pylint: disable=C0415
    def import_aws_wrapper(self):
        """Try and import AWS Python wrapper"""
        try:
            from aws_advanced_python_wrapper import AwsWrapperConnection

            self.aws_wrapper = AwsWrapperConnection
            self.imported_aws_wrapper = True
        except ImportError as err:
            self.imported_aws_wrapper_error = err

    def import_psycopg(self):
        """Try and import psycopg"""
        try:
            from psycopg import Connection

            self.psycopg_connection = Connection
            self.imported_psycopg = True
        except ImportError as err:
            self.imported_psycopg_error = err

    def import_cx_oracle(self):
        """Try and import cx_oracle"""
        try:
            import cx_Oracle

            self.cx_oracle = cx_Oracle
            self.imported_cx_oracle = True
        except ImportError as err:
            self.imported_cx_oracle_error = err

    def import_mssql(self):
        """Try and import mssql_python"""
        try:
            from mssql_python import connect as mssql_connect

            self.mssql_connect = mssql_connect
            self.imported_mssql = True
        except ImportError as err:
            self.imported_mssql_error = err

    def import_mysql_connector(self):
        """Try and import mysql_connector"""
        try:
            import mysql.connector

            self.mysql_connector = mysql.connector
            self.imported_mysql = True
        except ImportError as err:
            self.imported_mysql_error = err

    def import_psycopg2(self):
        """Try and import psycopg2"""
        try:
            import psycopg2  # type: ignore

            self.psycopg2 = psycopg2
            self.imported_psycopg2 = True
        except ImportError as err:
            self.imported_psycopg2_error = err

    def import_pyodbc(self):
        """Try and import pyodbc"""
        try:
            import pyodbc

            self.pyodbc = pyodbc
            self.imported_pyodbc = True
        except ImportError as err:
            self.imported_pyodbc_error = err

    def import_sqlite3(self):
        """Try and import sqlite3"""
        try:
            import sqlite3

            self.sqlite3 = sqlite3
            self.imported_sqlite3 = True
        except ImportError as err:
            self.imported_sqlite3_error = err

    # pylint: enable=C0415

    def append_uri_query_params(
        self, string_to_append: str, params_dict: Dict[str, str], keys_to_ignore: List[str] | None = None
    ) -> str:
        """
        Add any query parameters to connection strings when specified, for example with:

        CONNECTION=mssql://senzing:Password787@localhost:1433:G2/?driver=mssqldriver&TrustServerCertificate=yes

        Add ";TrustServerCertificate=yes" but not ";driver=mssqldriver" if keys_to_ignore is ["driver"]. Resulting
        connection string would be similar to:

        "SERVER=localhost,1433;DATABASE=G2;UID=senzing;PWD=Password;TrustServerCertificate=yes"
        """
        keys_to_ignore = keys_to_ignore or []

        string_to_append += "".join(
            f";{k}={v_list[0]}" for k, v_list in params_dict.items() if v_list and k not in keys_to_ignore
        )

        return string_to_append
