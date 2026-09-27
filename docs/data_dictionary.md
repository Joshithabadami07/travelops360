# TravelOps 360 — Data Dictionary (Bronze Layer)

## airports.csv
| Field | Type | Description |
|---|---|---|
| airport_id | string (PK) | IATA-style 3-letter code |
| city | string | City served |
| region | string | North / South / East / West |
| capacity | int | Approx. daily passenger handling capacity |

## aircraft.csv
| Field | Type | Description |
|---|---|---|
| aircraft_id | string (PK) | Internal tail/fleet id |
| type | string | Aircraft type (A320, B737, ...) |
| seat_capacity | int | Total seats |

## routes.csv
| Field | Type | Description |
|---|---|---|
| route_id | string (PK) | Route identifier |
| origin_airport_id | string (FK -> airports) | Departure airport |
| dest_airport_id | string (FK -> airports) | Arrival airport |
| popularity | float | Synthetic demand-weight driving load factor & fares |

## customers.csv
| Field | Type | Description |
|---|---|---|
| customer_id | string (PK) | Customer identifier |
| name | string | Synthetic name |
| tier | string | Standard / Silver / Gold / Platinum |
| home_region | string | Region of residence |

## dim_date.csv
| Field | Type | Description |
|---|---|---|
| date_id | string (PK) | YYYY-MM-DD |
| date | date | Calendar date |
| year / month / day | int | Date parts |
| day_of_week | string | Day name |
| is_weekend | bool | Sat/Sun flag |

## flights.csv
| Field | Type | Description |
|---|---|---|
| flight_id | string (PK) | Flight identifier |
| route_id | string (FK -> routes) | Route flown |
| aircraft_id | string (FK -> aircraft) | Aircraft operating |
| scheduled_departure | datetime | Planned departure |
| actual_departure | datetime, nullable | Actual departure (null if cancelled/not yet departed) |
| status | string | SCHEDULED / BOARDING / DEPARTED / COMPLETED / CANCELLED |
| delay_minutes | float, nullable | Departure delay in minutes |

## fares.csv
| Field | Type | Description |
|---|---|---|
| route_id | string (FK -> routes) | Route |
| cabin | string | Economy / PremiumEconomy / Business |
| timestamp | datetime | Fare snapshot time (days-to-departure curve) |
| price | float | Fare in INR |

## bookings.csv
| Field | Type | Description |
|---|---|---|
| booking_id | string (PK) | Booking identifier |
| customer_id | string (FK -> customers) | Passenger |
| flight_id | string (FK -> flights) | Flight booked |
| fare | float | Fare paid |
| booking_time | datetime | Time of booking |
| status | string | CONFIRMED / CHECKED_IN / COMPLETED / REFUNDED / REBOOKED |

## baggage.csv
| Field | Type | Description |
|---|---|---|
| bag_id | string (PK) | Bag tag id |
| booking_id | string (FK -> bookings) | Associated booking |
| scan_time | datetime | Last scan event time |
| airport | string (FK -> airports) | Scan location |
| status | string | LOADED / IN_TRANSIT / DELIVERED / DELAYED |

## support_tickets.csv
| Field | Type | Description |
|---|---|---|
| ticket_id | string (PK) | Ticket id |
| booking_id | string (FK -> bookings) | Related booking |
| issue_type | string | DELAY_COMPLAINT / BAGGAGE_ISSUE / CANCELLATION / REFUND_REQUEST / SERVICE_QUALITY |
| created_at | datetime | Ticket creation time |

## Injected scenarios (for downstream ML/automation demo)
- **Demand surge window**: 2026-08-27 → 2026-09-02 (elevated load factors, feeds the "demand surge → revenue-management alert" rule)
- **Cancellation cluster day**: 2026-09-11 (elevated cancel rate + delay spike at hub airports, feeds "cancellation cluster → incident workflow" and "delay risk → operations escalation")
- **Baggage SLA breach probability** rises with flight delay minutes, feeding "baggage SLA breach → baggage-team alert"
