import pandas as pd
from fredapi import Fred
from sqlalchemy import create_engine, text
from datetime import date
import os
import time
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


def get_fred_series_with_retry(fred_code, max_retries=5):
    for attempt in range(1, max_retries + 1):
        try:
            return fred.get_series(fred_code)

        except Exception as error:
            if attempt == max_retries:
                raise

            wait_seconds = 2 ** attempt

            print(
                f"FRED request failed for {fred_code}: {error}. "
                f"Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)


# FRED series to fetch and their corresponding metadata
SERIES_MAP = {

    # CPI
    "CPI_HEADLINE":          ("CPIAUCSL",   "monthly",   "CPI Headline (Index)",                      "yoy_pct"),
    "CPI_CORE":              ("CPILFESL",   "monthly",   "CPI Core (Index)",                           "yoy_pct"),

    # PCE
    "PCE_HEADLINE":          ("PCEPI",      "monthly",   "PCE Headline (Index)",                       "yoy_pct"),
    "PCE_CORE":              ("PCEPILFE",   "monthly",   "PCE Core (Index)",                           "yoy_pct"),

    # PPI
    "PPI_HEADLINE":          ("PPIFIS",     "monthly",   "PPI Final Demand (Index)",                   "yoy_pct"),
    "PPI_CORE":              ("PPIFES",     "monthly",   "PPI Final Demand Less Food & Energy (Index)", "yoy_pct"),

    # Inflation expectations
    "INFL_EXP_MICH":         ("MICH",       "monthly",   "Michigan Inflation Expectations (%)",        "level"),

    # Labor market
    "PAYROLLS":              ("PAYEMS",     "monthly",   "Nonfarm Payrolls (Thousands)",               "change"),
    "CLAIMS_INITIAL":        ("ICSA",       "weekly",    "Initial Jobless Claims",                     "level"),
    "CLAIMS_CONTINUED":      ("CCSA",       "weekly",    "Continued Jobless Claims",                   "level"),
    "AVG_HOURLY_EARNINGS":   ("AHETPI",     "monthly",   "Average Hourly Earnings ($)",                "yoy_pct"),
    "UNRATE":                ("UNRATE",     "monthly",   "Unemployment Rate (%)",                      "level"),
    "UNEMPLOY_LEVEL":        ("UNEMPLOY",   "monthly",   "Unemployment Level (Thousands)",             "level"),
    "JOB_OPENINGS":          ("JTSJOL",     "monthly",   "Job Openings (Thousands)",                   "level"),
    "LAYOFFS_DISCHARGES":    ("JTSLDL",     "monthly",   "Layoffs & Discharges (Thousands)",           "level"),
    "QUITS_RATE":            ("JTSQUR",     "monthly",   "Quits Rate (%)",                             "level"),
    "LABOR_FORCE_PARTICIPATION": ("CIVPART","monthly",   "Labor Force Participation Rate (%)",         "level"),
    "ECI":                   ("ECIALLCIV",  "quarterly", "Employment Cost Index (Index)",              "yoy_pct"),
    "REAL_DISPOSABLE_INCOME":("DSPIC96",    "monthly",   "Real Disposable Personal Income ($ Billions)","yoy_pct"),
    "PERSONAL_SAVING_RATE":  ("PSAVERT",    "monthly",   "Personal Saving Rate (%)",                   "level"),
    "POPULATION":            ("POPTHM",     "monthly",   "Population (Thousands)",                     "yoy_pct"),

    # Money supply
    "M2_MONEY_SUPPLY":       ("M2SL",       "monthly",   "M2 Money Supply ($ Billions)",               "yoy_pct"),

    # Treasury yields
    "YIELD_2Y":              ("DGS2",       "daily",     "2-Year Treasury Yield (%)",                  "level"),
    "YIELD_5Y":              ("DGS5",       "daily",     "5-Year Treasury Yield (%)",                  "level"),
    "YIELD_10Y":             ("DGS10",      "daily",     "10-Year Treasury Yield (%)",                 "level"),
    "YIELD_20Y":             ("DGS20",      "daily",     "20-Year Treasury Yield (%)",                 "level"),
    "YIELD_30Y":             ("DGS30",      "daily",     "30-Year Treasury Yield (%)",                 "level"),

    # Yield curve spread
    "SPREAD_10Y2Y":          ("T10Y2Y",     "daily",     "10Y-2Y Treasury Spread (pp)",                "level"),

    # Treasury term premiums
    "TERM_PREMIUM_2Y":       ("THREEFYTP2",  "daily",    "2-Year Treasury Term Premium (%)",           "level"),
    "TERM_PREMIUM_5Y":       ("THREEFYTP5",  "daily",    "5-Year Treasury Term Premium (%)",           "level"),
    "TERM_PREMIUM_10Y":      ("THREEFYTP10", "daily",    "10-Year Treasury Term Premium (%)",          "level"),

    # Federal debt
    "DEBT_TO_GDP":           ("GFDEGDQ188S",  "quarterly", "Total Federal Debt (% of GDP)",              "level"),
    "PUBLIC_DEBT_TO_GDP":    ("FYGFGDQ188S",  "quarterly", "Federal Debt Held by the Public (% of GDP)", "level"),

    # Commodity prices
    "WTI_PRICE":             ("DCOILWTICO",       "daily", "WTI Crude Oil Price ($ per Barrel)",         "level"),
    "BRENT_PRICE":           ("DCOILBRENTEU",     "daily", "Brent Crude Oil Price ($ per Barrel)",       "level"),
    "NATURAL_GAS_PRICE":     ("DHHNGSP",           "daily", "Henry Hub Natural Gas Price ($ per MMBtu)",  "level"),
}

# Note: "Vacancy-to-unemployment ratio" has no direct FRED ticker.
# It has to be computed after the fact as JOB_OPENINGS / UNEMPLOY_LEVEL, once both are saved.

# Number of observations that make up one year, per frequency
# used so the year-over-year comparison spans an actual 12-month period,
# regardless of whether the series is daily, weekly, monthly, or quarterly
PERIODS_PER_YEAR = {"daily": 252, "weekly": 52, "monthly": 12, "quarterly": 4}

for series_id, (fred_code, frequency, name, transform) in SERIES_MAP.items():
    data = get_fred_series_with_retry(fred_code)
    periods = PERIODS_PER_YEAR[frequency]

    if transform == "yoy_pct":
        # for index/count-type series: show year-over-year % change
        result = data.pct_change(periods=periods) * 100
        label = "YoY % change"

    elif transform == "change":
        # show the change from the previous observation
        # for monthly payrolls, this is the monthly change in thousands
        result = data.diff()
        label = "change from previous observation"

    elif transform == "diff":
        # for series already expressed as a %, e.g. yields/spreads:
        # show year-over-year change in percentage points, not a % change of a %
        result = data.diff(periods=periods)
        label = "YoY change (pp)"

    else:  # "level"
        # show the raw value with no transformation
        result = data
        label = "level"

    print(f"\n--- {series_id} ({name}) [{frequency}] --- ({label})")
    print(result.tail(10))

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

    with engine.begin() as conn:
        # Fetch and save the original FRED series
        for series_id, (fred_code, frequency, name, transform) in SERIES_MAP.items():
            print(f"\n--- {series_id} ({name}) [{frequency}] ---")
            data = get_fred_series_with_retry(fred_code)

            for obs_date, value in data.items():
                if pd.isna(value):
                    continue

                upsert_observation(
                    conn,
                    series_id,
                    obs_date.date(),
                    float(value),
                    today
                )

            print(f"Saved {len(data)} rows for {series_id}")

        # Vacancy-to-unemployment ratio
        job_openings = get_fred_series_with_retry("JTSJOL")
        unemployed = get_fred_series_with_retry("UNEMPLOY")

        vacancy_ratio = pd.concat(
            [
                job_openings.rename("job_openings"),
                unemployed.rename("unemployed")
            ],
            axis=1,
            join="inner"
        ).dropna()

        vacancy_ratio["ratio"] = (
            vacancy_ratio["job_openings"]
            / vacancy_ratio["unemployed"]
        )

        print("\n--- VACANCY RATIO ---")
        print(vacancy_ratio["ratio"].tail(10))

        # Save the calculated ratio
        for obs_date, value in vacancy_ratio["ratio"].items():
            upsert_observation(
                conn,
                "VACANCY_RATIO",
                obs_date.date(),
                float(value),
                today
            )

        print(
            f"Saved {len(vacancy_ratio)} rows "
            "for VACANCY_RATIO"
        )

if __name__ == "__main__":
    main()