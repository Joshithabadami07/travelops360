import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import timedelta
import secrets
import jwt


# ============================================================
# TRAVELOPS 360
# FASTAPI BACKEND
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")

JWT_SECRET = os.getenv(
    "TRAVELOPS_JWT_SECRET",
    "CHANGE_THIS_SECRET_BEFORE_DEPLOYMENT"
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8


OUTPUT_DIR = BASE_DIR / "analytics" / "outputs"
SILVER_DIR = BASE_DIR / "data" / "silver"


# ============================================================
# FILE CONFIGURATION
# ============================================================

AUTOMATION_FILE = (
    OUTPUT_DIR / "automation_gap_actions.parquet"
)

OLD_PREDICTIONS_FILE = (
    OUTPUT_DIR / "delay_automation_actions.parquet"
)

NOTIFICATION_FILE = (
    OUTPUT_DIR / "notification_audit.parquet"
)

ROUTE_PROFITABILITY_FILE = (
    OUTPUT_DIR / "route_profitability.parquet"
)

BAGGAGE_SLA_FILE = (
    OUTPUT_DIR / "baggage_sla.parquet"
)

PASSENGER_EXPERIENCE_FILE = (
    OUTPUT_DIR / "passenger_experience.parquet"
)

PASSENGER_ISSUES_FILE = (
    OUTPUT_DIR / "passenger_issue_summary.parquet"
)

ROUTE_DEMAND_FILE = (
    OUTPUT_DIR / "route_demand_daily.parquet"
)

DEMAND_FORECAST_FILE = (
    OUTPUT_DIR / "demand_forecast.parquet"
)

CANCELLATION_FILE = (
    OUTPUT_DIR / "cancellation_anomalies.parquet"
)

FLIGHTS_FILE = (
    SILVER_DIR / "flights.parquet"
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="TravelOps 360 API",
    description=(
        "Airline Operations Control Center API for "
        "flight risk, analytics, automation, "
        "notifications and operational monitoring."
    ),
    version="2.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTHENTICATION / AUTHORIZATION
# ============================================================

class LoginRequest(BaseModel):
    email: str
    password: str


def demo_users():
    return {
        "ops@travelops360.com": {
            "email": "ops@travelops360.com",
            "role": "operator",
            "password": os.getenv(
                "TRAVELOPS_OPS_PASSWORD",
                "TravelOps@123"
            ),
        },
        "admin@travelops360.com": {
            "email": "admin@travelops360.com",
            "role": "admin",
            "password": os.getenv(
                "TRAVELOPS_ADMIN_PASSWORD",
                "Admin@123"
            ),
        },
    }


def create_access_token(email: str, role: str):
    expires = datetime.now(timezone.utc) + timedelta(
        hours=JWT_EXPIRATION_HOURS
    )

    return jwt.encode(
        {
            "sub": email,
            "role": role,
            "exp": expires,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def decode_access_token(token: str):
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Session expired. Please login again."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token."
        )


def current_user_from_request(request: Request):
    authorization = request.headers.get("Authorization")

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header."
        )

    token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication token is missing."
        )

    return decode_access_token(token)


def require_roles(request: Request, allowed_roles):
    user = current_user_from_request(request)

    if user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission for this operation."
        )

    return user



# ============================================================
# AUTHENTICATION ENDPOINTS
# ============================================================

@app.post("/auth/login")
def login(credentials: LoginRequest):

    email = credentials.email.lower().strip()
    user = demo_users().get(email)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    if not secrets.compare_digest(
        credentials.password,
        user["password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    token = create_access_token(
        email=user["email"],
        role=user["role"]
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.get("/auth/me")
def auth_me(request: Request):

    user = current_user_from_request(request)

    return {
        "email": user.get("sub"),
        "role": user.get("role"),
    }


@app.get("/auth/admin-check")
def auth_admin_check(request: Request):

    user = require_roles(request, {"admin"})

    return {
        "authorized": True,
        "email": user.get("sub"),
        "role": user.get("role"),
    }


# ============================================================
# AUTHENTICATION MIDDLEWARE
# ============================================================

@app.middleware("http")
async def authentication_middleware(request: Request, call_next):

    path = request.url.path

    public_paths = {
        "/",
        "/health",
        "/auth/login",
        "/openapi.json",
        "/docs",
        "/redoc",
    }

    if request.method == "OPTIONS":
        return await call_next(request)

    if (
        path in public_paths
        or path.startswith("/docs")
        or path.startswith("/redoc")
    ):
        return await call_next(request)

    try:
        request.state.user = current_user_from_request(request)
        return await call_next(request)

    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers={
                "Access-Control-Allow-Origin": request.headers.get(
                    "origin", "http://localhost:5173"
                ),
                "Access-Control-Allow-Credentials": "true",
            },
        )

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Authentication error: {str(exc)}"
            },
            headers={
                "Access-Control-Allow-Origin": request.headers.get(
                    "origin", "http://localhost:5173"
                ),
                "Access-Control-Allow-Credentials": "true",
            },
        )


