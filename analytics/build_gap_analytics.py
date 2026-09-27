from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


warnings.filterwarnings("ignore")


# ============================================================
# TRAVELOPS 360
# GAP ANALYTICS + ML MODULE
#
# Creates:
#   1. Route profitability
#   2. Baggage SLA
#   3. Passenger experience
#   4. Route demand
#   5. Demand forecasting
#   6. Cancellation anomaly detection
#
# Existing project code is not modified.
# ============================================================


ROOT = Path(__file__).resolve().parents[1]

SILVER = ROOT / "data" / "silver"
OUTPUT = ROOT / "analytics" / "outputs"

OUTPUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def find_parquet(keyword):
    """
    Find the first parquet file containing keyword.
    Searches recursively under data/silver.
    """

    keyword = keyword.lower()

    candidates = list(SILVER.rglob("*.parquet"))

    for path in candidates:
        if keyword in path.name.lower():
            return path

    return None


def read_table(keyword, required=False):

    path = find_parquet(keyword)

    if path is None:

        if required:
            raise FileNotFoundError(
                f"Could not find Silver parquet for: {keyword}"
            )

        print(f"[SKIP] No parquet found for '{keyword}'")
        return pd.DataFrame()

    print(f"[READ] {path}")

    df = pd.read_parquet(path)

    print(f"       rows={len(df):,}")

    return df


def normalize_columns(df):

    if df.empty:
        return df

    df = df.copy()

    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]

    return df


def first_existing(df, candidates):

    for column in candidates:

        if column in df.columns:
            return column

    return None


def save(df, filename):

    path = OUTPUT / filename

    df.to_parquet(
        path,
        index=False
    )

    print(
        f"[SAVE] {filename} "
        f"rows={len(df):,}"
    )


def safe_mape(y_true, y_pred):

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    denominator = np.where(
        np.abs(y_true) < 1,
        1,
        np.abs(y_true)
    )

    return float(
        np.mean(
            np.abs(y_true - y_pred)
            / denominator
        ) * 100
    )


# ============================================================
# LOAD SILVER DATA
# ============================================================

print()
print("=" * 70)
print("TRAVELOPS 360 - GAP ANALYTICS")
print("=" * 70)
print()


flights = normalize_columns(
    read_table("flights", required=True)
)

bookings = normalize_columns(
    read_table("bookings", required=True)
)

baggage = normalize_columns(
    read_table("baggage")
)

support = normalize_columns(
    read_table("support")
)

cancellations = normalize_columns(
    read_table("cancellation")
)


# ============================================================
# FLIGHTS PREPARATION
# ============================================================

flight_id_col = first_existing(
    flights,
    ["flight_id", "id"]
)

route_id_col = first_existing(
    flights,
    ["route_id", "route"]
)

flight_date_col = first_existing(
    flights,
    [
        "flight_date",
        "scheduled_departure",
        "departure_date"
    ]
)

status_col = first_existing(
    flights,
    ["status", "flight_status"]
)

delay_col = first_existing(
    flights,
    ["delay_minutes", "delay"]
)


if flight_date_col:

    flights["flight_date"] = pd.to_datetime(
        flights[flight_date_col],
        errors="coerce"
    ).dt.date

else:

    flights["flight_date"] = pd.NaT


if delay_col:

    flights["delay_minutes"] = pd.to_numeric(
        flights[delay_col],
        errors="coerce"
    ).fillna(0)

else:

    flights["delay_minutes"] = 0


# ============================================================
# 1. ROUTE PROFITABILITY
# ============================================================

print()
print("[1/6] ROUTE PROFITABILITY")


