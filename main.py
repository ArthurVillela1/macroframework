import pandas as pd
from fredapi import Fred
from sqlalchemy import create_engine, text
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()
FRED_API_KEY = os.getenv("FRED_API_KEY")

CONN_STR = (
    "mssql+pyodbc://@ARTHUR\\SQLEXPRESS/macro"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)
engine = create_engine(CONN_STR)
fred = Fred(api_key=FRED_API_KEY) 


# Listing FRED series to fetch and their corresponding metadata

SERIES_MAP = {

    # CPI
    "CPI_HEADLINE":          ("CPIAUCSL",  "monthly", "CPI Headline (Index)"),
    "CPI_CORE":              ("CPILFESL",  "monthly", "CPI Core (Index)"),}