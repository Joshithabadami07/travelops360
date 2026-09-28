import { useEffect, useMemo, useState } from "react";

import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

import "./App.css";


const API_BASE = "https://travelops360-api.onrender.com";


const AUTH_TOKEN_KEY = "travelops360_access_token";
const AUTH_USER_KEY = "travelops360_user";


async function apiFetch(url, options = {}) {

  const token = localStorage.getItem(AUTH_TOKEN_KEY);

  const headers = {
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    window.dispatchEvent(new Event("travelops-auth-expired"));
  }

  return response;
}


const COLORS = {
  high: "#ff4d6d",
  medium: "#ffb703",
  low: "#2dd4bf",
};


/* =========================================================
   AUTHENTICATION
========================================================= */

function LoginPage({ onLogin }) {

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {

    event.preventDefault();
    setError("");
    setLoading(true);

    try {

      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail || "Invalid email or password."
        );
      }

      localStorage.setItem(
        AUTH_TOKEN_KEY,
        data.access_token
      );

      localStorage.setItem(
        AUTH_USER_KEY,
        JSON.stringify(data.user || {})
      );

      onLogin(data.user || {});

    } catch (loginError) {

      setError(loginError.message || "Login failed.");

    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#07111f",
      padding: "24px",
      fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    }}>
      <div style={{
        width: "100%",
        maxWidth: "440px",
        background: "#101927",
        border: "1px solid #26364b",
        borderRadius: "18px",
        padding: "38px",
        boxShadow: "0 24px 70px rgba(0,0,0,0.35)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "30px" }}>
          <div style={{
            width: "48px",
            height: "48px",
            borderRadius: "12px",
            display: "grid",
            placeItems: "center",
            background: "#17263a",
            border: "1px solid #2b415c",
            color: "#2dd4bf",
            fontSize: "24px",
            fontWeight: 800,
          }}>T</div>
          <div>
            <div style={{ color: "#ffffff", fontSize: "22px", fontWeight: 800 }}>TravelOps 360</div>
            <div style={{ color: "#8fa4ba", fontSize: "12px", letterSpacing: "1.4px", marginTop: "3px" }}>AIRLINE OPERATIONS CONTROL</div>
          </div>
        </div>

        <div style={{ marginBottom: "24px" }}>
          <div style={{ color: "#2dd4bf", fontSize: "11px", fontWeight: 800, letterSpacing: "1.6px", marginBottom: "8px" }}>SECURE ACCESS</div>
          <h1 style={{ color: "#ffffff", margin: 0, fontSize: "28px" }}>Sign in to Control Center</h1>
          <p style={{ color: "#8fa4ba", lineHeight: 1.6, margin: "10px 0 0" }}>Access flight operations, risk analytics, alerts and platform health.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <label style={{ display: "block", color: "#b9c7d6", fontSize: "13px", fontWeight: 600, marginBottom: "8px" }}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="ops@travelops360.com"
            autoComplete="username"
            required
            style={{ width: "100%", boxSizing: "border-box", padding: "13px 14px", borderRadius: "10px", border: "1px solid #30445c", background: "#0b1524", color: "#ffffff", outline: "none", marginBottom: "16px" }}
          />

          <label style={{ display: "block", color: "#b9c7d6", fontSize: "13px", fontWeight: 600, marginBottom: "8px" }}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Enter your password"
            autoComplete="current-password"
            required
            style={{ width: "100%", boxSizing: "border-box", padding: "13px 14px", borderRadius: "10px", border: "1px solid #30445c", background: "#0b1524", color: "#ffffff", outline: "none", marginBottom: "16px" }}
          />

          {error && (
            <div style={{ padding: "11px 12px", borderRadius: "9px", background: "rgba(255,77,109,0.10)", border: "1px solid rgba(255,77,109,0.35)", color: "#ff8097", fontSize: "13px", marginBottom: "16px" }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{ width: "100%", padding: "13px 16px", border: 0, borderRadius: "10px", background: loading ? "#1d5360" : "#2dd4bf", color: "#06131d", fontWeight: 800, cursor: loading ? "not-allowed" : "pointer", fontSize: "14px" }}
          >
            {loading ? "Signing in..." : "Sign in to Control Center"}
          </button>
        </form>

        <div style={{ marginTop: "22px", paddingTop: "18px", borderTop: "1px solid #26364b", color: "#70869d", fontSize: "12px", lineHeight: 1.6 }}>
          Demo operator account: <strong style={{ color: "#9fb0c3" }}>ops@travelops360.com</strong>
        </div>
      </div>
    </div>
  );
}


function App() {

  const [authUser, setAuthUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "null");
    } catch {
      return null;
    }
  });

  const [authToken, setAuthToken] = useState(() =>
    localStorage.getItem(AUTH_TOKEN_KEY)
  );

  useEffect(() => {
    function handleAuthExpired() {
      setAuthToken(null);
      setAuthUser(null);
    }

    window.addEventListener("travelops-auth-expired", handleAuthExpired);
    return () => window.removeEventListener("travelops-auth-expired", handleAuthExpired);
  }, []);

  function handleLogin(user) {
    setAuthUser(user);
    setAuthToken(localStorage.getItem(AUTH_TOKEN_KEY));
  }

  function handleLogout() {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    setAuthToken(null);
    setAuthUser(null);
  }

  if (!authToken) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <DashboardApp
      authUser={authUser}
      onLogout={handleLogout}
    />
  );
}


/* =========================================================
   DASHBOARD APP
========================================================= */