# ============================================================
# GENERAL HELPERS
# ============================================================

def now_utc():
    return datetime.now(
        timezone.utc
    ).isoformat()


def file_exists(path):
    return path.exists()


def read_parquet(path):
    """
    Safely read a parquet file.
    Returns an empty DataFrame if the file doesn't exist.
    """

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_parquet(path)

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                f"Unable to read {path.name}: "
                f"{str(exc)}"
            )
        )


def clean_records(df):
    """
    Convert Pandas records into JSON-safe dictionaries.

    Handles:
    - datetime
    - NaN
    - NaT
    - infinity
    """

    if df is None or df.empty:
        return []

    records = df.copy()

    # Convert datetime columns
    for column in records.columns:

        if pd.api.types.is_datetime64_any_dtype(
            records[column]
        ):

            records[column] = (
                records[column]
                .astype(str)
            )

    # Replace infinity
    records = records.replace(
        [
            float("inf"),
            float("-inf")
        ],
        pd.NA
    )

    # Replace NaN / NaT / NA
    records = (
        records
        .astype(object)
        .where(
            pd.notna(records),
            None
        )
    )

    return records.to_dict(
        orient="records"
    )


def find_column(df, candidates):
    """
    Find the first available column.
    """

    if df is None or df.empty:
        return None

    for column in candidates:

        if column in df.columns:
            return column

    return None


def safe_int(value, default=0):

    try:
        return int(value)

    except Exception:
        return default


def safe_float(value, default=0.0):

    try:
        return float(value)

    except Exception:
        return default


# ============================================================
# DATA LOADERS
# ============================================================

def load_automation():

    if AUTOMATION_FILE.exists():

        return read_parquet(
            AUTOMATION_FILE
        )

    # Fallback to the older file
    if OLD_PREDICTIONS_FILE.exists():

        return read_parquet(
            OLD_PREDICTIONS_FILE
        )

    raise HTTPException(
        status_code=404,
        detail=(
            "No automation prediction file found."
        )
    )


def load_notifications():

    if not NOTIFICATION_FILE.exists():

        return pd.DataFrame(
            columns=[
                "timestamp",
                "alert_id",
                "entity_id",
                "flight_id",
                "alert_type",
                "risk_level",
                "priority",
                "automation_action",
                "trigger_reason",
                "owner",
                "recipient",
                "status",
            ]
        )

    return read_parquet(
        NOTIFICATION_FILE
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "TravelOps 360 API",
        "version": "2.0.0",
        "timestamp": now_utc()
    }


# ============================================================
# DASHBOARD SUMMARY
# ============================================================

