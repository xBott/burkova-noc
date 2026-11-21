"""Compare classify.py against the hand-labeled sample and list every disagreement.

Usage: python check_labels.py [data/labeled_sample.jsonl]
"""

import json
import sys
from collections import Counter

from classify import classify

DEFAULT_SAMPLE = "data/labeled_sample.jsonl"


def main() -> None:
    """Entry point"""

    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SAMPLE
    with open(path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    totals = Counter()
    correct = Counter()
    misses = []

    for record in records:

        expected = record["label"]
        predicted = classify(record["events"]).name
        totals[expected] += 1

        if predicted == expected:
            correct[expected] += 1

        else:
            misses.append((record["call_id"], expected, predicted, record.get("note", "")))

    n_correct = sum(correct.values())
    
    print(f"accuracy: {n_correct}/{len(records)} ({n_correct / len(records):.1%})")
    for label in sorted(totals):
        print(f"  {label:24s} {correct[label]}/{totals[label]}")

    if misses:
        print("\ndisagreements (call_id, expected, predicted, note):")
        for call_id, expected, predicted, note in misses:
            print(f"  {call_id}  {expected} -> {predicted}  {note}")
        sys.exit(1)


if __name__ == "__main__":
    main()
