"""
Integration-style tests for the full NL → SQL → results pipeline.
Both OpenAI and psycopg2 are mocked, so no network/DB access is needed.
"""
import pytest
from unittest.mock import MagicMock, patch

from nl_sql.nl_to_sql import nl_to_sql
from nl_sql.query_executor import execute_query


def _openai_resp(sql: str):
    choice = MagicMock()
    choice.message.content = sql
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = None   # skip token-logging branch
    return resp


def _db_rows(rows: list[dict]):
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    cur.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn


class TestFullPipeline:
    def test_top_securities_by_issue_size(self):
        sql = 'SELECT * FROM public."PDB_isin_records" ORDER BY total_issue_size_cr DESC LIMIT 10;'
        rows = [{"isin": f"INE00{i}A07KL8", "total_issue_size_cr": 1000 - i} for i in range(10)]

        with patch("nl_sql.nl_to_sql._get_client") as mock_llm:
            mock_llm.return_value.chat.completions.create.return_value = _openai_resp(sql)
            generated_sql, llm_time = nl_to_sql("Show the top 10 securities by issue size.")

        with patch("nl_sql.query_executor._get_connection", return_value=_db_rows(rows)):
            results, db_time = execute_query(generated_sql)

        assert generated_sql == sql
        assert len(results) == 10
        assert results[0]["total_issue_size_cr"] == 1000
        assert llm_time >= 0
        assert db_time >= 0

    def test_psu_issuances_last_year(self):
        sql = ('SELECT ir.*, io.issuer_name '
               'FROM public."PDB_isin_records" ir '
               'JOIN public."PDB_issuer_organization" io ON ir.issuer_organization_id = io.id '
               'JOIN public."PDB_tag" t ON ir.id = t.isin_id '
               'JOIN public."PDB_payin" p ON ir.id = p.isin_id '
               "WHERE t.tag = 'PSU' AND p.payin_date >= CURRENT_DATE - INTERVAL '1 year' "
               "GROUP BY ir.id, io.issuer_name LIMIT 10;")
        rows = [{"isin": "INE001A07KL8", "issuer_name": "NABARD"}]

        with patch("nl_sql.nl_to_sql._get_client") as mock_llm:
            mock_llm.return_value.chat.completions.create.return_value = _openai_resp(sql)
            generated_sql, _ = nl_to_sql("List PSU issuances in the last 1 year.")

        with patch("nl_sql.query_executor._get_connection", return_value=_db_rows(rows)):
            results, _ = execute_query(generated_sql)

        assert "PSU" in generated_sql
        assert results[0]["issuer_name"] == "NABARD"

    def test_count_frb_returns_single_row(self):
        sql = ('SELECT COUNT(DISTINCT ir.id) FROM public."PDB_isin_records" ir '
               "JOIN public.\"PDB_tag\" t ON ir.id = t.isin_id WHERE t.tag ILIKE '%FRB%';")
        rows = [{"count": 128}]

        with patch("nl_sql.nl_to_sql._get_client") as mock_llm:
            mock_llm.return_value.chat.completions.create.return_value = _openai_resp(sql)
            generated_sql, _ = nl_to_sql("How many floating rate bonds are in the system?")

        with patch("nl_sql.query_executor._get_connection", return_value=_db_rows(rows)):
            results, _ = execute_query(generated_sql)

        assert "COUNT" in generated_sql.upper()
        assert len(results) == 1
        assert results[0]["count"] == 128

    def test_maturing_next_month(self):
        sql = ('SELECT ir.* FROM public."PDB_isin_records" ir '
               'JOIN public."PDB_redemption" r ON ir.id = r.isin_id '
               "WHERE r.redemption_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '1 month' "
               "LIMIT 10;")

        with patch("nl_sql.nl_to_sql._get_client") as mock_llm:
            mock_llm.return_value.chat.completions.create.return_value = _openai_resp(sql)
            generated_sql, _ = nl_to_sql("List ISINs that are maturing in the next one month.")

        assert "CURRENT_DATE" in generated_sql
        assert "redemption_date" in generated_sql

    def test_perpetual_bonds_with_call_before_2030(self):
        sql = ("SELECT * FROM public.\"PDB_isin_records\" "
               "WHERE seniority = 'Perpetual' AND call_option_date IS NOT NULL "
               "AND call_option_date < DATE '2030-01-01' LIMIT 10;")

        with patch("nl_sql.nl_to_sql._get_client") as mock_llm:
            mock_llm.return_value.chat.completions.create.return_value = _openai_resp(sql)
            generated_sql, _ = nl_to_sql(
                "Identify perpetual bonds whose call option date is before 2030."
            )

        assert "Perpetual" in generated_sql
        assert "call_option_date" in generated_sql

    def test_db_error_propagates(self):
        conn = MagicMock()
        cur = MagicMock()
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        cur.execute.side_effect = Exception("relation does not exist")
        conn.cursor.return_value = cur

        with patch("nl_sql.query_executor._get_connection", return_value=conn):
            with pytest.raises(Exception, match="relation does not exist"):
                execute_query("SELECT * FROM nonexistent_table;")

    def test_timing_both_components(self):
        sql = 'SELECT * FROM public."PDB_isin_records" LIMIT 1;'
        rows = [{"isin": "INE001A07KL8"}]

        with patch("nl_sql.nl_to_sql._get_client") as mock_llm:
            mock_llm.return_value.chat.completions.create.return_value = _openai_resp(sql)
            _, llm_time = nl_to_sql("Show one ISIN")

        with patch("nl_sql.query_executor._get_connection", return_value=_db_rows(rows)):
            _, db_time = execute_query(sql)

        assert llm_time >= 0
        assert db_time >= 0