@app.get("/summary")
def summary():

    df = load_automation()

    high = 0
    medium = 0
    low = 0

    if "risk_level" in df.columns:

        high = safe_int(
            (
                df["risk_level"]
                .astype(str)
                .str.upper()
                == "HIGH"
            ).sum()
        )

        medium = safe_int(
            (
                df["risk_level"]
                .astype(str)
                .str.upper()
                == "MEDIUM"
            ).sum()
        )

        low = safe_int(
            (
                df["risk_level"]
                .astype(str)
                .str.upper()
                == "LOW"
            ).sum()
        )

    urgent = 0
    turnaround = 0

    if "automation_action" in df.columns:

        urgent = safe_int(
            (
                df["automation_action"]
                == "URGENT_OPERATIONS_REVIEW"
            ).sum()
        )

        turnaround = safe_int(
            (
                df["automation_action"]
                == "AIRCRAFT_TURNAROUND_ALERT"
            ).sum()
        )

    audit = load_notifications()

    sent = 0
    failed = 0
    acknowledged = 0

    if not audit.empty:

        if "status" in audit.columns:

            sent = safe_int(
                (
                    audit["status"]
                    .astype(str)
                    .str.upper()
                    == "SENT"
                ).sum()
            )

            failed = safe_int(
                (
                    audit["status"]
                    .astype(str)
                    .str.upper()
                    == "FAILED"
                ).sum()
            )

            acknowledged = safe_int(
                (
                    audit["status"]
                    .astype(str)
                    .str.upper()
                    == "ACKNOWLEDGED"
                ).sum()
            )

    operational_flight_count = 0

    if FLIGHTS_FILE.exists():
        try:
            operational_flight_count = len(
                pd.read_parquet(FLIGHTS_FILE)
            )
        except Exception:
            operational_flight_count = len(df)

    if operational_flight_count == 0:
        operational_flight_count = len(df)

    return {

        "total_flights": operational_flight_count,

        "risk_scored_flights": len(df),

        "high_risk": high,

        "medium_risk": medium,

        "low_risk": low,

        "urgent_actions": urgent,

        "aircraft_turnaround_alerts":
            turnaround,

        "notifications_sent":
            sent,

        "notifications_failed":
            failed,

        "notifications_acknowledged":
            acknowledged,

        "timestamp":
            now_utc()
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard")
def dashboard():

    summary_data = summary()

    route_df = read_parquet(
        ROUTE_PROFITABILITY_FILE
    )

    baggage_df = read_parquet(
        BAGGAGE_SLA_FILE
    )

    passenger_df = read_parquet(
        PASSENGER_EXPERIENCE_FILE
    )

    forecast_df = read_parquet(
        DEMAND_FORECAST_FILE
    )

    cancellation_df = read_parquet(
        CANCELLATION_FILE
    )

    return {

        "summary":
            summary_data,

        "route_profitability_count":
            len(route_df),

        "baggage_records":
            len(baggage_df),

        "passenger_experience_records":
            len(passenger_df),

        "forecast_records":
            len(forecast_df),

        "cancellation_records":
            len(cancellation_df),

        "timestamp":
            now_utc()
    }


# ============================================================
# FLIGHTS
# ============================================================

@app.get("/flights")
def flights(
    risk: str | None = None,
    limit: int = Query(
        default=100,
        ge=1,
        le=5000
    )
):

    df = load_automation()

    result = df.copy()

    # --------------------------------------------------------
    # Risk filter
    # --------------------------------------------------------

    if (
        risk
        and "risk_level" in result.columns
    ):

        result = result[
            result["risk_level"]
            .astype(str)
            .str.upper()
            == risk.upper()
        ]


    # --------------------------------------------------------
    # Compatible columns
    # --------------------------------------------------------

    preferred_columns = [
        "flight_id",
        "entity_id",
        "aircraft_id",
        "route_id",
        "delay_probability",
        "future_delay_probability",
        "model_probability",
        "risk_level",
        "priority",
        "automation_action",
        "action_message",
        "trigger_reason",
        "owner",
        "status",
        "timestamp",
    ]

    available = [
        column
        for column in preferred_columns
        if column in result.columns
    ]

    if available:
        result = result[available]


    # --------------------------------------------------------
    # Highest risk first
    # --------------------------------------------------------

    probability_column = find_column(
        result,
        [
            "delay_probability",
            "future_delay_probability",
            "model_probability"
        ]
    )

    if probability_column:

        result = result.sort_values(
            probability_column,
            ascending=False
        )


    result = result.head(
        limit
    )

    return {

        "count":
            len(result),

        "flights":
            clean_records(result),

        "timestamp":
            now_utc()
    }


# ============================================================
# LIVE FLIGHTS
# ============================================================

@app.get("/flights/live")
def live_flights(
    limit: int = Query(
        default=100,
        ge=1,
        le=5000
    )
):

    if not FLIGHTS_FILE.exists():

        return {
            "count": 0,
            "flights": [],
            "source": "silver_flights",
            "timestamp": now_utc()
        }

    df = read_parquet(
        FLIGHTS_FILE
    )

    result = df.copy()

    # Join automation information
    try:

        automation = load_automation()

        if (
            "flight_id" in df.columns
            and "flight_id"
            in automation.columns
        ):

            automation_columns = [
                column
                for column in [
                    "flight_id",
                    "risk_level",
                    "priority",
                    "automation_action",
                    "model_probability",
                    "delay_probability"
                ]
                if column in automation.columns
            ]

            if automation_columns:

                automation_small = (
                    automation[
                        automation_columns
                    ]
                    .drop_duplicates(
                        subset=["flight_id"]
                    )
                )

                result = result.merge(
                    automation_small,
                    on="flight_id",
                    how="left"
                )

    except Exception:
        pass


    result = result.head(
        limit
    )

    return {

        "count":
            len(result),

        "flights":
            clean_records(result),

        "source":
            "silver_flights",

        "timestamp":
            now_utc()
    }


# ============================================================
# SINGLE FLIGHT
# ============================================================

@app.get("/flights/{flight_id}")
def flight_detail(
    flight_id: str
):

    df = load_automation()

    id_column = find_column(
        df,
        [
            "flight_id",
            "entity_id"
        ]
    )

    if id_column is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "No flight identifier column "
                "found."
            )
        )

    result = df[
        df[id_column].astype(str)
        == str(flight_id)
    ]

    if result.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Flight {flight_id} "
                f"not found."
            )
        )

    return clean_records(
        result
    )[0]


