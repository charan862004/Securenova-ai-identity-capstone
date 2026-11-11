
import json
import sys
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path


# ==================================================
# SecureNova - AI Identity Anomaly Detection
# ==================================================

CALL_LIMIT = 20
TIME_WINDOW_SECONDS = 60


def parse_timestamp(value):
    """Convert ISO timestamp or Unix timestamp to seconds."""
    if isinstance(value, (int, float)):
        return float(value)

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).timestamp()


def load_events(file_path):
    """Read events from a JSON Lines file."""
    events = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                event = json.loads(line)
                event["_line"] = line_number
                event["_timestamp"] = parse_timestamp(
                    event["timestamp"]
                )
                events.append(event)

            except (json.JSONDecodeError, KeyError, ValueError) as error:
                print(f"Skipping invalid event on line {line_number}: {error}")

    return sorted(events, key=lambda event: event["_timestamp"])


def detect_high_request_volume(events):
    """Alert when an agent makes more than 20 calls in 60 seconds."""
    alerts = []
    agent_events = defaultdict(deque)

    for event in events:
        agent_id = event.get("agent_id", "unknown")
        current_time = event["_timestamp"]

        requests = agent_events[agent_id]
        requests.append(current_time)

        while requests and current_time - requests[0] > TIME_WINDOW_SECONDS:
            requests.popleft()

        if len(requests) > CALL_LIMIT:
            alerts.append(
                f"[ALERT 1 - HIGH REQUEST VOLUME] "
                f"Agent {agent_id} made {len(requests)} calls "
                f"within 60 seconds."
            )

    return alerts


def detect_scope_changes(events):
    """Alert when an agent's scope changes between consecutive requests."""
    alerts = []
    previous_scope = {}

    for event in events:
        agent_id = event.get("agent_id", "unknown")
        current_scope = event.get("scope", "")

        if agent_id in previous_scope:
            if previous_scope[agent_id] != current_scope:
                alerts.append(
                    f"[ALERT 2 - SCOPE CHANGE] "
                    f"Agent {agent_id}: scope changed from "
                    f"'{previous_scope[agent_id]}' to "
                    f"'{current_scope}'."
                )

        previous_scope[agent_id] = current_scope

    return alerts


def detect_expired_token_reuse(events):
    """Alert when a token is used at or after its expiry time."""
    alerts = []
    seen_tokens = set()

    for event in events:
        token_id = event.get("token_id") or event.get("token")
        token_exp = event.get("token_exp")

        if not token_id or token_exp is None:
            continue

        try:
            expiry_time = parse_timestamp(token_exp)
            request_time = event["_timestamp"]

            if token_id in seen_tokens and request_time >= expiry_time:
                alerts.append(
                    f"[ALERT 3 - EXPIRED TOKEN REUSE] "
                    f"Agent {event.get('agent_id', 'unknown')} "
                    f"reused token {token_id} after expiry."
                )

            seen_tokens.add(token_id)

        except (ValueError, TypeError):
            print(f"Invalid token expiry value: {token_exp}")

    return alerts


def main():
    if len(sys.argv) < 2:
        print("Usage: python anomaly_detection.py <events.jsonl>")
        print("Example: python anomaly_detection.py anomaly_events.jsonl")
        return

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Event file not found: {file_path}")
        return

    events = load_events(file_path)

    print("\n==========================================")
    print(" SECURENOVA ANOMALY DETECTION")
    print("==========================================")
    print(f"Events analysed: {len(events)}")

    alerts = []
    alerts.extend(detect_high_request_volume(events))
    alerts.extend(detect_scope_changes(events))
    alerts.extend(detect_expired_token_reuse(events))

    print("\nDetection Results")
    print("------------------------------------------")

    if alerts:
        for alert in alerts:
            print(alert)
    else:
        print("No anomalies detected.")

    print("------------------------------------------")
    print(f"Total alerts: {len(alerts)}")
    print("==========================================")


if __name__ == "__main__":
    main()
