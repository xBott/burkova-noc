# Notes

## Assumptions

**Classifier (`classify.py`)**
- The label is what the caller ended up with. Rules are checked from the furthest step the call
  reached: transfer -> route -> ticket -> `get_outage` → address. An early hiccup, like an address
  retry, doesn't override a good outcome.
- Any status other than `ok` is a failure. `no_match` and `ambiguous` from the resolver mean
  `ADDRESS_NOT_UNDERSTOOD`. Any other error status from a tool, including ones we haven't seen,
  means `API_ERROR`. A transfer status other than `connected` means `TRANSFER_FAILED`.
- If the caller hung up while `get_outage` was running, the late result decides the label: `ok`
  gives `ENDED_EARLY`; a timeout or no answer gives `API_ERROR`. This follows the labeled notes.
- If the address resolved but `get_outage` never ran, a caller reply means they rejected the
  address (`ADDRESS_NOT_UNDERSTOOD`). No reply means they left first (`ENDED_EARLY`). This
  doesn't depend on `ended_by`, which may get new values.
- A known outage means `outage_id` is set, and the bot spoke after the result. We never match
  the bot's Slovak text, since the wording can change on another night.
- If the outage was unknown and no ticket was attempted, the label is `ENDED_EARLY`. This case
  doesn't occur in this night's data or the sample.
- Events are sorted by `t` and compared by time, not position. A tool result and the bot's reply
  share a timestamp.
- Unknown event types are ignored. A call without a hangup runs to its last event. Malformed lines
  are skipped with a warning on stderr.

**Report (`REPORT.md`)**
- "Failed" means `API_ERROR`, `ADDRESS_NOT_UNDERSTOOD` and `TRANSFER_FAILED`. `ENDED_EARLY`
  isn't counted, though 273 of those callers hung up while waiting for a slow OMS.
- Counts for the OMS window go by when the call started, so they're approximate.
- The capacity comparison assumes ~4 minutes per call for 3 operators and ignores repeated
  attempts on a busy line.
- The data is in UTC, and local time is Europe/Bratislava (UTC+1).

## What I deliberately didn't do

- **No LLM or trained model.** 60 labels is about 7 per class, too few to train on. The
  structured events (statuses, transfer, route, timing) explain all 60 labels with no overlaps.
  Rules are deterministic, explainable for each call, fast (~0.15 s for 11,400 calls), and run
  without an API key on the workshop's data.
- **No `asr_conf` threshold in the classifier.** Low confidence explains *why* addresses fail,
  but the label depends on the outcome. A threshold tuned on one night could break on the next.

## With more time

- Hand-label ~50 more calls, focused on cases the sample doesn't cover. Examples: an unknown
  outage where the caller hangs up before the ticket, a caller hanging up mid-address, and
  `create_ticket` never returning.
- Unit tests for each rule, plus the format-change test (new statuses, new event types,
  shuffled events) as a permanent test.
- Add a chart of failures per hour by cause against the OMS window to the report.
- Find out why 54 of 60 `create_ticket` timeouts fall in the OMS window when the tool is ours.
- Look at the 639 calls that hung up at the greeting (silence? "počujete ma"?). Also the 273 that
  hung up within ~2.5 s of waiting for OMS: a short "one moment, checking" might keep them.
- A prototype of an outcome dashboard built on `classify.py`.

## How I used AI tools

I used Claude Code (Claude desktop app) throughout.

- **Delegated:**
  - writing the EDA notebook and labeled sample analysis
  - small fixes to `classify.py`
  - `check_labels.py` for evaluation of classifier on labeled sample
  - computing the numbers for the report, and the first drafts of the text
- **Decided myself:**
  - rules instead of an LLM, after asking for the options and their trade-offs
  - the first draft of `classify.py`
  - adding the ASR analysis and the per-label analysis to the EDA
  - review of EDA notebook and `check_labels.py`
- **Where the agent was wrong:** in the draft of the report's "What next" section, the agent
  misread its own numbers in two places. Recomputing the figures against the data caught both.
  - It wrote that stale ETAs after midnight were "a median of 43 minutes late". The 43-minute
    median applies to all 377 stale ETAs over the whole night; after midnight it's the share
    (29%) that is higher.
  - It wrote that OMS errors caused "624 of the failures in 50 minutes". 624 is the night's total
    of OMS-related failures; 567 of them fell inside the 50-minute outage window.