# ============================================================
# ALERT CENTER
# ============================================================

@app.get("/alerts")
def alerts(
    risk: str | None = None,
    action: str | None = None,
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = load_automation()

    result = df.copy()


    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    if "risk_level" in result.columns:

        result = result[
            result["risk_level"]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "HIGH",
                    "MEDIUM"
                ]
            )
        ]


    if (
        risk
        and "risk_level" in result.columns
    ):

        result = result[
            result["risk_level"]
            .astype(str)
            .str.upper()
            == risk.upper()
        ]


    # --------------------------------------------------------
    # Action filter
    # --------------------------------------------------------

    if (
        action
        and "automation_action"
        in result.columns
    ):

        result = result[
            result["automation_action"]
            .astype(str)
            == action
        ]


    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    probability_column = find_column(
        result,
        [
            "delay_probability",
            "future_delay_probability",
            "model_probability"
        ]
    )

    if probability_column:

        result = result.sort_values(
            probability_column,
            ascending=False
        )


    high = 0
    medium = 0

    if "risk_level" in result.columns:

        high = safe_int(
            (
                result["risk_level"]
                .astype(str)
                .str.upper()
                == "HIGH"
            ).sum()
        )

        medium = safe_int(
            (
                result["risk_level"]
                .astype(str)
                .str.upper()
                == "MEDIUM"
            ).sum()
        )


    result = result.head(
        limit
    )


    return {

        "count":
            len(result),

        "high_risk":
            high,

        "medium_risk":
            medium,

        "alerts":
            clean_records(result),

        "timestamp":
            now_utc()
    }


# ============================================================
# DELAY RISK
# ============================================================

@app.get("/delay-risk")
def delay_risk(
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = load_automation()

    result = df.copy()

    if "risk_level" in result.columns:

        result = result[
            result["risk_level"]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "HIGH",
                    "MEDIUM"
                ]
            )
        ]


    probability_column = find_column(
        result,
        [
            "delay_probability",
            "future_delay_probability",
            "model_probability"
        ]
    )

    if probability_column:

        result = result.sort_values(
            probability_column,
            ascending=False
        )


    result = result.head(
        limit
    )


    return {

        "count":
            len(result),

        "risk_predictions":
            clean_records(result),

        "timestamp":
            now_utc()
    }


# ============================================================
# RISK
# ============================================================

@app.get("/risk")
def risk():

    df = load_automation()

    distribution = {}

    if "risk_level" in df.columns:

        distribution = (
            df["risk_level"]
            .astype(str)
            .str.upper()
            .value_counts()
            .to_dict()
        )


    return {

        "distribution":
            distribution,

        "total":
            len(df),

        "timestamp":
            now_utc()
    }


