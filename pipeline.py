import os
import sys
from textwrap import dedent

import psycopg2
from dotenv import load_dotenv
from openai import OpenAI

from retriever import retrieve_context


SYSTEM_PROMPT = dedent("""\
    You are a PostgreSQL expert. Your task is to convert a user's natural-language
    question into a SINGLE valid SQL query that answers it.

    CRITICAL RULES:
    - Return ONLY the SQL query. No markdown fences. No explanations. No prefixes.
    - The query must be syntactically correct PostgreSQL.
    - Only use the tables described in the schema below.
    - Only SELECT statements. Never INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER.
    - If you cannot generate a query, return: CANNOT_GENERATE
""").strip()

RETRY_PROMPT = dedent("""\
    Your previous SQL query failed.

    Error message: {error}

    The query you wrote:
    {failed_sql}

    Please fix the query. Return ONLY the corrected SQL, no markdown fences.
""").strip()

MAX_RETRIES = 3
REQUEST_TIMEOUT = 30  # seconds


def clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM output."""
    sql = raw.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else ""
    if sql.endswith("```"):
        sql = sql.rsplit("```", 1)[0]
    return sql.strip()


def run_sql(conn, sql: str) -> list[tuple]:
    """Execute a SELECT query and return all rows."""
    with conn.cursor() as cur:
        cur.execute(sql)
        if cur.description:
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            return columns, rows
        return [], []


def format_results(columns: list[str], rows: list[tuple]) -> str:
    """Pretty-print query results as a simple table."""
    if not columns:
        return "Query executed successfully (no rows returned)."

    if not rows:
        return "No results found."

    col_widths = [len(c) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    def fmt_row(vals):
        return " | ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(vals))

    sep = "-+-".join("-" * w for w in col_widths)

    lines = [fmt_row(columns), sep]
    for row in rows:
        lines.append(fmt_row(row))

    lines.append(f"\n({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return "\n".join(lines)


def _build_prompt(question: str) -> str:
    """Build the LLM prompt using retrieved context instead of the full schema dump."""
    context = retrieve_context(question)
    schema_text = context["prompt_context"]["schema_text"]
    example_text = context["prompt_context"].get("example_text", "")

    sections = ["RELEVANT SCHEMA:", schema_text]
    if example_text:
        sections.append("EXAMPLE QUERIES:")
        sections.append(example_text)
    sections.append(f"QUESTION: {question}")
    sections.append("SQL:")

    return "\n\n".join(sections)


def _build_retry_prompt(base_prompt: str, error: str, failed_sql: str) -> str:
    """Build a correction prompt while retaining the retrieved context."""
    correction = RETRY_PROMPT.format(error=error, failed_sql=failed_sql)
    return f"{base_prompt}\n\n{correction}\n\nSQL:"


def ask_database(question: str) -> tuple[str, str | None]:
    """Convert a natural-language question to SQL, execute it, and return (answer, sql)."""
    load_dotenv(override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    model = os.getenv("SQL_AGENT_LLM_STRONG_MODEL")

    if not all([api_key, api_base, model]):
        return ("ERROR: Missing OpenAI config in .env (OPENAI_API_KEY, OPENAI_API_BASE, SQL_AGENT_LLM_STRONG_MODEL)", None)

    pg_host = os.getenv("PGHOST", "localhost")
    pg_port = os.getenv("PGPORT", "5432")
    pg_user = os.getenv("PGUSER", "postgres")
    pg_password = os.getenv("PGPASSWORD", "")
    pg_dbname = os.getenv("PGDATABASE", "postgres")

    client = OpenAI(api_key=api_key, base_url=api_base)

    base_prompt = _build_prompt(question)
    prompt = base_prompt

    retries = 0
    last_sql = ""

    while retries <= MAX_RETRIES:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                timeout=REQUEST_TIMEOUT,
            )
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                return ("Request timed out after 30s. Please try again.", None)
            return (f"ERROR: LLM API call failed: {e}", None)

        sql = clean_sql(response.choices[0].message.content)
        last_sql = sql

        if sql.upper() == "CANNOT_GENERATE":
            return ("Could not generate a query for this question.", None)

        try:
            conn = psycopg2.connect(
                host=pg_host,
                port=pg_port,
                user=pg_user,
                password=pg_password,
                dbname=pg_dbname,
            )
            conn.autocommit = True
            columns, rows = run_sql(conn, sql)
            conn.close()
            return (format_results(columns, rows), sql)

        except psycopg2.Error as e:
            conn.close()
            retries += 1
            if retries > MAX_RETRIES:
                break
            prompt = _build_retry_prompt(
                base_prompt,
                error=str(e.pgerror or e),
                failed_sql=sql,
            )

        except Exception as e:
            return (f"ERROR: {e}", None)

    return (f"Sorry, I couldn't generate a working SQL query after {MAX_RETRIES} attempts.", last_sql)


def main():
    user_query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ""
    if not user_query:
        user_query = input("Enter your question: ").strip()
    if not user_query:
        print("No question provided. Exiting.")
        sys.exit(0)

    answer, sql = ask_database(user_query)
    print(answer)


if __name__ == "__main__":
    main()
