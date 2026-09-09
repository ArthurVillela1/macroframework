import pandas as pd
from fredapi import Fred
from sqlalchemy import create_engine, text
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")


# SQL server
CONN_STR = (
    "mssql+pyodbc://@ARTHUR\\SQLEXPRESS/macro"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)
engine = create_engine(CONN_STR) # Used to open the connection to the SQL Server database
fred = Fred(api_key=FRED_API_KEY) 


# Listing FRED series to fetch and their corresponding metadata
SERIES_MAP = {

    # CPI
    "CPI_HEADLINE":          ("CPIAUCSL",  "monthly", "CPI Headline (Index)"),
    "CPI_CORE":              ("CPILFESL",  "monthly", "CPI Core (Index)"),

    # PCE
    "PCE_HEADLINE":          ("PCEPI",     "monthly", "PCE Headline (Index)"),
    "PCE_CORE":              ("PCEPILFE",  "monthly", "PCE Core (Index)"),

    # PPI
    "PPI_HEADLINE":          ("PPIFIS",    "monthly", "PPI Final Demand (Index)"),
    "PPI_CORE":              ("PPIFES",    "monthly", "PPI Final Demand Less Food & Energy (Index)"),
}

for series_id, (fred_code, frequency, name) in SERIES_MAP.items():
    print(f"\n--- {series_id} ({name}) ---")
    data = fred.get_series(fred_code)
    yoy = data.pct_change(periods=12) * 100
    print(yoy.tail(10))

def upsert_observation(conn, series_id, obs_date, value, vintage_date):
    conn.execute(text("""
        MERGE observations AS target
        USING (SELECT :sid AS series_id, :d AS obs_date) AS src
        ON target.series_id = src.series_id AND target.obs_date = src.obs_date
        WHEN MATCHED THEN
            UPDATE SET value = :val, vintage_date = :vint
        WHEN NOT MATCHED THEN
            INSERT (series_id, obs_date, value, vintage_date)
            VALUES (:sid, :d, :val, :vint);
    """), {"sid": series_id, "d": obs_date, "val": value, "vint": vintage_date})

def main():
    today = date.today()
    with engine.begin() as conn:
        for series_id, (fred_code, frequency, name) in SERIES_MAP.items():
            print(f"\n--- {series_id} ({name}) ---")
            data = fred.get_series(fred_code)

            for obs_date, value in data.items():
                if pd.isna(value):
                    continue
                upsert_observation(conn, series_id, obs_date.date(), float(value), today)

            print(f"Saved {len(data)} rows for {series_id}")

if __name__ == "__main__":
    main()