# ============================================================
# ACKNOWLEDGE ALERT
# ============================================================

class AlertAcknowledgement(BaseModel):

    owner: str = "Operations Control"


@app.post(
    "/alerts/{flight_id}/acknowledge"
)
def acknowledge_alert(
    flight_id: str,
    request: AlertAcknowledgement
):

    audit = load_notifications()

    if audit.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                "No notification audit "
                "records found."
            )
        )


    # New notification audit uses entity_id.
    # Older records may use flight_id.

    id_column = find_column(
        audit,
        [
            "entity_id",
            "flight_id"
        ]
    )

    if id_column is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "No entity identifier found "
                "in notification audit."
            )
        )


    matches = audit[
        audit[id_column].astype(str)
        == str(flight_id)
    ]


    if matches.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"No notification found "
                f"for {flight_id}."
            )
        )


    # Most recent record
    if "timestamp" in matches.columns:

        matches = matches.sort_values(
            "timestamp"
        )


    index = matches.index[-1]


    audit.loc[
        index,
        "status"
    ] = "ACKNOWLEDGED"


    audit.loc[
        index,
        "owner"
    ] = request.owner


    audit.loc[
        index,
        "acknowledged_at"
    ] = now_utc()


    audit.to_parquet(
        NOTIFICATION_FILE,
        index=False
    )


    return {

        "success":
            True,

        "entity_id":
            flight_id,

        "status":
            "ACKNOWLEDGED",

        "owner":
            request.owner,

        "acknowledged_at":
            audit.loc[
                index,
                "acknowledged_at"
            ]
    }


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.get("/notifications")
def notifications():

    audit = load_notifications()

    if audit.empty:

        return {

            "count": 0,

            "sent": 0,

            "failed": 0,

            "acknowledged": 0,

            "notifications": []

        }


    if "timestamp" in audit.columns:

        audit = audit.sort_values(
            "timestamp",
            ascending=False
        )


    sent = 0
    failed = 0
    acknowledged = 0


    if "status" in audit.columns:

        statuses = (
            audit["status"]
            .astype(str)
            .str.upper()
        )

        sent = safe_int(
            (statuses == "SENT").sum()
        )

        failed = safe_int(
            (statuses == "FAILED").sum()
        )

        acknowledged = safe_int(
            (
                statuses
                == "ACKNOWLEDGED"
            ).sum()
        )


    return {

        "count":
            len(audit),

        "sent":
            sent,

        "failed":
            failed,

        "acknowledged":
            acknowledged,

        "notifications":
            clean_records(audit),

        "timestamp":
            now_utc()
    }


# ============================================================
# NOTIFICATION SUMMARY
# ============================================================

@app.get("/notifications/summary")
def notification_summary():

    audit = load_notifications()

    if audit.empty:

        return {

            "total": 0,

            "sent": 0,

            "failed": 0,

            "acknowledged": 0,

            "timestamp":
                now_utc()
        }


    statuses = (
        audit["status"]
        .astype(str)
        .str.upper()
    )


    return {

        "total":
            len(audit),

        "sent":
            safe_int(
                (statuses == "SENT").sum()
            ),

        "failed":
            safe_int(
                (statuses == "FAILED").sum()
            ),

        "acknowledged":
            safe_int(
                (
                    statuses
                    == "ACKNOWLEDGED"
                ).sum()
            ),

        "timestamp":
            now_utc()
    }


# ============================================================
# ROUTE PROFITABILITY
# ============================================================

@app.get("/routes/profitability")
def route_profitability(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    )
):

    df = read_parquet(
        ROUTE_PROFITABILITY_FILE
    )

    if df.empty:

        return {
            "count": 0,
            "routes": [],
            "timestamp": now_utc()
        }


    # Try to sort by profit
    profit_column = find_column(
        df,
        [
            "profit",
            "estimated_profit",
            "route_profit",
            "profitability"
        ]
    )

    if profit_column:

        df = df.sort_values(
            profit_column,
            ascending=False
        )


    df = df.head(
        limit
    )


    return {

        "count":
            len(df),

        "routes":
            clean_records(df),

        "timestamp":
            now_utc()
    }


# ============================================================
# ROUTE PERFORMANCE
# ============================================================

