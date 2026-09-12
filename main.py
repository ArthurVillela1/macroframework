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

    # Inflation expectations
    "INFL_EXP_MICH":         ("MICH",      "monthly", "Michigan Inflation Expectations (%)"),

    # Labor market
    "PAYROLLS":              ("PAYEMS",    "monthly", "Nonfarm Payrolls (Thousands)"),
    "CLAIMS_INITIAL":        ("ICSA",      "weekly",  "Initial Jobless Claims"),
    "CLAIMS_CONTINUED":      ("CCSA",      "weekly",  "Continued Jobless Claims"),
    "AVG_HOURLY_EARNINGS":   ("AHETPI",    "monthly", "Average Hourly Earnings ($)"),

    # Money supply
    "M2_MONEY_SUPPLY":       ("M2SL",      "monthly", "M2 Money Supply ($ Billions)"),
}

# Number of observations that make up one year, per frequency
# used so the YoY % change is calculated over an actual 12-month span,
# regardless of whether the series is monthly, weekly, or daily
PERIODS_PER_YEAR = {"monthly": 12, "weekly": 52, "daily": 252}

for series_id, (fred_code, frequency, name) in SERIES_MAP.items():
    print(f"\n--- {series_id} ({name}) [{frequency}] --- (YoY % change)")
    data = fred.get_series(fred_code)
    periods = PERIODS_PER_YEAR[frequency]  # pick the right lookback based on this series' frequency
    yoy = data.pct_change(periods=periods) * 100
    print(yoy.tail(10))

def upsert_observation(conn, series_id, obs_date, value, vintage_date): # conn = database connection
    # calling .execute() on the connection to run a SQL command
    # text(...) (from SQLAlchemy) marks the string as raw SQL to be run as-is
    # The MERGE statement is used to either update an existing row or insert a new row into the observations table
    # USING clause specifies the source data to be merged into the target table
    # ON to Check if a row with the same series_id and obs_date already exists in the observations table
    # WHEN MATCHED THEN clause specifies what to do if a matching row is found (update the value and vintage_date)
    # WHEN NOT MATCHED THEN clause specifies what to do if no matching row is found (insert a new row with the provided values)
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

# Fetching data from FRED and saving it to the database
def main():
    today = date.today()
    with engine.begin() as conn: # Opens a connection to the datbase
        for series_id, (fred_code, frequency, name) in SERIES_MAP.items():
            print(f"\n--- {series_id} ({name}) [{frequency}] ---")
            data = fred.get_series(fred_code)

            for obs_date, value in data.items():
                if pd.isna(value):
                    continue
                upsert_observation(conn, series_id, obs_date.date(), float(value), today)

            print(f"Saved {len(data)} rows for {series_id}")

if __name__ == "__main__":
    main()