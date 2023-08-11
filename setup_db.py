#!/usr/bin/env python3
"""
Stand up financial_db in PostgreSQL, apply the schema, and load
Aurora Mobility Inc. sample figures (2022–2024, quarterly).

Run: python setup_db.py
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path
from src.config import DATABASE_URL

SCHEMA_FILE = Path(__file__).parent / "data" / "schema.sql"

# ---------------------------------------------------------------------------
# Seed data — Aurora Mobility Inc. (all figures in thousands USD)
# ---------------------------------------------------------------------------
COMPANY = {
    "name": "Aurora Mobility Inc.",
    "ticker": "AURM",
    "sector": "EV Charging Infrastructure",
    "founded_year": 2014,
}

# (year, quarter, revenue, cost_of_revenue, gross_profit, opex, ebitda, net_income, users, employees)
METRICS = [
    # 2022
    (2022, "Q1", 148_200,  91_200,  57_000,  98_500, -18_200, -41_200, 1_200_000, 1_840),
    (2022, "Q2", 161_500,  97_800,  63_700, 102_100, -14_500, -36_800, 1_350_000, 1_910),
    (2022, "Q3", 175_800, 104_200,  71_600, 106_800,  -9_800, -31_200, 1_520_000, 1_980),
    (2022, "Q4", 189_400, 110_100,  79_300, 111_400,  -4_200, -27_400, 1_710_000, 2_060),
    # 2023
    (2023, "Q1", 215_600, 121_800,  93_800, 118_200,   8_200, -14_600, 2_050_000, 2_210),
    (2023, "Q2", 238_900, 132_400, 106_500, 124_600,  21_400,  -2_800, 2_380_000, 2_340),
    (2023, "Q3", 262_400, 142_100, 120_300, 131_200,  34_800,   9_600, 2_740_000, 2_460),
    (2023, "Q4", 281_700, 148_900, 132_800, 136_800,  42_100,  15_800, 3_120_000, 2_580),
    # 2024
    (2024, "Q1", 312_800, 161_200, 151_600, 142_400,  52_800,  24_600, 3_580_000, 2_710),
    (2024, "Q2", 341_200, 172_800, 168_400, 148_600,  68_400,  38_200, 4_050_000, 2_840),
    (2024, "Q3", 368_500, 182_400, 186_100, 154_200,  81_200,  49_600, 4_520_000, 2_975),
]

# (year, quarter, segment_name, revenue, growth_yoy)
SEGMENTS = [
    # 2022
    (2022, "Q1", "Public Network",  68_200, None),
    (2022, "Q1", "Fleet Solutions", 42_100, None),
    (2022, "Q1", "Residential",     37_900, None),
    (2022, "Q2", "Public Network",  74_100, None),
    (2022, "Q2", "Fleet Solutions", 46_800, None),
    (2022, "Q2", "Residential",     40_600, None),
    (2022, "Q3", "Public Network",  81_200, None),
    (2022, "Q3", "Fleet Solutions", 51_200, None),
    (2022, "Q3", "Residential",     43_400, None),
    (2022, "Q4", "Public Network",  87_600, None),
    (2022, "Q4", "Fleet Solutions", 55_800, None),
    (2022, "Q4", "Residential",     46_000, None),
    # 2023
    (2023, "Q1", "Public Network", 102_400, 50.15),
    (2023, "Q1", "Fleet Solutions", 64_800, 53.92),
    (2023, "Q1", "Residential",     48_400, 27.70),
    (2023, "Q2", "Public Network", 114_200, 54.12),
    (2023, "Q2", "Fleet Solutions", 72_800, 55.56),
    (2023, "Q2", "Residential",     51_900, 27.83),
    (2023, "Q3", "Public Network", 126_800, 56.16),
    (2023, "Q3", "Fleet Solutions", 81_200, 58.59),
    (2023, "Q3", "Residential",     54_400, 25.35),
    (2023, "Q4", "Public Network", 136_400, 55.71),
    (2023, "Q4", "Fleet Solutions", 88_600, 58.78),
    (2023, "Q4", "Residential",     56_700, 23.26),
    # 2024
    (2024, "Q1", "Public Network", 154_600, 50.98),
    (2024, "Q1", "Fleet Solutions",102_800, 58.64),
    (2024, "Q1", "Residential",     55_400, 14.46),
    (2024, "Q2", "Public Network", 168_900, 47.90),
    (2024, "Q2", "Fleet Solutions",114_200, 56.87),
    (2024, "Q2", "Residential",     58_100, 11.95),
    (2024, "Q3", "Public Network", 183_200, 44.48),
    (2024, "Q3", "Fleet Solutions",126_400, 55.67),
    (2024, "Q3", "Residential",     58_900,  8.27),
]


def _parse_db_url(url: str):
    """
    Extract psycopg2 connect kwargs from a DATABASE_URL.
    Handles both TCP (postgresql://user:pass@host/db) and Unix socket
    (postgresql+psycopg2:///db?host=/var/run/postgresql) forms.
    """
    from urllib.parse import urlparse, parse_qs
    p = urlparse(url)
    qs = parse_qs(p.query)
    params: dict = {}
    params["dbname"] = p.path.lstrip("/") or "financial_db"
    if "host" in qs:
        params["host"] = qs["host"][0]
    elif p.hostname:
        params["host"] = p.hostname
    if p.port:
        params["port"] = p.port
    if p.username:
        params["user"] = p.username
    if p.password:
        params["password"] = p.password
    return params


def create_database(params: dict):
    dbname = params["dbname"]
    conn_params = {k: v for k, v in params.items() if k != "dbname"}
    conn_params["dbname"] = "postgres"

    conn = psycopg2.connect(**conn_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{dbname}"')
        print(f"Created database: {dbname}")
    else:
        print(f"Database '{dbname}' already exists.")
    cur.close()
    conn.close()


def apply_schema(conn):
    schema_sql = SCHEMA_FILE.read_text()
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()
    print("Schema applied.")


def seed_data(conn):
    with conn.cursor() as cur:
        # Replace any prior demo company (e.g. NovaTech) cleanly
        cur.execute("TRUNCATE companies RESTART IDENTITY CASCADE")

        cur.execute(
            """INSERT INTO companies (name, ticker, sector, founded_year)
               VALUES (%(name)s, %(ticker)s, %(sector)s, %(founded_year)s)
               RETURNING id""",
            COMPANY,
        )
        company_id = cur.fetchone()[0]

        cur.executemany(
            """INSERT INTO financial_metrics
               (company_id, year, quarter, revenue, cost_of_revenue, gross_profit,
                operating_expenses, ebitda, net_income, user_count, employee_count)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [(company_id, *row) for row in METRICS],
        )

        cur.executemany(
            """INSERT INTO segments (company_id, year, quarter, segment_name, revenue, growth_yoy)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            [(company_id, *row) for row in SEGMENTS],
        )

    conn.commit()
    print(f"Seeded {COMPANY['name']} ({COMPANY['ticker']}): "
          f"{len(METRICS)} quarterly metric rows and {len(SEGMENTS)} segment rows.")


def main():
    params = _parse_db_url(DATABASE_URL)
    create_database(params)

    conn = psycopg2.connect(**params)
    try:
        apply_schema(conn)
        seed_data(conn)
    finally:
        conn.close()

    print("\nDatabase setup complete. Run `python ingest_docs.py` next to load documents into Pinecone.")


if __name__ == "__main__":
    main()
