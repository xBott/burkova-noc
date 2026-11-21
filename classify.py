"""Label each voicebot call by what the caller ended up with.

Usage: python classify.py data/transcripts.jsonl > predictions_night1.csv
Reads JSON lines with "call_id" and "events" from the file, or from stdin when no file is given.
"""

import csv
import json
import sys
from collections.abc import Iterable, Iterator
from enum import Enum

OK = "ok"
CONNECTED = "connected"
ADDRESS_NOT_FOUND = {"no_match", "ambiguous"}

class EventType(Enum):
    BOT = 0
    CALLER = 1
    TOOL_CALL = 2
    TOOL_RESULT = 3
    HANGUP = 4
    TRANSFER = 5
    ROUTE = 6

    @property
    def id(self) -> str:
        return _EVENT_TYPE_IDS.get(self)

_EVENT_TYPE_IDS = { event_type: event_type.name.lower() for event_type in EventType }

class Prediction(Enum):
    KNOWN_OUTAGE_INFORMED = 0
    TICKET_CREATED = 1
    TRANSFERRED = 2
    TRANSFER_FAILED = 3
    API_ERROR = 4
    ADDRESS_NOT_UNDERSTOOD = 5
    OUT_OF_SCOPE = 6
    ENDED_EARLY = 7

def of_type(events: list[dict], event_type: EventType) -> list[dict]:
    """Filters events by type"""
    return [event for event in events if event.get("type") == event_type.id]


def was_tool_called(events: list[dict], tool_name: str) -> bool:
    """Checks whether the specified tool was called during the call"""
    return any(
        event.get("type") == EventType.TOOL_CALL.id and event.get("name") == tool_name
        for event in events
    )


def last_tool_result(events: list[dict], tool_name: str) -> dict | None:
    """Returns last tool result for a specified tool"""
    results = [
        event
        for event in events
        if event.get("type") == EventType.TOOL_RESULT.id and event.get("name") == tool_name
    ]
    return results[-1] if results else None


def has_event_between(events: list[dict], event_type: EventType, start: float, end: float) -> bool:
    """Checks whether the call contains events of specified type between two timestamps"""
    return any(
        event.get("type") == event_type.id and start <= event.get("t", 0) <= end
        for event in events
    )


def outage_label(events: list[dict], hangup_at: float) -> Prediction:
    """Predict outage"""

    result = last_tool_result(events, "get_outage")
    if result is None or result.get("status") != OK:
        return Prediction.API_ERROR
    
    result_time = result.get("t", 0)
    if result_time > hangup_at:
        return Prediction.ENDED_EARLY

    outage = result.get("result") or {}
    is_known = outage.get("outage_id") is not None
    if is_known and has_event_between(events, EventType.BOT, result_time, hangup_at):
        return Prediction.KNOWN_OUTAGE_INFORMED

    return Prediction.ENDED_EARLY


def address_label(events: list[dict], hangup_at: float) -> Prediction:
    """Predict address"""

    result = last_tool_result(events, "resolve_address")
    if result is None:
        return Prediction.API_ERROR

    status = result.get("status")
    if status in ADDRESS_NOT_FOUND:
        return Prediction.ADDRESS_NOT_UNDERSTOOD
    
    if status != OK:
        return Prediction.API_ERROR

    result_time = result.get("t", 0)
    has_replied = has_event_between(events, EventType.CALLER, result_time, hangup_at)
    return Prediction.ADDRESS_NOT_UNDERSTOOD if has_replied else Prediction.ENDED_EARLY


def classify(events: list[dict]) -> Prediction:
    """Classifes the call using events happed during it"""

    events = sorted(events, key=lambda e: e.get("t", 0))
    hangups = of_type(events, EventType.HANGUP)
    hangup_at = hangups[0].get("t", 0) if hangups else float("inf")

    transfers = of_type(events, EventType.TRANSFER)
    if transfers:
        last_transfer_event = transfers[-1]
        last_transfer_event_status = last_transfer_event.get("status")
        return (
            Prediction.TRANSFERRED
            if last_transfer_event_status == CONNECTED
            else Prediction.TRANSFER_FAILED
        )

    if of_type(events, EventType.ROUTE):
        return Prediction.OUT_OF_SCOPE

    if was_tool_called(events, "create_ticket"):
        ticket = last_tool_result(events, "create_ticket")
        is_created = ticket is not None and ticket.get("status") == OK
        return Prediction.TICKET_CREATED if is_created else Prediction.API_ERROR

    if was_tool_called(events, "get_outage"):
        return outage_label(events, hangup_at)

    if was_tool_called(events, "resolve_address"):
        return address_label(events, hangup_at)

    return Prediction.ENDED_EARLY


def read_calls(lines: Iterable[str]) -> Iterator[tuple[str, list[dict]]]:
    """An iterator across call json that returns call id and events happened during it"""

    for line_number, line in enumerate(lines, start=1):

        if not line.strip():
            continue

        try:
            call = json.loads(line)

        except json.JSONDecodeError:
            print(f"skipping line {line_number}: not valid JSON", file=sys.stderr)
            continue

        if "call_id" not in call:
            print(f"skipping line {line_number}: no call_id", file=sys.stderr)
            continue

        yield call["call_id"], call.get("events") or []


def write_predictions(lines: Iterable[str]) -> None:
    """Reads jsonl file, makes prediction and writes it in format 'call_id,prediction' to stdout"""

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["call_id", "label"])

    for call_id, events in read_calls(lines):
        prediction = classify(events)
        writer.writerow([call_id, prediction.name])


def main() -> None:
    """Entry point"""

    if len(sys.argv) > 2:
        sys.exit("usage: python classify.py [transcripts.jsonl]")

    if len(sys.argv) == 2:
        with open(sys.argv[1], encoding="utf-8") as file:
            write_predictions(file)

    else:
        write_predictions(sys.stdin)


if __name__ == "__main__":
    main()