if not bookings.empty and not flights.empty:

    booking_flight_col = first_existing(
        bookings,
        ["flight_id"]
    )

    fare_col = first_existing(
        bookings,
        [
            "fare",
            "amount",
            "price",
            "booking_fare"
        ]
    )

    if (
        booking_flight_col
        and flight_id_col
        and route_id_col
        and fare_col
    ):

        revenue = bookings[
            [
                booking_flight_col,
                fare_col
            ]
        ].copy()

        revenue[fare_col] = pd.to_numeric(
            revenue[fare_col],
            errors="coerce"
        ).fillna(0)

        revenue = (
            revenue
            .groupby(
                booking_flight_col,
                as_index=False
            )[fare_col]
            .sum()
            .rename(
                columns={
                    booking_flight_col: "flight_id",
                    fare_col: "flight_revenue"
                }
            )
        )

        flight_route = flights[
            [
                flight_id_col,
                route_id_col,
                "delay_minutes"
            ]
        ].copy()

        flight_route = flight_route.rename(
            columns={
                flight_id_col: "flight_id",
                route_id_col: "route_id"
            }
        )

        route_data = flight_route.merge(
            revenue,
            on="flight_id",
            how="left"
        )

        route_data["flight_revenue"] = (
            route_data["flight_revenue"]
            .fillna(0)
        )

        route_summary = (
            route_data
            .groupby("route_id")
            .agg(
                total_revenue=(
                    "flight_revenue",
                    "sum"
                ),
                total_flights=(
                    "flight_id",
                    "nunique"
                ),
                avg_delay_minutes=(
                    "delay_minutes",
                    "mean"
                )
            )
            .reset_index()
        )

        route_summary[
            "revenue_per_flight"
        ] = (
            route_summary["total_revenue"]
            /
            route_summary["total_flights"]
            .replace(0, np.nan)
        )

        # Transparent synthetic operating-cost proxy.
        #
        # The assignment uses synthetic data, so we make the
        # assumption explicit rather than pretending that a
        # real airline cost field exists.
        route_summary[
            "estimated_operating_cost"
        ] = (
            route_summary["total_flights"] * 5000
            +
            route_summary["avg_delay_minutes"]
            * route_summary["total_flights"]
            * 100
            +
            route_summary["total_revenue"] * 0.45
        )

        route_summary["estimated_profit"] = (
            route_summary["total_revenue"]
            -
            route_summary["estimated_operating_cost"]
        )

        route_summary["profit_margin_pct"] = (
            route_summary["estimated_profit"]
            /
            route_summary["total_revenue"]
            .replace(0, np.nan)
            * 100
        )

        route_summary[
            "profitability_status"
        ] = np.select(
            [
                route_summary[
                    "profit_margin_pct"
                ] >= 20,

                route_summary[
                    "profit_margin_pct"
                ] >= 0
            ],
            [
                "HEALTHY",
                "BREAK_EVEN"
            ],
            default="LOSS"
        )

        route_summary = route_summary.sort_values(
            "estimated_profit",
            ascending=False
        )

        save(
            route_summary,
            "route_profitability.parquet"
        )

    else:

        print(
            "[WARN] Required route profitability "
            "columns not available."
        )


# ============================================================
# 2. BAGGAGE SLA
# ============================================================

print()
print("[2/6] BAGGAGE SLA")


if not baggage.empty:

    bag_id_col = first_existing(
        baggage,
        ["bag_id", "baggage_id"]
    )

    scan_time_col = first_existing(
        baggage,
        ["scan_time", "timestamp", "event_time"]
    )

    bag_status_col = first_existing(
        baggage,
        ["status", "scan_status"]
    )

    airport_col = first_existing(
        baggage,
        ["airport", "airport_id"]
    )

    if (
        bag_id_col
        and scan_time_col
    ):

        b = baggage.copy()

        b["scan_timestamp"] = pd.to_datetime(
            b[scan_time_col],
            errors="coerce"
        )

        b = b.dropna(
            subset=[
                bag_id_col,
                "scan_timestamp"
            ]
        )

        first_scan = (
            b.groupby(bag_id_col)[
                "scan_timestamp"
            ]
            .min()
            .rename("first_scan")
        )

        last_scan = (
            b.groupby(bag_id_col)[
                "scan_timestamp"
            ]
            .max()
            .rename("last_scan")
        )

        sla = pd.concat(
            [
                first_scan,
                last_scan
            ],
            axis=1
        ).reset_index()

        sla["cycle_minutes"] = (
            (
                sla["last_scan"]
                -
                sla["first_scan"]
            )
            .dt.total_seconds()
            / 60
        )

        # Operational SLA assumption for synthetic demo:
        # baggage should complete its scan journey within
        # 45 minutes.
        SLA_MINUTES = 45

        sla["sla_minutes"] = SLA_MINUTES

        sla["sla_breached"] = (
            sla["cycle_minutes"]
            > SLA_MINUTES
        )

        if airport_col:

            airport_map = (
                b.groupby(bag_id_col)[airport_col]
                .first()
                .rename("airport")
            )

            sla = sla.merge(
                airport_map,
                on=bag_id_col,
                how="left"
            )

        sla["sla_status"] = np.where(
            sla["sla_breached"],
            "BREACH",
            "WITHIN_SLA"
        )

        save(
            sla,
            "baggage_sla.parquet"
        )

    else:

        print(
            "[WARN] Baggage SLA columns unavailable."
        )