function DashboardApp({ authUser, onLogout }) {

  const [activePage, setActivePage] = useState("overview");

  const [summary, setSummary] = useState(null);

  const [alerts, setAlerts] = useState([]);

  const [flights, setFlights] = useState([]);

  const [liveFlights, setLiveFlights] = useState([]);

  const [notifications, setNotifications] = useState([]);

  const [notificationSummary, setNotificationSummary] =
    useState(null);

  const [apiStatus, setApiStatus] =
    useState("checking");

  const [search, setSearch] =
    useState("");

  const [riskFilter, setRiskFilter] =
    useState("ALL");

  const [actionFilter, setActionFilter] =
    useState("ALL");

  const [currentPage, setCurrentPage] =
    useState(1);

  const rowsPerPage = 10;


  /* =======================================================
     LOAD DASHBOARD
  ======================================================= */

  useEffect(() => {

    // Initial load plus automatic refresh for the command center.
    loadDashboard();

    const refreshTimer = setInterval(() => {
      loadDashboard();
    }, 15000);

    return () => clearInterval(refreshTimer);

  }, []);


  async function loadDashboard() {

    try {

      setApiStatus("checking");


      const [
        summaryRes,
        alertsRes,
        flightsRes,
        liveFlightsRes,
        healthRes,
        notificationsRes,
        notificationSummaryRes,
      ] = await Promise.all([

        apiFetch(`${API_BASE}/summary`),

        apiFetch(`${API_BASE}/alerts`),

        apiFetch(`${API_BASE}/flights`),

        apiFetch(`${API_BASE}/flights/live?limit=5000`),

        apiFetch(`${API_BASE}/health`),

        apiFetch(`${API_BASE}/notifications`),

        apiFetch(
          `${API_BASE}/notifications/summary`
        ),

      ]);


      if (
        !summaryRes.ok ||
        !alertsRes.ok ||
        !flightsRes.ok ||
        !notificationsRes.ok ||
        !notificationSummaryRes.ok
      ) {

        throw new Error(
          "API request failed"
        );

      }


      const summaryData =
        await summaryRes.json();

      const alertsData =
        await alertsRes.json();

      const flightsData =
        await flightsRes.json();

      const liveFlightsData =
        await liveFlightsRes.json();

      await healthRes.json();

      const notificationsData =
        await notificationsRes.json();

      const notificationSummaryData =
        await notificationSummaryRes.json();


      setSummary(summaryData);

      setAlerts(
        normalizeArray(alertsData)
      );

      // The /alerts endpoint contains the complete 681-record risk queue.
      // Use it for Flight Operations instead of the /flights endpoint,
      // which is intentionally limited to a smaller response page.
      setFlights(
        normalizeArray(alertsData)
      );

      setLiveFlights(
        normalizeArray(liveFlightsData)
      );

      setNotifications(
        normalizeArray(
          notificationsData
        )
      );

      setNotificationSummary(
        notificationSummaryData
      );


      setApiStatus("connected");


    } catch (error) {

      console.error(
        "Dashboard loading error:",
        error
      );

      setApiStatus("offline");

    }

  }


  /* =======================================================
     NORMALIZE API ARRAYS
  ======================================================= */

  function normalizeArray(data) {

    if (Array.isArray(data))
      return data;

    if (Array.isArray(data?.data))
      return data.data;

    if (Array.isArray(data?.alerts))
      return data.alerts;

    if (Array.isArray(data?.flights))
      return data.flights;

    if (
      Array.isArray(
        data?.notifications
      )
    )
      return data.notifications;

    if (Array.isArray(data?.results))
      return data.results;

    return [];

  }


  /* =======================================================
     ACKNOWLEDGE ALERT
  ======================================================= */

  async function acknowledgeAlert(
    flightId
  ) {

    try {

      const response = await apiFetch(
        `${API_BASE}/alerts/${flightId}/acknowledge`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            owner: "Operations Control",
          }),

        }
      );


      if (!response.ok) {

        throw new Error(
          "Failed to acknowledge alert"
        );

      }


      await loadDashboard();


    } catch (error) {

      console.error(
        "Acknowledgement error:",
        error
      );

      alert(
        "Unable to acknowledge this alert."
      );

    }

  }


  /* =======================================================
     FILTER FLIGHTS
  ======================================================= */

  const filteredFlights = useMemo(() => {

    return flights.filter((flight) => {

      const flightId = String(
        flight.entity_id ??
          flight.flight_id ??
          flight.flightId ??
          flight.id ??
          ""
      ).toLowerCase();


      const aircraftId = String(
        flight.aircraft_id ??
          flight.aircraftId ??
          ""
      ).toLowerCase();


      const routeId = String(
        flight.route_id ??
          flight.routeId ??
          ""
      ).toLowerCase();


      const risk = String(
        flight.risk ??
          flight.risk_level ??
          flight.riskLevel ??
          ""
      ).toUpperCase();


      const action = String(
        flight.automation_action ??
          flight.action ??
          flight.recommended_action ??
          ""
      ).toUpperCase();


      const searchValue =
        search.toLowerCase();


      const matchesSearch =
        flightId.includes(
          searchValue
        ) ||
        aircraftId.includes(
          searchValue
        ) ||
        routeId.includes(
          searchValue
        );


      const matchesRisk =
        riskFilter === "ALL" ||
        risk === riskFilter;


      const matchesAction =
        actionFilter === "ALL" ||
        action === actionFilter;


      return (
        matchesSearch &&
        matchesRisk &&
        matchesAction
      );

    });

  }, [
    flights,
    search,
    riskFilter,
    actionFilter,
  ]);


  const totalPages = Math.max(
    1,
    Math.ceil(
      filteredFlights.length /
        rowsPerPage
    )
  );


  const visibleFlights =
    filteredFlights.slice(
      (currentPage - 1) *
        rowsPerPage,

      currentPage *
        rowsPerPage
    );


  useEffect(() => {

    setCurrentPage(1);

  }, [
    search,
    riskFilter,
    actionFilter,
  ]);


  /* =======================================================
     CHART DATA
  ======================================================= */

  const riskData = [

    {
      name: "High",
      value:
        summary?.high_risk ?? 0,
    },

    {
      name: "Medium",
      value:
        summary?.medium_risk ?? 0,
    },

    {
      name: "Low",
      value:
        summary?.low_risk ?? 0,
    },

  ];


  const actionData = [

    {
      name: "Urgent Review",
      value:
        summary?.urgent_actions ?? 0,
    },

    {
      name: "Turnaround",
      value:
        summary?.aircraft_turnaround_alerts ??
        0,
    },

    {
      name: "Monitoring",
      value: Math.max(
        0,
        (summary?.medium_risk ?? 0) -
          (summary?.aircraft_turnaround_alerts ??
            0)
      ),
    },

  ];


  const highRiskAlerts =
    alerts.filter(
      (alert) =>
        String(
          alert.risk ??
            alert.severity ??
            alert.risk_level ??
            ""
        ).toUpperCase() ===
        "HIGH"
    );


  const pageTitle = {

    overview:
      "Operations Overview",

    flights:
      "Flight Operations",

    alerts:
      "Alert Center",

    analytics:
      "Risk Analytics",

    streaming:
      "System Health",

  };


  /* =======================================================
     MAIN UI
  ======================================================= */

  return (

    <div className="app-shell">

      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
      />


      <main className="main-content">

        <header className="topbar">

          <div>

            <div className="breadcrumb">
              TRAVELOPS 360 /
              CONTROL CENTER
            </div>

            <h1>
              {pageTitle[activePage]}
            </h1>

          </div>


          <div className="topbar-actions">

            <div
              className={`connection-pill ${apiStatus}`}
            >

              <span className="status-dot"></span>

              {apiStatus ===
              "connected"
                ? "API Connected"
                : apiStatus ===
                  "checking"
                ? "Checking API..."
                : "API Offline"}

            </div>


            <button
              className="refresh-button"
              onClick={loadDashboard}
            >
              ↻ Refresh
            </button>

            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              padding: "8px 12px",
              border: "1px solid #26364b",
              borderRadius: "10px",
              background: "#101927",
              fontSize: "12px",
            }}>
              <span style={{ color: "#9fb0c3" }}>
                {authUser?.email || "Operator"}
              </span>
              <span style={{
                color: "#2dd4bf",
                fontWeight: 700,
                textTransform: "uppercase",
              }}>
                {authUser?.role || "operator"}
              </span>
            </div>

            <button
              className="refresh-button"
              onClick={onLogout}
              style={{ marginLeft: "2px" }}
            >
              Logout
            </button>

          </div>

        </header>


        {activePage ===
          "overview" && (

          <Overview
            summary={{
              ...summary,
              total_flights:
                liveFlights.length > 0
                  ? liveFlights.length
                  : 3058,
            }}
            riskData={riskData}
            actionData={actionData}
            apiStatus={apiStatus}
            notificationSummary={
              notificationSummary
            }
            setActivePage={
              setActivePage
            }
          />

        )}


        {activePage ===
          "flights" && (

          <FlightsPage
            flights={flights}
            filteredFlights={
              filteredFlights
            }
            visibleFlights={
              visibleFlights
            }
            search={search}
            setSearch={setSearch}
            riskFilter={
              riskFilter
            }
            setRiskFilter={
              setRiskFilter
            }
            actionFilter={
              actionFilter
            }
            setActionFilter={
              setActionFilter
            }
            currentPage={
              currentPage
            }
            setCurrentPage={
              setCurrentPage
            }
            totalPages={
              totalPages
            }
          />

        )}


        {activePage ===
          "alerts" && (

          <AlertsPage
            alerts={alerts}
            highRiskAlerts={
              highRiskAlerts
            }
            notifications={
              notifications
            }
            notificationSummary={
              notificationSummary
            }
            acknowledgeAlert={
              acknowledgeAlert
            }
          />

        )}


        {activePage ===
          "analytics" && (

          <AnalyticsPage />

        )}


        {activePage ===
          "streaming" && (

          <StreamingPage
            apiStatus={apiStatus}
          />

        )}

      </main>

    </div>

  );

}


/* =========================================================
   SIDEBAR
========================================================= */

function Sidebar({
  activePage,
  setActivePage,
}) {

  const menuItems = [

    {
      id: "overview",
      icon: "⌂",
      label: "Overview",
    },

    {
      id: "flights",
      icon: "✈",
      label: "Flight Operations",
    },

    {
      id: "alerts",
      icon: "⚠",
      label: "Alert Center",
    },

    {
      id: "analytics",
      icon: "◈",
      label: "Risk Analytics",
    },

    {
      id: "streaming",
      icon: "◉",
      label: "System Health",
    },

  ];


  return (

    <aside className="sidebar">

      <div className="brand">

        <div className="brand-logo">
          T
        </div>

        <div>

          <div className="brand-name">
            TravelOps
          </div>

          <div className="brand-subtitle">
            360 CONTROL
          </div>

        </div>

      </div>


      <div className="sidebar-section-title">
        COMMAND CENTER
      </div>


      <nav>

        {menuItems.map(
          (item) => (

            <button
              key={item.id}
              className={`nav-item ${
                activePage ===
                item.id
                  ? "active"
                  : ""
              }`}
              onClick={() =>
                setActivePage(
                  item.id
                )
              }
            >

              <span className="nav-icon">
                {item.icon}
              </span>

              <span>
                {item.label}
              </span>

            </button>

          )
        )}

      </nav>


      <div className="sidebar-bottom">

        <div className="system-mini-card">

          <div className="mini-status">

            <span className="status-dot online"></span>

            Operations System

          </div>

          <div className="mini-value">
            Operational
          </div>

          <div className="mini-description">
            Predictive flight monitoring active
          </div>

        </div>


        <div className="version">
          TravelOps 360 · v1.0
        </div>

      </div>

    </aside>

  );

}


