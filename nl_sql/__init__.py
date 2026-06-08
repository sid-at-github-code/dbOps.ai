"""
NL-to-SQL package — public API.

    from nl_sql import nl_to_sql, execute_query, validate_read_only

    sql, t1 = nl_to_sql("How many users signed up last month?")
    rows, t2 = execute_query(sql)
"""

from nl_sql.nl_to_sql import nl_to_sql
from nl_sql.query_executor import execute_query
from nl_sql.sql_validator import validate_read_only

__all__ = ["nl_to_sql", "execute_query", "validate_read_only"]
