from datetime import date
import pandas as pd
import streamlit as st

import db
from db import init_db, insert_order, fetch_latest

st.set_page_config(page_title="E-commerce Orders", page_icon="🛒")
init_db()


# Cloud concept: Idempotency - safe to run multiple times
try:
    db.init_db()
except Exception as e:
    st.error("Database initialization failed.")
    st.exception(e)
    st.stop()

st.title("🛒 E-commerce Order Entry")
st.caption("Order ID is generated automatically by the system.")

def clean_text(s: str) -> str:
    return " ".join((s or "").strip().split())

with st.form("order_form", clear_on_submit=True):
    customer_id = st.text_input("customer_id", placeholder="e.g., C1023")

    order_date = st.date_input("order_date", value=date.today())
    ship_date = st.date_input("ship_date (optional)", value=None)

    status = st.selectbox(
        "status",
        ["pending", "processing", "shipped", "delivered", "cancelled"]
    )

    channel = st.selectbox(
        "channel",
        ["website", "social", "marketplace", "partner"]
    )

    total_amount_usd = st.number_input(
        "total_amount_usd", min_value=0.0, step=1.0
    )

    discount_pct = st.number_input(
        "discount_pct", min_value=0.0, max_value=100.0, step=0.1
    )

    payment_method = st.selectbox(
        "payment_method",
        ["card", "cash", "bank_transfer", "e-wallet"]
    )

    region = st.text_input("region", placeholder="e.g., Phnom Penh")

    submitted = st.form_submit_button("Save Order")

if submitted:
    data = {
        "customer_id": clean_text(customer_id).upper(),
        "order_date": order_date,
        "ship_date": ship_date,
        "status": status.lower(),
        "channel": channel.lower(),
        "total_amount_usd": float(total_amount_usd),
        "discount_pct": float(discount_pct),
        "payment_method": payment_method.lower(),
        "region": clean_text(region).title(),
    }
    # ship_date validation
    if ship_date is not None and ship_date < order_date:
        st.error("❌ Ship date cannot be earlier than Order date.")
        st.stop()
        
    # validation
    errors = []
    if not data["customer_id"]:
        errors.append("customer_id is required.")
    if data["total_amount_usd"] <= 0:
        errors.append("total_amount_usd must be greater than 0.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        new_id = insert_order(data)
        st.success(f"✅ Order saved (order_id = {new_id})")

st.divider()
st.subheader("📄 Latest Orders")

try:
    rows = fetch_latest(200)

    if not rows:
        st.info("No orders yet. Submit the form above.")
    else:
        df = pd.DataFrame(rows)

        # ---- Chart ABOVE the latest orders table ----
        # Group the latest orders by day (count + revenue).
        # Works whether order_date arrives as date or string.
        if "order_date" in df.columns and "total_amount" in df.columns:
            _tmp = df.copy()
            _tmp["order_date"] = pd.to_datetime(_tmp["order_date"], errors="coerce")
            daily = (
                _tmp.dropna(subset=["order_date"])
                    .groupby(_tmp["order_date"].dt.date)
                    .agg(
                        orders=("order_id", "count") if "order_id" in _tmp.columns else ("total_amount", "count"),
                        revenue=("total_amount", "sum"),
                    )
                    .reset_index()
                    .rename(columns={"order_date": "date"})
            )
            daily["date"] = pd.to_datetime(daily["date"])
            daily = daily.sort_values("date")

            ch1, ch2 = st.columns(2)
            with ch1:
                st.caption("Revenue by day (from latest 200 orders)")
                st.line_chart(daily.set_index("date")["revenue"])
            with ch2:
                st.caption("Orders by day (from latest 200 orders)")
                st.bar_chart(daily.set_index("date")["orders"])

        # Latest orders table (kept below the chart)
        st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Could not fetch rows from the database.")
    st.code(str(e))
    st.dataframe(df, use_container_width=True)
else:
    st.info("No orders yet.")