# ============================================================
# 3. PASSENGER EXPERIENCE
# ============================================================

print()
print("[3/6] PASSENGER EXPERIENCE")


if not support.empty:

    ticket_id_col = first_existing(
        support,
        ["ticket_id", "id"]
    )

    issue_col = first_existing(
        support,
        [
            "issue_type",
            "category",
            "issue"
        ]
    )

    created_col = first_existing(
        support,
        [
            "created_at",
            "created_time",
            "timestamp"
        ]
    )

    support_booking_col = first_existing(
        support,
        ["booking_id"]
    )

    if ticket_id_col:

        p = support.copy()

        if created_col:

            p["created_at"] = pd.to_datetime(
                p[created_col],
                errors="coerce"
            )

            p["ticket_date"] = (
                p["created_at"]
                .dt.date
            )

        else:

            p["ticket_date"] = pd.NaT

        if issue_col:

            issue_counts = (
                p.groupby(issue_col)
                .size()
                .reset_index(
                    name="ticket_count"
                )
                .sort_values(
                    "ticket_count",
                    ascending=False
                )
            )

            issue_counts[
                "complaint_share_pct"
            ] = (
                issue_counts["ticket_count"]
                /
                issue_counts["ticket_count"].sum()
                * 100
            )

        else:

            issue_counts = pd.DataFrame(
                {
                    "issue_type": [],
                    "ticket_count": [],
                    "complaint_share_pct": []
                }
            )

        if (
            support_booking_col
            and not bookings.empty
        ):

            booking_customer = bookings[
                [
                    support_booking_col
                ]
            ].drop_duplicates()

            p = p.merge(
                booking_customer,
                on=support_booking_col,
                how="left"
            )

        save(
            p,
            "passenger_experience.parquet"
        )

        issue_counts.to_parquet(
            OUTPUT /
            "passenger_issue_summary.parquet",
            index=False
        )

        print(
            f"[SAVE] passenger_issue_summary.parquet "
            f"rows={len(issue_counts):,}"
        )

    else:

        print(
            "[WARN] Support ticket ID unavailable."
        )


# ============================================================
# 4. ROUTE DEMAND
# ============================================================

print()
print("[4/6] ROUTE DEMAND")


demand = pd.DataFrame()

if (
    not bookings.empty
    and not flights.empty
):

    booking_flight_col = first_existing(
        bookings,
        ["flight_id"]
    )

    if (
        booking_flight_col
        and flight_id_col
        and route_id_col
    ):

        booking_counts = (
            bookings
            .groupby(
                booking_flight_col
            )
            .size()
            .reset_index(
                name="booking_count"
            )
            .rename(
                columns={
                    booking_flight_col:
                    "flight_id"
                }
            )
        )

        flight_route = flights[
            [
                flight_id_col,
                route_id_col,
                "flight_date"
            ]
        ].rename(
            columns={
                flight_id_col: "flight_id",
                route_id_col: "route_id"
            }
        )

        demand = flight_route.merge(
            booking_counts,
            on="flight_id",
            how="left"
        )

        demand["booking_count"] = (
            demand["booking_count"]
            .fillna(0)
        )

        demand = (
            demand
            .groupby(
                [
                    "flight_date",
                    "route_id"
                ],
                as_index=False
            )["booking_count"]
            .sum()
        )

        demand = demand.dropna(
            subset=["flight_date"]
        )

        demand["flight_date"] = pd.to_datetime(
            demand["flight_date"]
        )

        save(
            demand,
            "route_demand_daily.parquet"
        )