/* =========================================================
   OVERVIEW
========================================================= */

function Overview({
  summary,
  riskData,
  actionData,
  apiStatus,
  notificationSummary,
  setActivePage,
}) {

  return (

    <div className="page">

      <section className="hero-section">

        <div>

          <div className="eyebrow">
            AIRLINE OPERATIONS
            INTELLIGENCE
          </div>

          <h2>
            Good afternoon,
            <span>
              {" "}Operations Team.
            </span>
          </h2>

          <p>
            Monitor flight risk,
            operational alerts and
            predictive insights from
            one control center.
          </p>

        </div>


        <div className="hero-status">

          <span className="pulse-ring"></span>

          <div>

            <strong>
              Control Center Active
            </strong>

            <small>
              Predictive monitoring
              enabled
            </small>

          </div>

        </div>

      </section>


      <section className="kpi-grid">

        <KpiCard
          title="Flights Analyzed"
          value={
            summary?.total_flights ??
            "—"
          }
          icon="✈"
          description="Flights in the operational dataset"
        />


        <KpiCard
          title="High Risk"
          value={
            summary?.high_risk ??
            "—"
          }
          icon="⚠"
          type="danger"
          description="Immediate attention"
        />


        <KpiCard
          title="Medium Risk"
          value={
            summary?.medium_risk ??
            "—"
          }
          icon="◐"
          type="warning"
          description="Requires monitoring"
        />


        <KpiCard
          title="Notifications Sent"
          value={
            notificationSummary?.sent ??
            "—"
          }
          icon="✉"
          type="success"
          description="Automated operational alerts"
        />

      </section>


      <section className="dashboard-grid">

        <div className="panel risk-panel">

          <PanelHeader
            title="Flight Risk Distribution"
            subtitle="Predicted operational risk"
          />


          <div className="risk-chart-container">

            <ResponsiveContainer
              width="100%"
              height={280}
            >

              <PieChart>

                <Pie
                  data={riskData}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={115}
                  paddingAngle={4}
                  dataKey="value"
                >

                  {riskData.map(
                    (entry, index) => (

                      <Cell
                        key={`cell-${index}`}
                        fill={
                          index === 0
                            ? COLORS.high
                            : index === 1
                            ? COLORS.medium
                            : COLORS.low
                        }
                      />

                    )
                  )}

                </Pie>


                <Tooltip
                  contentStyle={{
                    background:
                      "#101927",
                    border:
                      "1px solid #26364b",
                    borderRadius:
                      "10px",
                    color: "#fff",
                  }}
                />

              </PieChart>

            </ResponsiveContainer>


            <div className="chart-center">

              <strong>
                {summary?.total_flights ??
                  "—"}
              </strong>

              <span>
                FLIGHTS
              </span>

            </div>

          </div>


          <div className="risk-legend">

            <LegendItem
              color={COLORS.high}
              label="High Risk"
              value={
                summary?.high_risk
              }
            />

            <LegendItem
              color={COLORS.medium}
              label="Medium Risk"
              value={
                summary?.medium_risk
              }
            />

            <LegendItem
              color={COLORS.low}
              label="Low Risk"
              value={
                summary?.low_risk
              }
            />

          </div>

        </div>


        <div className="panel">

          <PanelHeader
            title="Operational Actions"
            subtitle="AI-generated operational response"
          />


          <div className="action-chart">

            <ResponsiveContainer
              width="100%"
              height={280}
            >

              <BarChart
                data={actionData}
                layout="vertical"
                margin={{
                  left: 15,
                  right: 20,
                  top: 15,
                  bottom: 15,
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#26364b"
                  horizontal={false}
                />

                <XAxis
                  type="number"
                  stroke="#718198"
                />

                <YAxis
                  type="category"
                  dataKey="name"
                  stroke="#718198"
                  width={90}
                />

                <Tooltip
                  contentStyle={{
                    background:
                      "#101927",
                    border:
                      "1px solid #26364b",
                    borderRadius:
                      "10px",
                  }}
                />

                <Bar
                  dataKey="value"
                  fill="#3b82f6"
                  radius={[
                    0,
                    6,
                    6,
                    0,
                  ]}
                />

              </BarChart>

            </ResponsiveContainer>

          </div>

        </div>

      </section>


      <section className="section-header">

        <div>

          <h3>
            Operations Command
          </h3>

          <p>
            Move directly to the areas
            requiring attention.
          </p>

        </div>

      </section>


      <section className="command-grid">

        <CommandCard
          icon="⚠"
          title="High-Risk Flights"
          value={
            summary?.high_risk ??
            "—"
          }
          description="Flights requiring operational review"
          type="danger"
          onClick={() =>
            setActivePage(
              "flights"
            )
          }
        />


        <CommandCard
          icon="🚨"
          title="Urgent Actions"
          value={
            summary?.urgent_actions ??
            "—"
          }
          description="Immediate operational interventions"
          type="danger"
          onClick={() =>
            setActivePage(
              "alerts"
            )
          }
        />


        <CommandCard
          icon="⏱"
          title="Turnaround Alerts"
          value={
            summary?.aircraft_turnaround_alerts ??
            "—"
          }
          description="Aircraft turnaround concerns"
          type="warning"
          onClick={() =>
            setActivePage(
              "alerts"
            )
          }
        />


        <CommandCard
          icon="✉"
          title="Notifications"
          value={
            notificationSummary?.sent ??
            "—"
          }
          description="Operational emails delivered"
          type="blue"
          onClick={() =>
            setActivePage(
              "alerts"
            )
          }
        />

      </section>


      <section className="bottom-grid">

        <div className="panel system-panel">

          <PanelHeader
            title="System Status"
            subtitle="Platform component health"
          />


          <SystemRow
            name="FastAPI Backend"
            status={
              apiStatus ===
              "connected"
                ? "Operational"
                : "Offline"
            }
            active={
              apiStatus ===
              "connected"
            }
          />


          <SystemRow
            name="Flight Risk Model"
            status="Available"
            active
          />


          <SystemRow
            name="Kafka Event Processing"
            status="Configured"
            active
          />


          <SystemRow
            name="Analytics Warehouse"
            status="Available"
            active
          />

        </div>


        <div className="panel insight-panel">

          <PanelHeader
            title="AI Operations Insight"
            subtitle="Predictive intelligence"
          />


          <div className="insight-content">

            <div className="insight-icon">
              ◈
            </div>

            <div>

              <h4>
                Previous flight disruption
                is the strongest predictive
                signal.
              </h4>

              <p>
                The current delay model
                uses previous-flight
                cascade behavior,
                turnaround time and
                historical delay
                information to identify
                future delay risk.
              </p>

            </div>

          </div>

        </div>

      </section>

    </div>

  );

}


/* =========================================================
   KPI CARD
========================================================= */

function KpiCard({
  title,
  value,
  icon,
  type = "blue",
  description,
}) {

  return (

    <div
      className={`kpi-card ${type}`}
    >

      <div className="kpi-top">

        <div className="kpi-icon">
          {icon}
        </div>

        <span className="kpi-label">
          {title}
        </span>

      </div>

      <div className="kpi-value">
        {value}
      </div>

      <div className="kpi-description">
        {description}
      </div>

    </div>

  );

}


/* =========================================================
   PANEL HEADER
========================================================= */

function PanelHeader({
  title,
  subtitle,
}) {

  return (

    <div className="panel-header">

      <div>

        <h3>
          {title}
        </h3>

        <p>
          {subtitle}
        </p>

      </div>

      <span className="panel-menu">
        •••
      </span>

    </div>

  );

}


/* =========================================================
   LEGEND
========================================================= */

function LegendItem({
  color,
  label,
  value,
}) {

  return (

    <div className="legend-item">

      <span
        className="legend-dot"
        style={{
          background: color,
        }}
      ></span>

      <span>
        {label}
      </span>

      <strong>
        {value ?? "—"}
      </strong>

    </div>

  );

}


/* =========================================================
   COMMAND CARD
========================================================= */

function CommandCard({
  icon,
  title,
  value,
  description,
  type,
  onClick,
}) {

  return (

    <button
      className={`command-card ${type}`}
      onClick={onClick}
    >

      <div className="command-icon">
        {icon}
      </div>

      <div className="command-info">

        <span>
          {title}
        </span>

        <strong>
          {value}
        </strong>

        <small>
          {description}
        </small>

      </div>

      <span className="command-arrow">
        →
      </span>

    </button>

  );

}


/* =========================================================
   SYSTEM ROW
========================================================= */

function SystemRow({
  name,
  status,
  active,
}) {

  return (

    <div className="system-row">

      <div className="system-name">

        <span
          className={`status-dot ${
            active
              ? "online"
              : "offline"
          }`}
        ></span>

        {name}

      </div>

      <span
        className={`system-status ${
          active
            ? "good"
            : "bad"
        }`}
      >
        {status}
      </span>

    </div>

  );

}


/* =========================================================
   FLIGHTS PAGE
========================================================= */

function FlightsPage({
  flights,
  filteredFlights,
  visibleFlights,
  search,
  setSearch,
  riskFilter,
  setRiskFilter,
  actionFilter,
  setActionFilter,
  currentPage,
  setCurrentPage,
  totalPages,
}) {

  return (

    <div className="page">

      <section className="page-intro">

        <div>
          <div className="eyebrow">
            FLIGHT INTELLIGENCE
          </div>

          <h2>
            Flight Risk Operations
          </h2>

          <p>
            Search, filter and review predictive flight risk across the network.
          </p>
        </div>

        <div className="data-count">
          <strong>
            {filteredFlights.length}
          </strong>
          <span>
            matching risk records
          </span>
        </div>

      </section>

      <div className="panel">

        <div className="filter-bar">

          <div className="search-box">
            <span>⌕</span>
            <input
              type="text"
              placeholder="Search flight ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
          >
            <option value="ALL">All Risk Levels</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>

          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
          >
            <option value="ALL">All Actions</option>
            <option value="URGENT_OPERATIONS_REVIEW">Urgent Review</option>
            <option value="OPERATIONS_REVIEW">Operations Review</option>
            <option value="AIRCRAFT_TURNAROUND_ALERT">Turnaround Alert</option>
            <option value="MONITOR_FLIGHT">Monitor Flight</option>
            <option value="MONITOR_AIRCRAFT">Monitor Aircraft</option>
            <option value="NO_ACTION">No Action</option>
          </select>

        </div>

        <div className="table-wrapper">

          <table className="flight-table">

            <thead>
              <tr>
                <th>FLIGHT</th>
                <th>RISK PROBABILITY</th>
                <th>RISK</th>
                <th>PRIORITY</th>
                <th>ACTION</th>
                <th>OWNER</th>
                <th>STATUS</th>
              </tr>
            </thead>

            <tbody>

              {visibleFlights.length === 0 ? (
                <tr>
                  <td colSpan="7">
                    <div className="empty-state">
                      No flight risk records match your filters.
                    </div>
                  </td>
                </tr>
              ) : (
                visibleFlights.map((flight, index) => {

                  const flightId =
                    flight.entity_id ??
                    flight.flight_id ??
                    flight.flightId ??
                    flight.id ??
                    "—";

                  const probability = getProbability(flight);

                  const risk = String(
                    flight.risk_level ??
                    flight.risk ??
                    flight.riskLevel ??
                    "UNKNOWN"
                  ).toUpperCase();

                  const action = getAction(flight);

                  const priority =
                    flight.priority ?? "—";

                  const owner =
                    flight.owner ??
                    "Operations Control";

                  const status =
                    flight.status ??
                    "OPEN";

                  return (
                    <tr key={`${flightId}-${index}`}>

                      <td>
                        <div className="flight-id">
                          <span className="airplane-mini">✈</span>
                          <strong>{flightId}</strong>
                        </div>
                        <div className="table-subtext">
                          {flight.trigger_reason ??
                            "Predicted future flight delay risk."}
                        </div>
                      </td>

                      <td>
                        <div className="probability">
                          <div className="probability-bar">
                            <div
                              className={`probability-fill ${risk.toLowerCase()}`}
                              style={{ width: `${probability}%` }}
                            ></div>
                          </div>
                          <span>
                            {probability.toFixed(1)}%
                          </span>
                        </div>
                      </td>

                      <td>
                        <RiskBadge risk={risk} />
                      </td>

                      <td>
                        <span className="priority-value">
                          P{priority}
                        </span>
                      </td>

                      <td>
                        <ActionBadge action={action} />
                      </td>

                      <td>
                        <span className="owner-text">
                          {owner}
                        </span>
                      </td>

                      <td>
                        <span
                          className={`status-badge ${String(status).toLowerCase()}`}
                        >
                          {status}
                        </span>
                      </td>

                    </tr>
                  );
                })
              )}

            </tbody>
          </table>
        </div>

        <div className="pagination">

          <span>
            Showing {filteredFlights.length === 0 ? 0 : (currentPage - 1) * 10 + 1}
            {" "}-{" "}
            {Math.min(currentPage * 10, filteredFlights.length)}
            {" "}of{" "}
            {filteredFlights.length}
          </span>

          <div className="pagination-buttons">
            <button
              disabled={currentPage === 1}
              onClick={() =>
                setCurrentPage((page) => Math.max(1, page - 1))
              }
            >
              ←
            </button>

            <span className="page-number">
              {currentPage}
            </span>

            <button
              disabled={currentPage >= totalPages}
              onClick={() =>
                setCurrentPage((page) => Math.min(totalPages, page + 1))
              }
            >
              →
            </button>
          </div>

        </div>

      </div>

    </div>
  );
}

/* =========================================================
   RISK BADGE
========================================================= */

function RiskBadge({
  risk,
}) {

  const normalized =
    risk.toLowerCase();


  return (

    <span
      className={`risk-badge ${normalized}`}
    >

      <span className="badge-dot"></span>

      {risk}

    </span>

  );

}


/* =========================================================
   ACTION BADGE
========================================================= */

function ActionBadge({
  action,
}) {

  const formatted =
    String(action || "—")
      .replaceAll("_", " ")
      .toLowerCase()
      .replace(
        /\b\w/g,
        (letter) =>
          letter.toUpperCase()
      );


  return (

    <span className="action-badge">
      {formatted}
    </span>

  );

}


/* =========================================================
   ALERT PAGE
========================================================= */

function AlertsPage({
  alerts,
  highRiskAlerts,
  notifications,
  notificationSummary,
  acknowledgeAlert,
}) {

  const mediumCount =
    alerts.filter(
      (a) =>
        String(
          a.risk ??
            a.severity ??
            a.risk_level ??
            ""
        ).toUpperCase() ===
        "MEDIUM"
    ).length;


  return (

    <div className="page">

      <section className="page-intro">

        <div>

          <div className="eyebrow">
            OPERATIONAL RESPONSE
          </div>

          <h2>
            Alert Center
          </h2>

          <p>
            Review predictive alerts,
            automated actions and
            notification history.
          </p>

        </div>


        <div className="alert-count">

          <strong>
            {alerts.length}
          </strong>

          <span>
            Active alerts
          </span>

        </div>

      </section>


      {/* ALERT SUMMARY */}

      <section className="alert-summary-grid">

        <div className="alert-stat danger">

          <span>
            HIGH RISK
          </span>

          <strong>
            {highRiskAlerts.length}
          </strong>

        </div>


        <div className="alert-stat warning">

          <span>
            MEDIUM RISK
          </span>

          <strong>
            {mediumCount}
          </strong>

        </div>


        <div className="alert-stat neutral">

          <span>
            TOTAL
          </span>

          <strong>
            {alerts.length}
          </strong>

        </div>


        <div className="alert-stat neutral">

          <span>
            EMAILS SENT
          </span>

          <strong>
            {notificationSummary?.sent ??
              0}
          </strong>

        </div>

      </section>


      {/* NOTIFICATION STATUS */}

      <section className="notification-summary-grid">

        <div className="notification-card">

          <span>
            NOTIFICATIONS
          </span>

          <strong>
            {notificationSummary?.total ??
              0}
          </strong>

          <small>
            Recorded in audit log
          </small>

        </div>


        <div className="notification-card success">

          <span>
            SENT
          </span>

          <strong>
            {notificationSummary?.sent ??
              0}
          </strong>

          <small>
            Successfully delivered
          </small>

        </div>


        <div className="notification-card danger">

          <span>
            FAILED
          </span>

          <strong>
            {notificationSummary?.failed ??
              0}
          </strong>

          <small>
            Delivery failures
          </small>

        </div>


        <div className="notification-card">

          <span>
            ACKNOWLEDGED
          </span>

          <strong>
            {notificationSummary?.acknowledged ??
              0}
          </strong>

          <small>
            Operationally reviewed
          </small>

        </div>

      </section>


      {/* ALERT QUEUE */}

      <div className="panel">

        <PanelHeader
          title="Operational Alert Queue"
          subtitle="Predicted events requiring attention"
        />


        <div className="alert-list">

          {alerts.length === 0 ? (

            <div className="empty-state">
              No alert records
              available.
            </div>

          ) : (

            alerts
              .slice(0, 30)
              .map(
                (
                  alert,
                  index
                ) => {

                  const flight =
                    alert.entity_id ??
                    alert.flight_id ??
                    alert.flightId ??
                    alert.id ??
                    "Unknown Flight";


                  const risk =
                    String(
                      alert.risk ??
                        alert.severity ??
                        alert.risk_level ??
                        "UNKNOWN"
                    ).toUpperCase();


                  const action =
                    getAction(
                      alert
                    );


                  const probability =
                    getProbability(
                      alert
                    );


                  return (

                    <div
                      className="alert-row"
                      key={`${flight}-${index}`}
                    >

                      <div className="alert-severity">

                        <RiskBadge
                          risk={risk}
                        />

                      </div>


                      <div className="alert-main">

                        <div className="alert-title">
                          Flight {flight}
                        </div>

                        <div className="alert-reason">

                          {alert.action_message ??
                            "Predictive delay risk detected"}

                        </div>

                      </div>


                      <div className="alert-probability">

                        <span>
                          Risk probability
                        </span>

                        <strong>
                          {probability.toFixed(
                            1
                          )}
                          %
                        </strong>

                      </div>


                      <div className="alert-action">

                        <ActionBadge
                          action={action}
                        />

                      </div>

                    </div>

                  );

                }
              )

          )}

        </div>

      </div>


      {/* NOTIFICATION HISTORY */}

      <div className="panel notification-history-panel">

        <PanelHeader
          title="Notification History"
          subtitle="Automated operational actions and audit trail"
        />


        {notifications.length ===
        0 ? (

          <div className="empty-state">
            No notifications recorded.
          </div>

        ) : (

          <div className="notification-table-wrapper">

            <table className="flight-table">

              <thead>

                <tr>

                  <th>
                    TIME
                  </th>

                  <th>
                    FLIGHT
                  </th>

                  <th>
                    RISK
                  </th>

                  <th>
                    ACTION
                  </th>

                  <th>
                    OWNER
                  </th>

                  <th>
                    STATUS
                  </th>

                  <th>
                    CONTROL
                  </th>

                </tr>

              </thead>


              <tbody>

                {notifications.map(
                  (
                    notification,
                    index
                  ) => {

                    const status =
                      String(
                        notification.status ??
                          "UNKNOWN"
                      ).toUpperCase();


                    return (

                      <tr
                        key={`${notification.entity_id ?? notification.flight_id ?? notification.flightId ?? index}-${index}`}
                      >

                        <td>
                          {formatTimestamp(
                            notification.timestamp
                          )}
                        </td>


                        <td>

                          <strong>
                            {notification.entity_id ??
                              notification.flight_id ??
                              notification.flightId ??
                              notification.id ??
                              "—"}
                          </strong>

                        </td>


                        <td>

                          <RiskBadge
                            risk={
                              notification.risk_level ??
                              "UNKNOWN"
                            }
                          />

                        </td>


                        <td>

                          <ActionBadge
                            action={
                              notification.automation_action ??
                              "—"
                            }
                          />

                        </td>


                        <td>
                          {notification.owner ??
                            "—"}
                        </td>


                        <td>

                          <StatusBadge
                            status={status}
                          />

                        </td>


                        <td>

                          {status ===
                            "SENT" ? (

                            <button
                              className="acknowledge-button"
                              onClick={() =>
                                acknowledgeAlert(
                                  notification.entity_id ??
                                  notification.flight_id ??
                                  notification.flightId ??
                                  notification.id
                                )
                              }
                            >
                              Acknowledge
                            </button>

                          ) : (

                            <span className="acknowledged-label">
                              ✓ Reviewed
                            </span>

                          )}

                        </td>

                      </tr>

                    );

                  }
                )}

              </tbody>

            </table>

          </div>

        )}

      </div>

    </div>

  );

}


/* =========================================================
   STATUS BADGE
========================================================= */

function StatusBadge({
  status,
}) {

  const normalized =
    status.toLowerCase();


  return (

    <span
      className={`status-badge ${normalized}`}
    >

      <span className="badge-dot"></span>

      {status}

    </span>

  );

}


/* =========================================================
   ANALYTICS PAGE
========================================================= */

function AnalyticsPage() {
  const [data, setData] = useState({
    dashboard: null,
    profitability: [],
    demandForecast: [],
    routeDemand: [],
    baggage: [],
    passenger: [],
    passengerIssues: [],
    cancellations: [],
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const featureData = [
    { feature: "Previous Cascade", importance: 58.2 },
    { feature: "Turnaround Time", importance: 9.1 },
    { feature: "Previous Propagated Delay", importance: 6.2 },
    { feature: "Departure Hour", importance: 6.1 },
    { feature: "Previous Flight Delay", importance: 6.1 },
    { feature: "Previous Flight Delayed", importance: 5.1 },
  ];

  useEffect(() => {
    let mounted = true;

    async function loadAnalytics() {
      try {
        setLoading(true);
        setError("");

        const endpoints = [
          "dashboard",
          "routes/profitability?limit=1000",
          "forecasts/demand?limit=1000",
          "routes/demand?limit=1000",
          "baggage/sla?limit=5000",
          "passenger/experience?limit=5000",
          "passenger/issues",
          "cancellations/anomalies?limit=1000",
        ];

        const results = await Promise.allSettled(
          endpoints.map((endpoint) => apiFetch(`${API_BASE}/${endpoint}`))
        );

        const payloads = await Promise.all(
          results.map(async (result) => {
            if (result.status !== "fulfilled" || !result.value.ok) return null;
            try {
              return await result.value.json();
            } catch {
              return null;
            }
          })
        );

        if (!mounted) return;

        const [
          dashboard,
          profitability,
          demandForecast,
          routeDemand,
          baggage,
          passenger,
          passengerIssues,
          cancellations,
        ] = payloads;

        setData({
          dashboard,
          profitability: extractRows(profitability),
          demandForecast: extractRows(demandForecast),
          routeDemand: extractRows(routeDemand),
          baggage: extractRows(baggage),
          passenger: extractRows(passenger),
          passengerIssues: extractRows(passengerIssues),
          cancellations: extractRows(cancellations),
        });

        const failed = results.filter((r) => r.status !== "fulfilled").length;
        if (failed > 0) {
          setError(`${failed} analytics API request${failed > 1 ? "s" : ""} could not be reached.`);
        }
      } catch (err) {
        console.error("Risk analytics loading error:", err);
        if (mounted) setError("Some analytics could not be loaded from the API.");
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadAnalytics();
    return () => {
      mounted = false;
    };
  }, []);

  // Compatible with the exact response keys used by api/main.py:
  // routes, forecast, demand, records, issues and anomalies.
  function extractRows(value) {
    if (!value) return [];
    if (Array.isArray(value)) return value;

    const keys = [
      "data",
      "results",
      "records",
      "rows",
      "items",
      "forecasts",
      "forecast",
      "routes",
      "demand",
      "issues",
      "anomalies",
      "values",
      "flights",
      "alerts",
      "notifications",
    ];

    for (const key of keys) {
      if (Array.isArray(value?.[key])) return value[key];
    }

    for (const key of ["payload", "result", "response", "output"]) {
      if (value?.[key]) {
        const nested = extractRows(value[key]);
        if (nested.length) return nested;
      }
    }

    return [];
  }

  const dashboard = data.dashboard || {};

  const number = (value, fallback = 0) => {
    if (typeof value === "number" && Number.isFinite(value)) return value;

    if (typeof value === "string") {
      const cleaned = value.replace(/[₹,%\s]/g, "").replace(/,/g, "");
      const n = Number(cleaned);
      return Number.isFinite(n) ? n : fallback;
    }

    return fallback;
  };

  const valueFrom = (row, keys, fallback = null) => {
    for (const key of keys) {
      if (row && row[key] !== undefined && row[key] !== null && row[key] !== "") {
        return row[key];
      }
    }
    return fallback;
  };

  // If a parquet field uses a different numeric name, find a usable
  // numeric value automatically instead of leaving the chart empty.
  const numericValueFromRow = (row, preferredKeys = [], fallback = NaN) => {
    const preferred = valueFrom(row, preferredKeys, null);
    const preferredNumber = number(preferred, NaN);

    if (Number.isFinite(preferredNumber)) return preferredNumber;
    if (!row || typeof row !== "object") return fallback;

    const ignored = new Set([
      "id",
      "flight_id",
      "route_id",
      "aircraft_id",
      "customer_id",
      "booking_id",
      "baggage_id",
      "ticket_id",
      "date",
      "flight_date",
      "scheduled_departure",
      "actual_departure",
      "forecast_date",
      "prediction_date",
      "target_date",
      "ds",
      "timestamp",
      "created_at",
      "updated_at",
    ]);

    for (const [key, raw] of Object.entries(row)) {
      if (ignored.has(key)) continue;
      const n = number(raw, NaN);
      if (Number.isFinite(n)) return n;
    }

    return fallback;
  };

  const textFromRow = (row, preferredKeys = [], fallback = "—") => {
    const preferred = valueFrom(row, preferredKeys, null);

    if (preferred !== null && preferred !== undefined && String(preferred).trim() !== "") {
      return String(preferred);
    }

    if (row && typeof row === "object") {
      for (const [key, raw] of Object.entries(row)) {
        if (
          raw !== null &&
          raw !== undefined &&
          String(raw).trim() !== "" &&
          ![
            "id",
            "flight_id",
            "route_id",
            "aircraft_id",
            "customer_id",
            "booking_id",
            "baggage_id",
            "ticket_id",
          ].includes(key)
        ) {
          if (typeof raw === "string" && !raw.includes("T")) return raw;
        }
      }
    }

    return fallback;
  };

  const formatNumber = (value) => number(value, NaN).toLocaleString();

  const formatMoney = (value) => {
    const n = number(value, NaN);
    if (!Number.isFinite(n)) return "—";
    if (Math.abs(n) >= 1000000) return `₹${(n / 1000000).toFixed(1)}M`;
    if (Math.abs(n) >= 1000) return `₹${(n / 1000).toFixed(0)}K`;
    return `₹${n.toFixed(0)}`;
  };

  const routeCount = number(
    valueFrom(dashboard, ["route_profitability_count", "routeProfitabilityCount"], null),
    data.profitability.length || 97
  );

  const baggageCount = number(
    valueFrom(dashboard, ["baggage_records", "baggageRecords"], null),
    279399
  );

  const passengerCount = number(
    valueFrom(dashboard, ["passenger_experience_records", "passengerExperienceRecords"], null),
    29804
  );

  const forecastCount = number(
    valueFrom(dashboard, ["forecast_records", "forecastRecords"], null),
    231
  );

  const cancellationCount = number(
    valueFrom(dashboard, ["cancellation_records", "cancellationRecords"], null),
    65
  );

  const routeDemandCount = data.routeDemand.length || 2383;

  const routeProfitRows = data.profitability
    .map((row) => {
      const revenue = numericValueFromRow(
        row,
        ["revenue", "route_revenue", "total_revenue", "totalRevenue", "routeRevenue"],
        0
      );

      const cost = numericValueFromRow(
        row,
        ["operating_cost", "estimated_cost", "cost", "total_cost", "operatingCost"],
        0
      );

      const explicitProfit = numericValueFromRow(
        row,
        [
          "profit",
          "route_profit",
          "profit_amount",
          "net_profit",
          "estimated_profit",
          "estimatedProfit",
          "total_profit",
          "profitability",
        ],
        NaN
      );

      return {
        route: textFromRow(
          row,
          ["route_id", "route", "route_code", "routeId"],
          "Route"
        ),
        revenue,
        cost,
        profit: Number.isFinite(explicitProfit) ? explicitProfit : revenue - cost,
      };
    })
    .filter((row) => Number.isFinite(row.profit))
    .sort((a, b) => b.profit - a.profit)
    .slice(0, 10);

  const forecastRows = data.demandForecast
    .map((row, index) => {
      const rawDate = valueFrom(
        row,
        [
          "forecast_date",
          "date",
          "flight_date",
          "ds",
          "target_date",
          "prediction_date",
          "date_key",
        ],
        null
      );

      const actual = numericValueFromRow(
        row,
        [
          "actual_demand",
          "actual_bookings",
          "demand",
          "bookings",
          "actual",
          "historical_demand",
          "historical_bookings",
          "actual_value",
          "y",
        ],
        NaN
      );

      const forecast = numericValueFromRow(
        row,
        [
          "forecast_demand",
          "predicted_demand",
          "prediction",
          "forecast",
          "predicted_bookings",
          "forecasted_bookings",
          "yhat",
          "predicted_value",
          "forecast_value",
          "prediction_value",
        ],
        NaN
      );

      const fallbackNumeric =
        !Number.isFinite(actual) && !Number.isFinite(forecast)
          ? numericValueFromRow(row, [], NaN)
          : NaN;

      const finalForecast = Number.isFinite(forecast)
        ? forecast
        : Number.isFinite(actual)
        ? actual
        : fallbackNumeric;

      const labelSource = rawDate ?? `D${index + 1}`;
      const label =
        String(labelSource).length > 16
          ? String(labelSource).slice(0, 16)
          : String(labelSource);

      return {
        label,
        actual: Number.isFinite(actual) ? actual : NaN,
        forecast: Number.isFinite(finalForecast) ? finalForecast : NaN,
      };
    })
    .filter(
      (row) =>
        Number.isFinite(row.actual) || Number.isFinite(row.forecast)
    )
    .slice(-14);

  const routeDemandRows = data.routeDemand
    .map((row, index) => ({
      route: textFromRow(
        row,
        ["route_id", "route", "route_code", "routeId", "route_name"],
        `Route ${index + 1}`
      ),
      demand: numericValueFromRow(
        row,
        [
          "demand",
          "booking_count",
          "bookings",
          "total_bookings",
          "daily_demand",
          "passenger_demand",
          "total_demand",
          "demand_count",
          "booking_demand",
        ],
        NaN
      ),
    }))
    .filter((row) => Number.isFinite(row.demand))
    .sort((a, b) => b.demand - a.demand)
    .slice(0, 10);

  const baggageBreaches = data.baggage.filter((row) => {
    const status = String(
      valueFrom(
        row,
        [
          "sla_status",
          "status",
          "sla_breach",
          "breach",
          "slaStatus",
          "sla_breach_flag",
          "is_breach",
        ],
        ""
      )
    ).toUpperCase();

    return (
      status.includes("BREACH") ||
      status === "LATE" ||
      status === "FAILED" ||
      status === "1" ||
      status === "TRUE" ||
      status === "YES"
    );
  }).length;

  const issueCounts = {};

  data.passenger.forEach((row) => {
    const issue = String(
      valueFrom(
        row,
        [
          "issue_type",
          "category",
          "issue",
          "ticket_type",
          "ticket_category",
          "issue_category",
        ],
        "OTHER"
      )
    );

    issueCounts[issue] = (issueCounts[issue] || 0) + 1;
  });

  data.passengerIssues.forEach((row) => {
    const issue = String(
      valueFrom(
        row,
        ["issue_type", "category", "issue", "ticket_type", "name"],
        "OTHER"
      )
    );

    const count = numericValueFromRow(
      row,
      ["count", "ticket_count", "tickets", "total", "value"],
      0
    );

    if (count > 0) {
      issueCounts[issue] = Math.max(issueCounts[issue] || 0, count);
    }
  });

  const passengerIssueChart = Object.entries(issueCounts)
    .map(([issue, count]) => ({
      issue: issue.replace(/_/g, " "),
      count,
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  const cancellationRows = data.cancellations;

  return (
    <div className="page">
      <section className="hero-section">
        <div>
          <div className="eyebrow">PREDICTIVE OPERATIONS INTELLIGENCE</div>
          <h2>Risk Analytics</h2>
          <p>
            Combine machine-learning risk prediction with route, demand,
            baggage, passenger and cancellation analytics.
          </p>
        </div>

        <div className="hero-status">
          <span className="pulse-ring"></span>
          <div>
            <strong>{loading ? "Loading Analytics" : "Analytics Ready"}</strong>
            <small>
              {error || "Connected to TravelOps 360 analytical APIs"}
            </small>
          </div>
        </div>
      </section>

      <section className="kpi-grid">
        <KpiCard
          title="Test Accuracy"
          value="86.7%"
          icon="◎"
          description="Random Forest holdout performance"
        />
        <KpiCard
          title="High-Risk F1"
          value="0.90"
          icon="⚠"
          type="danger"
          description="Positive class F1 score"
        />
        <KpiCard
          title="Routes"
          value={formatNumber(routeCount)}
          icon="↔"
          description="Route profitability records"
        />
        <KpiCard
          title="Forecast Records"
          value={formatNumber(forecastCount)}
          icon="◌"
          type="success"
          description="Demand forecast observations"
        />
      </section>

      <section className="dashboard-grid">
        <div className="panel" style={{ gridColumn: "1 / -1" }}>
          <PanelHeader
            title="Delay Risk Analytics"
            subtitle="Predictive intelligence used to identify future flight delay risk"
          />

          <div className="kpi-grid" style={{ marginTop: 16 }}>
            <KpiCard
              title="Training Data"
              value="781"
              icon="▦"
              description="Training observations"
            />
            <KpiCard
              title="Test Data"
              value="196"
              icon="▤"
              description="Holdout observations"
            />
            <KpiCard
              title="Model"
              value="Random Forest"
              icon="◇"
              description="300 trees · depth 10"
            />
            <KpiCard
              title="Target"
              value="Future Delay"
              icon="→"
              description="Balanced class weighting"
            />
          </div>
        </div>

        <div className="panel">
          <PanelHeader
            title="Feature Importance"
            subtitle="Signals used by the prediction model"
          />

          <ResponsiveContainer width="100%" height={320}>
            <BarChart
              data={featureData}
              layout="vertical"
              margin={{ left: 20, right: 25, top: 10, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" unit="%" />
              <YAxis
                type="category"
                dataKey="feature"
                width={145}
                tick={{ fontSize: 10 }}
              />
              <Tooltip
                formatter={(value) => [`${value}%`, "Importance"]}
              />
              <Bar
                dataKey="importance"
                name="Importance"
                fill="#3b82f6"
                radius={[0, 5, 5, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="panel">
          <PanelHeader
            title="Model Interpretation"
            subtitle="Business objective and limitations"
          />

          <div style={{ lineHeight: 1.7, marginTop: 18 }}>
            <p>
              <strong>Business objective:</strong> Identify flights with
              elevated future delay risk so operations teams can intervene
              before disruption propagates.
            </p>

            <p>
              <strong>Training approach:</strong> Historical flight sequences
              are split into training and holdout observations. The model uses
              previous-flight disruption, cascade behavior, turnaround time
              and scheduled departure features.
            </p>

            <div className="notice-box" style={{ marginTop: 18 }}>
              <strong>Model limitation</strong>
              <p style={{ marginBottom: 0 }}>
                Performance is based on the available synthetic project dataset
                and test split. Production performance may differ when exposed
                to real operational data.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-heading" style={{ marginTop: 28 }}>
        <div>
          <div className="eyebrow">BUSINESS ANALYTICS</div>
          <h2 style={{ marginBottom: 4 }}>Operational Intelligence</h2>
          <p>Analytical outputs generated from the TravelOps 360 pipeline.</p>
        </div>
      </section>

      <section className="kpi-grid">
        <KpiCard
          title="Route Profitability"
          value={formatNumber(routeCount)}
          icon="₹"
          description="Route-level analytical records"
        />
        <KpiCard
          title="Baggage Records"
          value={formatNumber(baggageCount)}
          icon="▣"
          description="Operational scan records"
        />
        <KpiCard
          title="Passenger Records"
          value={formatNumber(passengerCount)}
          icon="♙"
          description="Support / experience records"
        />
        <KpiCard
          title="Cancellations"
          value={formatNumber(cancellationCount)}
          icon="×"
          type="warning"
          description="Cancellation records"
        />
      </section>

      <section className="dashboard-grid">
        <div className="panel" style={{ gridColumn: "1 / -1" }}>
          <PanelHeader
            title="Route Profitability"
            subtitle="Top route-level profitability observations"
          />

          {routeProfitRows.length > 0 ? (
            <ResponsiveContainer width="100%" height={340}>
              <BarChart
                data={routeProfitRows}
                layout="vertical"
                margin={{ top: 10, right: 35, left: 15, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  tickFormatter={(v) => formatMoney(v)}
                />
                <YAxis
                  type="category"
                  dataKey="route"
                  width={85}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  formatter={(v, name) => [
                    formatMoney(v),
                    name === "profit" ? "Estimated Profit" : "Revenue",
                  ]}
                />
                <Bar
                  dataKey="profit"
                  name="Profit"
                  fill="#2dd4bf"
                  radius={[0, 6, 6, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyAnalytics
              message={`The API reports ${formatNumber(
                routeCount
              )} route profitability records, but no chart rows were returned.`}
            />
          )}

          <div className="notice-box" style={{ marginTop: 12 }}>
            <strong>Data assumption</strong>
            <p style={{ marginBottom: 0 }}>
              Route profitability uses a synthetic operating-cost proxy from
              the project analytics layer, not actual airline accounting costs.
            </p>
          </div>
        </div>

        <div className="panel">
          <PanelHeader
            title="Demand Forecast"
            subtitle={`${formatNumber(forecastCount)} forecast records`}
          />

          {forecastRows.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart
                data={forecastRows}
                margin={{ top: 15, right: 15, left: 0, bottom: 35 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="label"
                  angle={-30}
                  textAnchor="end"
                  height={60}
                  tick={{ fontSize: 10 }}
                />
                <YAxis />
                <Tooltip
                  formatter={(v, name) => [
                    formatNumber(v),
                    name === "forecast" ? "Forecast" : "Actual",
                  ]}
                />

                {forecastRows.some((r) => Number.isFinite(r.actual)) && (
                  <Bar
                    dataKey="actual"
                    name="Actual"
                    fill="#64748b"
                    radius={[4, 4, 0, 0]}
                  />
                )}

                {forecastRows.some((r) => Number.isFinite(r.forecast)) && (
                  <Bar
                    dataKey="forecast"
                    name="Forecast"
                    fill="#38bdf8"
                    radius={[4, 4, 0, 0]}
                  />
                )}
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyAnalytics
              message={`The API reports ${formatNumber(
                forecastCount
              )} forecast records, but no numeric forecast values were available for the chart.`}
            />
          )}

          <p className="panel-footnote">
            Forecast output is based on the project demand forecasting model
            and synthetic data.
          </p>
        </div>

        <div className="panel">
          <PanelHeader
            title="Route Demand"
            subtitle={`${formatNumber(
              routeDemandCount
            )} daily route-demand records`}
          />

          {routeDemandRows.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart
                data={routeDemandRows}
                layout="vertical"
                margin={{ left: 5, right: 25, top: 10, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis
                  type="category"
                  dataKey="route"
                  width={80}
                  tick={{ fontSize: 10 }}
                />
                <Tooltip
                  formatter={(v) => [
                    formatNumber(v),
                    "Demand",
                  ]}
                />
                <Bar
                  dataKey="demand"
                  name="Demand"
                  fill="#818cf8"
                  radius={[0, 5, 5, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyAnalytics
              message={`The API reports ${formatNumber(
                routeDemandCount
              )} daily route-demand records, but no numeric demand values were available for the chart.`}
            />
          )}
        </div>

        <div className="panel">
          <PanelHeader
            title="Baggage Analytics"
            subtitle={`${formatNumber(
              baggageCount
            )} operational records`}
          />

          <div className="analytics-stat-large">
            {formatNumber(baggageBreaches)}
          </div>

          <div className="analytics-stat-label">
            SLA breaches detected in the records returned by the API
          </div>

          <div className="notice-box" style={{ marginTop: 20 }}>
            <strong>Operational SLA definition</strong>
            <p style={{ marginBottom: 0 }}>
              This project uses a 45-minute scan-based operational threshold.
              It should not be interpreted as a complete airport baggage-
              delivery SLA.
            </p>
          </div>
        </div>

        <div className="panel">
          <PanelHeader
            title="Passenger Experience"
            subtitle={`${formatNumber(
              passengerCount
            )} support records`}
          />

          {passengerIssueChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart
                data={passengerIssueChart}
                layout="vertical"
                margin={{ left: 5, right: 20, top: 10, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis
                  type="category"
                  dataKey="issue"
                  width={120}
                  tick={{ fontSize: 10 }}
                />
                <Tooltip
                  formatter={(v) => [
                    formatNumber(v),
                    "Support Records",
                  ]}
                />
                <Bar
                  dataKey="count"
                  name="Records"
                  fill="#f59e0b"
                  radius={[0, 5, 5, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyAnalytics
              message={`The dashboard reports ${formatNumber(
                passengerCount
              )} passenger/support records, but no issue-category rows were returned.`}
            />
          )}
        </div>

        <div className="panel" style={{ gridColumn: "1 / -1" }}>
          <PanelHeader
            title="Cancellation Analysis"
            subtitle={`${formatNumber(
              cancellationCount
            )} cancellation records`}
          />

          {cancellationRows.length > 0 ? (
            <div className="table-wrap" style={{ marginTop: 12 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Flight / Entity</th>
                    <th>Date</th>
                    <th>Reason</th>
                    <th>Anomaly</th>
                  </tr>
                </thead>

                <tbody>
                  {cancellationRows.slice(0, 8).map((row, index) => (
                    <tr
                      key={`${valueFrom(
                        row,
                        ["flight_id", "entity_id", "id"],
                        index
                      )}-${index}`}
                    >
                      <td>
                        {valueFrom(
                          row,
                          ["flight_id", "entity_id", "id"],
                          "—"
                        )}
                      </td>

                      <td>
                        {valueFrom(
                          row,
                          ["date", "flight_date", "scheduled_departure"],
                          "—"
                        )}
                      </td>

                      <td>
                        {valueFrom(
                          row,
                          ["reason", "cancellation_reason", "cause"],
                          "—"
                        )}
                      </td>

                      <td>
                        <span className="status-badge success">
                          ANALYSIS ROW
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="notice-box" style={{ marginTop: 12 }}>
              <strong>No cancellation anomaly rows returned</strong>
              <p style={{ marginBottom: 0 }}>
                The dashboard still contains {formatNumber(cancellationCount)}{" "}
                cancellation records. Cancellation records and anomaly records
                are different measures; an absence of anomaly rows does not
                mean there were no cancellations.
              </p>
            </div>
          )}
        </div>
      </section>

      <section className="panel" style={{ marginTop: 24 }}>
        <PanelHeader
          title="Analytics Coverage"
          subtitle="Current analytical outputs available to the control center"
        />

        <div className="table-wrap" style={{ marginTop: 16 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Analytics Area</th>
                <th>Records</th>
                <th>Purpose</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              <tr>
                <td>Delay prediction</td>
                <td>977 modeled flights</td>
                <td>Future delay risk</td>
                <td>
                  <span className="status-badge success">READY</span>
                </td>
              </tr>

              <tr>
                <td>Route profitability</td>
                <td>{formatNumber(routeCount)}</td>
                <td>Revenue / profitability analysis</td>
                <td>
                  <span className="status-badge success">READY</span>
                </td>
              </tr>

              <tr>
                <td>Demand forecast</td>
                <td>{formatNumber(forecastCount)}</td>
                <td>Forward demand planning</td>
                <td>
                  <span className="status-badge success">READY</span>
                </td>
              </tr>

              <tr>
                <td>Baggage</td>
                <td>{formatNumber(baggageCount)}</td>
                <td>Operational SLA monitoring</td>
                <td>
                  <span className="status-badge success">READY</span>
                </td>
              </tr>

              <tr>
                <td>Passenger experience</td>
                <td>{formatNumber(passengerCount)}</td>
                <td>Support / issue analysis</td>
                <td>
                  <span className="status-badge success">READY</span>
                </td>
              </tr>

              <tr>
                <td>Cancellation</td>
                <td>{formatNumber(cancellationCount)}</td>
                <td>Cancellation analysis</td>
                <td>
                  <span className="status-badge success">READY</span>
                </td>
              </tr>

              <tr>
                <td>Route demand</td>
                <td>{formatNumber(routeDemandCount)}</td>
                <td>Daily route demand</td>
                <td>
                  <span className="status-badge success">READY</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function EmptyAnalytics({ message }) {
  return (
    <div style={{ minHeight: 280, display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", opacity: 0.7, padding: 20, lineHeight: 1.6 }}>
      {message}
    </div>
  );
}

function StreamingPage({
  apiStatus,
}) {

  return (

    <div className="page">

      <section className="page-intro">

        <div>

          <div className="eyebrow">
            PLATFORM OBSERVABILITY
          </div>

          <h2>
            System Health
          </h2>

          <p>
            Monitor the operational
            components powering the
            TravelOps 360 platform.
          </p>

        </div>

      </section>


      <section className="health-grid">

        <HealthCard
          title="FastAPI"
          value={
            apiStatus ===
            "connected"
              ? "Operational"
              : "Offline"
          }
          status={
            apiStatus ===
            "connected"
          }
          description="Backend API"
        />


        <HealthCard
          title="Kafka"
          value="Configured"
          status
          description="Event streaming layer"
        />


        <HealthCard
          title="PySpark"
          value="Completed"
          status
          description="Transformation pipeline"
        />


        <HealthCard
          title="dbt"
          value="Validated"
          status
          description="Analytical modeling"
        />

      </section>


      <section className="streaming-evidence-grid">

        <div className="panel">

          <PanelHeader
            title="Kafka Processing Evidence"
            subtitle="Latest verified project processing run"
          />


          <div className="streaming-stat-grid">

            <StreamStat
              label="Events Processed"
              value="13,058"
            />

            <StreamStat
              label="Duplicates"
              value="130"
            />

            <StreamStat
              label="Processing Errors"
              value="0"
            />

            <StreamStat
              label="Event Topics"
              value="3"
            />

          </div>


          <div className="evidence-note">

            These values represent the
            verified streaming processing
            run completed during the
            project pipeline. They are
            presented as processing
            evidence rather than a claim
            of continuously live Kafka
            monitoring.

          </div>

        </div>


        <div className="panel">

          <PanelHeader
            title="Pipeline Components"
            subtitle="TravelOps 360 architecture"
          />


          <div className="pipeline-list">

            <PipelineItem
              number="01"
              title="Data Sources"
              description="Bookings, flights, baggage, airports and fares"
            />

            <PipelineItem
              number="02"
              title="Kafka Event Bus"
              description="Flight, baggage and booking events"
            />

            <PipelineItem
              number="03"
              title="Analytical Layer"
              description="PySpark + DuckDB + dbt"
            />

            <PipelineItem
              number="04"
              title="ML + Automation"
              description="Risk prediction and operational actions"
            />

            <PipelineItem
              number="05"
              title="FastAPI"
              description="Business intelligence API"
            />

          </div>

        </div>

      </section>

    </div>

  );

}


/* =========================================================
   HEALTH CARD
========================================================= */

function HealthCard({
  title,
  value,
  status,
  description,
}) {

  return (

    <div className="health-card">

      <div className="health-top">

        <span className="health-icon">
          ◉
        </span>

        <span
          className={`health-indicator ${
            status
              ? "online"
              : "offline"
          }`}
        ></span>

      </div>

      <strong>
        {title}
      </strong>

      <span className="health-value">
        {value}
      </span>

      <small>
        {description}
      </small>

    </div>

  );

}


/* =========================================================
   STREAM STAT
========================================================= */

function StreamStat({
  label,
  value,
}) {

  return (

    <div className="stream-stat">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>

  );

}


/* =========================================================
   PIPELINE ITEM
========================================================= */

function PipelineItem({
  number,
  title,
  description,
}) {

  return (

    <div className="pipeline-item">

      <div className="pipeline-number">
        {number}
      </div>

      <div>

        <strong>
          {title}
        </strong>

        <span>
          {description}
        </span>

      </div>

    </div>

  );

}


/* =========================================================
   HELPERS
========================================================= */

function getAction(item) {

  return (

    item?.automation_action ??
    item?.action ??
    item?.recommended_action ??
    "—"

  );

}


function getProbability(
  flight
) {

  const raw =
    flight.model_probability ??
    flight.probability ??
    flight.risk_probability ??
    flight.prediction_probability ??
    flight.delay_probability ??
    0;


  let value =
    Number(raw);


  if (Number.isNaN(value)) {

    return 0;

  }


  if (value <= 1) {

    value *= 100;

  }


  return Math.max(
    0,
    Math.min(100, value)
  );

}


function formatTimestamp(
  timestamp
) {

  if (!timestamp) {

    return "—";

  }


  const date =
    new Date(timestamp);


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {

    return String(timestamp);

  }


  return date.toLocaleString();

}


/* =========================================================
   EXPORT
========================================================= */

export default App;
