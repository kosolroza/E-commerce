import os
import psycopg2
import psycopg2.extras

def get_db_url():
    # Cloud concept: Configuration outside code (Secrets)
    # 1) Local/server environment variable
    url = os.environ.get("NEON_DATABASE_URL")
    if url:
        return url

    # 2) Streamlit Cloud Secrets
    try:
        import streamlit as st
        url = st.secrets.get("NEON_DATABASE_URL")
        if url:
            return url
    except Exception:
        pass

    return None

DB_URL = get_db_url()
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS orders (
  order_id SERIAL PRIMARY KEY,
  customer_id TEXT NOT NULL,
  order_date DATE NOT NULL,
  ship_date DATE,
  status TEXT,
  channel TEXT,
  total_amount_usd NUMERIC(12,2),
  discount_pct NUMERIC(5,2),
  payment_method TEXT,
  region TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

INSERT_SQL = """
INSERT INTO orders (
  customer_id, order_date, ship_date, status, channel,
  total_amount_usd, discount_pct, payment_method, region
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
RETURNING order_id;
"""

SELECT_LATEST_SQL = """
SELECT order_id, customer_id, order_date, ship_date, status, channel,
       total_amount_usd, discount_pct, payment_method, region, created_at
FROM orders
ORDER BY created_at DESC
LIMIT %s;
"""

def get_conn():
    if not DB_URL:
        raise ValueError("NEON_DATABASE_URL is not set.")
    return psycopg2.connect(DB_URL)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)

def insert_order(data: dict) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                INSERT_SQL,
                (
                    data["customer_id"],
                    data["order_date"],
                    data["ship_date"],
                    data["status"],
                    data["channel"],
                    data["total_amount_usd"],
                    data["discount_pct"],
                    data["payment_method"],
                    data["region"],
                ),
            )
            return cur.fetchone()[0]

def fetch_latest(limit: int = 50):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SELECT_LATEST_SQL, (limit,))
            return cur.fetchall()