# ============================================================
# 5. DEMAND FORECASTING
# ============================================================

print()
print("[5/6] DEMAND FORECASTING")


forecast_results = []
forecast_metrics = {}

if not demand.empty:

    for route_id, group in demand.groupby(
        "route_id"
    ):

        g = (
            group
            .sort_values("flight_date")
            .copy()
        )

        if len(g) < 21:
            continue

        g["day_index"] = np.arange(len(g))

        g["lag_1"] = (
            g["booking_count"]
            .shift(1)
        )

        g["lag_7"] = (
            g["booking_count"]
            .shift(7)
        )

        g["lag_14"] = (
            g["booking_count"]
            .shift(14)
        )

        g["rolling_7"] = (
            g["booking_count"]
            .shift(1)
            .rolling(7)
            .mean()
        )

        g["dow"] = (
            g["flight_date"]
            .dt.dayofweek
        )

        g = g.dropna()

        if len(g) < 14:
            continue

        features = [
            "day_index",
            "lag_1",
            "lag_7",
            "lag_14",
            "rolling_7",
            "dow"
        ]

        X = g[features]
        y = g["booking_count"]

        split = max(
            int(len(g) * 0.8),
            len(g) - 7
        )

        if split <= 0 or split >= len(g):
            continue

        X_train = X.iloc[:split]
        X_test = X.iloc[split:]

        y_train = y.iloc[:split]
        y_test = y.iloc[split:]

        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=8,
            min_samples_split=4,
            random_state=42
        )

        model.fit(
            X_train,
            y_train
        )

        predictions = model.predict(
            X_test
        )

        mae = mean_absolute_error(
            y_test,
            predictions
        )

        rmse = np.sqrt(
            mean_squared_error(
                y_test,
                predictions
            )
        )

        mape = safe_mape(
            y_test,
            predictions
        )

        forecast_metrics[
            str(route_id)
        ] = {
            "mae": round(float(mae), 3),
            "rmse": round(float(rmse), 3),
            "mape_pct": round(float(mape), 2),
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test))
        }

        # Forecast the next 7 days.
        history = list(
            g["booking_count"].astype(float)
        )

        last_date = g["flight_date"].max()

        for step in range(1, 8):

            next_date = (
                last_date
                +
                pd.Timedelta(days=step)
            )

            lag_1 = history[-1]

            lag_7 = (
                history[-7]
                if len(history) >= 7
                else np.mean(history)
            )

            lag_14 = (
                history[-14]
                if len(history) >= 14
                else np.mean(history)
            )

            rolling_7 = np.mean(
                history[-7:]
            )

            row = pd.DataFrame(
                {
                    "day_index": [
                        len(g) + step
                    ],
                    "lag_1": [lag_1],
                    "lag_7": [lag_7],
                    "lag_14": [lag_14],
                    "rolling_7": [rolling_7],
                    "dow": [
                        next_date.dayofweek
                    ]
                }
            )

            prediction = max(
                0,
                float(
                    model.predict(row)[0]
                )
            )

            history.append(
                prediction
            )

            forecast_results.append(
                {
                    "route_id": route_id,
                    "forecast_date": next_date,
                    "predicted_bookings": round(
                        prediction,
                        2
                    ),
                    "model": "RandomForestRegressor"
                }
            )


    if forecast_results:

        forecast_df = pd.DataFrame(
            forecast_results
        )

        save(
            forecast_df,
            "demand_forecast.parquet"
        )

    else:

        print(
            "[WARN] No routes had enough "
            "history for forecasting."
        )


# ============================================================
# 6. CANCELLATION ANOMALY DETECTION
# ============================================================

print()
print("[6/6] CANCELLATION ANOMALY DETECTION")


anomaly = pd.DataFrame()

