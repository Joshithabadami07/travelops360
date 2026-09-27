#!/usr/bin/env bash
# Creates the TravelOps 360 Kafka topics. Run after `docker compose up -d`.
set -e
BROKER="localhost:9092"

create() {
  docker exec travelops-kafka kafka-topics --bootstrap-server "$BROKER" \
    --create --if-not-exists --topic "$1" --partitions "$2" --replication-factor 1 \
    --config retention.ms=604800000
}

create flights.status      3   # keyed by flight_id
create baggage.scans       3   # keyed by bag_id
create bookings.events     3   # keyed by booking_id
create events.deadletter   1   # failed/poison messages land here for manual review

echo "Topics created:"
docker exec travelops-kafka kafka-topics --bootstrap-server "$BROKER" --list