@app.get("/routes/performance")
def route_performance(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    )
):

    df = read_parquet(
        ROUTE_PROFITABILITY_FILE
    )

    if df.empty:

        return {
            "count": 0,
            "routes": [],
            "timestamp": now_utc()
        }


    df = df.head(
        limit
    )


    return {

        "count":
            len(df),

        "routes":
            clean_records(df),

        "timestamp":
            now_utc()
    }


# ============================================================
# BAGGAGE SLA
# ============================================================

@app.get("/baggage/sla")
def baggage_sla(
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = read_parquet(
        BAGGAGE_SLA_FILE
    )

    if df.empty:

        return {
            "count": 0,
            "records": [],
            "timestamp": now_utc()
        }


    result = df.copy()


    breach_column = find_column(
        result,
        [
            "sla_breach",
            "breach",
            "is_breach"
        ]
    )


    breach_count = 0

    if breach_column:

        values = (
            result[breach_column]
            .astype(str)
            .str.lower()
        )

        breach_count = safe_int(
            values.isin(
                [
                    "true",
                    "1",
                    "yes",
                    "breach",
                    "high"
                ]
            ).sum()
        )


    result = result.head(
        limit
    )


    return {

        "count":
            len(result),

        "breach_count":
            breach_count,

        "records":
            clean_records(result),

        "timestamp":
            now_utc()
    }


# ============================================================
# BAGGAGE ISSUES
# ============================================================

@app.get("/baggage/issues")
def baggage_issues(
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = read_parquet(
        BAGGAGE_SLA_FILE
    )

    if df.empty:

        return {
            "count": 0,
            "issues": [],
            "timestamp": now_utc()
        }


    result = df.copy()

    duration_column = find_column(
        result,
        [
            "cycle_minutes",
            "sla_minutes",
            "scan_duration_minutes",
            "duration_minutes",
            "processing_minutes"
        ]
    )


    if duration_column:

        durations = pd.to_numeric(
            result[duration_column],
            errors="coerce"
        )

        result = result[
            durations > 45
        ]


    result = result.head(
        limit
    )


    return {

        "count":
            len(result),

        "issues":
            clean_records(result),

        "timestamp":
            now_utc()
    }


# ============================================================
# PASSENGER EXPERIENCE
# ============================================================

@app.get("/passenger/experience")
def passenger_experience(
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = read_parquet(
        PASSENGER_EXPERIENCE_FILE
    )

    if df.empty:

        return {
            "count": 0,
            "records": [],
            "timestamp": now_utc()
        }


    return {

        "count":
            len(df.head(limit)),

        "records":
            clean_records(
                df.head(limit)
            ),

        "timestamp":
            now_utc()
    }


# ============================================================
# PASSENGER ISSUE SUMMARY
# ============================================================

@app.get("/passenger/issues")
def passenger_issues():

    df = read_parquet(
        PASSENGER_ISSUES_FILE
    )

    return {

        "count":
            len(df),

        "issues":
            clean_records(df),

        "timestamp":
            now_utc()
    }


# ============================================================
# DEMAND FORECAST
# ============================================================

@app.get("/forecasts/demand")
def demand_forecast(
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = read_parquet(
        DEMAND_FORECAST_FILE
    )

    if df.empty:

        return {
            "count": 0,
            "forecast": [],
            "timestamp": now_utc()
        }


    return {

        "count":
            len(df.head(limit)),

        "forecast":
            clean_records(
                df.head(limit)
            ),

        "timestamp":
            now_utc()
    }


# ============================================================
# GENERIC FORECAST ENDPOINT
# ============================================================

@app.get("/forecasts")
def forecasts(
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = read_parquet(
        DEMAND_FORECAST_FILE
    )

    return {

        "count":
            len(df.head(limit)),

        "forecasts":
            clean_records(
                df.head(limit)
            ),

        "timestamp":
            now_utc()
    }


# ============================================================
# ROUTE DEMAND
# ============================================================

@app.get("/routes/demand")
def route_demand(
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = read_parquet(
        ROUTE_DEMAND_FILE
    )

    return {

        "count":
            len(df.head(limit)),

        "demand":
            clean_records(
                df.head(limit)
            ),

        "timestamp":
            now_utc()
    }


# ============================================================
# CANCELLATION ANOMALIES
# ============================================================

@app.get("/cancellations/anomalies")
def cancellation_anomalies(
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    )
):

    df = read_parquet(
        CANCELLATION_FILE
    )

    if df.empty:

        return {
            "count": 0,
            "anomalies": [],
            "timestamp": now_utc()
        }


    anomaly_column = find_column(
        df,
        [
            "anomaly",
            "is_anomaly",
            "anomaly_flag"
        ]
    )


    if anomaly_column:

        values = (
            df[anomaly_column]
            .astype(str)
            .str.lower()
        )

        result = df[
            values.isin(
                [
                    "true",
                    "1",
                    "yes",
                    "high",
                    "anomaly"
                ]
            )
        ].copy()

    else:

        z_column = find_column(
            df,
            [
                "z_score",
                "zscore",
                "cancellation_zscore"
            ]
        )

        if z_column:

            z_values = pd.to_numeric(
                df[z_column],
                errors="coerce"
            ).fillna(0)

            result = df[
                z_values >= 2
            ].copy()

        else:

            result = df.copy()


    result = result.head(
        limit
    )


    return {

        "count":
            len(result),

        "anomalies":
            clean_records(result),

        "timestamp":
            now_utc()
    }


# ============================================================
# LIVE EVENTS
# ============================================================

@app.get("/events/live")
def live_events():

    """
    Return persisted Kafka processing evidence when the
    consumer's DuckDB monitoring table is available.
    """

    topics = [
        "flights.status",
        "baggage.scans",
        "bookings.events",
    ]

    try:
        import duckdb

        candidates = []
        warehouse_dir = BASE_DIR / "warehouse"

        if warehouse_dir.exists():
            candidates.extend(warehouse_dir.glob("*.duckdb"))
            candidates.extend(warehouse_dir.glob("*.db"))

        candidates.extend(BASE_DIR.glob("*.duckdb"))
        candidates.extend(BASE_DIR.glob("*.db"))

        for db_path in candidates:

            try:
                con = duckdb.connect(
                    str(db_path),
                    read_only=True
                )

                try:
                    tables = {
                        row[0]
                        for row in con.execute(
                            "SHOW TABLES"
                        ).fetchall()
                    }

                    if "stream_monitoring" not in tables:
                        continue

                    processed = safe_int(
                        con.execute(
                            "SELECT COUNT(*) FROM stream_monitoring"
                        ).fetchone()[0]
                    )

                    duplicates = 0
                    errors = 0

                    columns = {
                        row[0]
                        for row in con.execute(
                            "DESCRIBE stream_monitoring"
                        ).fetchall()
                    }

                    status_column = next(
                        (
                            c for c in [
                                "event_status",
                                "status",
                                "processing_status",
                            ]
                            if c in columns
                        ),
                        None
                    )

                    if status_column:
                        q = (
                            'SELECT COUNT(*) FROM stream_monitoring '
                            f'WHERE UPPER(CAST("{status_column}" AS VARCHAR)) '
                            "IN ('DUPLICATE','DUPLICATED')"
                        )
                        duplicates = safe_int(
                            con.execute(q).fetchone()[0]
                        )

                        q = (
                            'SELECT COUNT(*) FROM stream_monitoring '
                            f'WHERE UPPER(CAST("{status_column}" AS VARCHAR)) '
                            "IN ('ERROR','FAILED','FAILURE')"
                        )
                        errors = safe_int(
                            con.execute(q).fetchone()[0]
                        )

                    if "stream_seen_events" in tables:
                        try:
                            unique_events = safe_int(
                                con.execute(
                                    "SELECT COUNT(DISTINCT event_id) "
                                    "FROM stream_seen_events"
                                ).fetchone()[0]
                            )
                            duplicates = max(
                                0,
                                processed - unique_events
                            )
                        except Exception:
                            pass

                    return {
                        "status": "live",
                        "events_processed": processed,
                        "duplicates_detected": duplicates,
                        "processing_errors": errors,
                        "topics": topics,
                        "source": str(db_path),
                        "last_checked": now_utc(),
                    }

                finally:
                    con.close()

            except Exception:
                continue

    except Exception:
        pass

    return {
        "status": "monitoring_unavailable",
        "events_processed": None,
        "duplicates_detected": None,
        "processing_errors": None,
        "topics": topics,
        "source": "Kafka monitoring database not available to API",
        "last_checked": now_utc(),
    }


# ============================================================
# DATA QUALITY
# ============================================================

@app.get("/data-quality")
def data_quality():

    datasets = {

        "automation":
            AUTOMATION_FILE,

        "route_profitability":
            ROUTE_PROFITABILITY_FILE,

        "baggage_sla":
            BAGGAGE_SLA_FILE,

        "passenger_experience":
            PASSENGER_EXPERIENCE_FILE,

        "demand_forecast":
            DEMAND_FORECAST_FILE,

        "cancellation_anomalies":
            CANCELLATION_FILE,

        "notification_audit":
            NOTIFICATION_FILE
    }


    results = {}

    overall_pass = True


    for name, path in datasets.items():

        if not path.exists():

            results[name] = {
                "exists": False,
                "rows": 0,
                "null_values": None,
                "duplicate_rows": None,
                "status": "MISSING"
            }

            overall_pass = False

            continue


        try:

            df = pd.read_parquet(
                path
            )

            null_values = safe_int(
                df.isnull()
                .sum()
                .sum()
            )

            duplicate_rows = safe_int(
                df.duplicated()
                .sum()
            )


            # We don't fail the complete API because
            # an analytical dataset contains nullable
            # model fields.

            status = (
                "PASS"
                if duplicate_rows == 0
                else "CHECK"
            )


            if status != "PASS":
                overall_pass = False


            results[name] = {

                "exists":
                    True,

                "rows":
                    len(df),

                "null_values":
                    null_values,

                "duplicate_rows":
                    duplicate_rows,

                "status":
                    status
            }


        except Exception as exc:

            results[name] = {

                "exists":
                    True,

                "rows":
                    0,

                "status":
                    "ERROR",

                "error":
                    str(exc)
            }

            overall_pass = False


    return {

        "quality_status":
            "PASS"
            if overall_pass
            else "CHECK",

        "datasets":
            results,

        "timestamp":
            now_utc()
    }


# ============================================================
# SYSTEM HEALTH
# ============================================================

@app.get("/system-health")
def system_health():

    checks = {

        "automation_output":
            (
                AUTOMATION_FILE.exists()
                or OLD_PREDICTIONS_FILE.exists()
            ),

        "notification_audit":
            NOTIFICATION_FILE.exists(),

        "route_profitability":
            ROUTE_PROFITABILITY_FILE.exists(),

        "baggage_sla":
            BAGGAGE_SLA_FILE.exists(),

        "passenger_experience":
            PASSENGER_EXPERIENCE_FILE.exists(),

        "demand_forecast":
            DEMAND_FORECAST_FILE.exists(),

        "cancellation_anomalies":
            CANCELLATION_FILE.exists(),

        "silver_flights":
            FLIGHTS_FILE.exists()
    }


    kafka_monitoring = False

    try:
        import duckdb

        warehouse_dir = BASE_DIR / "warehouse"

        if warehouse_dir.exists():

            for db_path in list(
                warehouse_dir.glob("*.duckdb")
            ) + list(
                warehouse_dir.glob("*.db")
            ):

                try:
                    con = duckdb.connect(
                        str(db_path),
                        read_only=True
                    )

                    tables = {
                        row[0]
                        for row in con.execute(
                            "SHOW TABLES"
                        ).fetchall()
                    }

                    con.close()

                    if "stream_monitoring" in tables:
                        kafka_monitoring = True
                        break

                except Exception:
                    continue

    except Exception:
        kafka_monitoring = False

    checks["kafka_monitoring"] = kafka_monitoring

    all_healthy = all(
        checks.values()
    )

    return {

        "status":
            "healthy"
            if all_healthy
            else "degraded",

        "checks":
            checks,

        "timestamp":
            now_utc()
    }


# ============================================================
# API ROOT
# ============================================================

@app.get("/")
def root():

    return {

        "application":
            "TravelOps 360",

        "service":
            "Airline Operations Control Center API",

        "version":
            "2.0.0",

        "status":
            "running",

        "docs":
            "/docs",

        "timestamp":
            now_utc()
    }