if not cancellations.empty:

    cancel_date_col = first_existing(
        cancellations,
        [
            "cancellation_date",
            "cancelled_at",
            "created_at",
            "timestamp",
            "flight_date"
        ]
    )

    cancel_flight_col = first_existing(
        cancellations,
        ["flight_id"]
    )

    if (
        cancel_date_col
        and cancel_flight_col
        and not flights.empty
    ):

        c = cancellations.copy()

        c["cancel_date"] = pd.to_datetime(
            c[cancel_date_col],
            errors="coerce"
        ).dt.date

        flight_route = flights[
            [
                flight_id_col,
                route_id_col
            ]
        ].rename(
            columns={
                flight_id_col: "flight_id",
                route_id_col: "route_id"
            }
        )

        c = c.rename(
            columns={
                cancel_flight_col:
                "flight_id"
            }
        )

        c = c.merge(
            flight_route,
            on="flight_id",
            how="left"
        )

        daily = (
            c.groupby(
                [
                    "cancel_date",
                    "route_id"
                ],
                as_index=False
            )
            .size()
            .rename(
                columns={
                    "size":
                    "cancellation_count"
                }
            )
        )

        daily["mean"] = (
            daily
            .groupby("route_id")[
                "cancellation_count"
            ]
            .transform("mean")
        )

        daily["std"] = (
            daily
            .groupby("route_id")[
                "cancellation_count"
            ]
            .transform("std")
            .fillna(0)
        )

        daily["z_score"] = np.where(
            daily["std"] > 0,
            (
                daily["cancellation_count"]
                -
                daily["mean"]
            )
            /
            daily["std"],
            0
        )

        daily["anomaly"] = (
            daily["z_score"] >= 2
        )

        daily["severity"] = np.select(
            [
                daily["z_score"] >= 3,
                daily["z_score"] >= 2
            ],
            [
                "HIGH",
                "MEDIUM"
            ],
            default="NORMAL"
        )

        anomaly = daily.sort_values(
            "z_score",
            ascending=False
        )

        save(
            anomaly,
            "cancellation_anomalies.parquet"
        )

    else:

        print(
            "[WARN] Cancellation columns unavailable."
        )


# ============================================================
# MODEL METRICS / DOCUMENTATION
# ============================================================

metrics = {

    "route_profitability": {
        "business_objective":
            "Identify routes generating strong or weak estimated financial returns.",
        "method":
            "Revenue aggregation with transparent synthetic operating-cost proxy.",
        "limitation":
            "Operating cost is estimated because the synthetic source data does not contain a real airline cost field."
    },

    "baggage_sla": {
        "business_objective":
            "Identify baggage journeys exceeding the operational SLA.",
        "sla_assumption_minutes": 45,
        "method":
            "Time between first and final recorded baggage scan.",
        "limitation":
            "Synthetic scan data may not represent the complete physical baggage journey."
    },

    "passenger_experience": {
        "business_objective":
            "Measure customer support demand and complaint mix.",
        "method":
            "Support-ticket volume and issue-type distribution.",
        "limitation":
            "Support tickets are a proxy for customer complaints."
    },

    "demand_forecasting": {
        "business_objective":
            "Forecast near-term booking demand by route.",
        "features": [
            "day_index",
            "lag_1",
            "lag_7",
            "lag_14",
            "rolling_7",
            "day_of_week"
        ],
        "train_test":
            "Chronological 80/20 split where sufficient history exists.",
        "metrics": [
            "MAE",
            "RMSE",
            "MAPE"
        ],
        "threshold_selection":
            "No classification threshold; forecast values are evaluated using regression error metrics.",
        "limitation":
            "Synthetic dataset has limited historical depth and may not capture seasonality or external demand drivers."
        ,
        "route_metrics":
            forecast_metrics
    },

    "cancellation_anomaly_detection": {
        "business_objective":
            "Detect unusual cancellation spikes by route and day.",
        "method":
            "Route-level z-score anomaly detection.",
        "threshold_selection":
            "z-score >= 2 indicates an anomaly; >= 3 indicates high severity.",
        "limitation":
            "Short synthetic history can make standard deviation estimates unstable."
    }
}


metrics_path = (
    OUTPUT /
    "analytics_model_metrics.json"
)

with open(
    metrics_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        metrics,
        f,
        indent=2,
        default=str
    )


print()
print("=" * 70)
print("GAP ANALYTICS COMPLETE")
print("=" * 70)

print()
print("Outputs:")

for file in sorted(
    OUTPUT.iterdir()
):

    if file.is_file():
        print(
            f"  ✓ {file.name}"
        )

print()
print(
    f"Metrics file: {metrics_path}"
)