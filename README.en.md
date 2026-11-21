# Storm Night

*Assignment for the Born Digital workshop @ Night of Chances IT 2026.*

You're a **forward deployed engineer** on the **Voltika** account. It's **Monday, November 16, 2026, 8:15 AM**. A storm hit last night. The client is angry and will decide by Wednesday whether to shut down our bot.

**Time box: 2–3 hours.** When time runs out, stop, even if it isn't perfect.
In NOTES.md, write what you would do next. We care about what you decided to do,
not how much you managed to get done.

**Use whatever you normally use: Claude Code, Codex, Cursor, anything.** That's
how we work too.

**Deadline: Monday 23 Nov 2026, 23:59.** Everyone who submits the assignment gets
a spot at the workshop. We'll send confirmations on Tuesday 24 Nov.

> The client, people and data are fictional. The situation is modeled on what we
> actually experience in production.

---

## The client

**Voltika** is a regional electricity distributor with ~600,000 supply points.
Since September, our **AI voicebot** has been running on their outage hotline.
It's backed up by 3 dispatch operators at night and 12 during the day.

## How the bot works

```
caller ──► voicebot
             │ 1. "Please tell me the address where your power is out."
             │ 2. resolve_address(text)  ──► Voltika address registry
             │ 3. get_outage(address_id) ──► Voltika outage management system (OMS)
             │
             ├─ outage is known     → announces it and gives a restoration estimate → says goodbye and hangs up
             ├─ outage is not known → create_ticket(...) → gives the report number
             ├─ dangerous situation (downed wire, sparking…) → transfer to dispatch
             └─ something else (bill, meter reading…) → refers caller to the customer line
```

- We run `resolve_address` and `create_ticket`. We look up addresses in a registry
  that Voltika supplies to us.
- `get_outage` is **Voltika's system**. We call it through their API.
- Transfers to dispatch go into a Voltika queue that has a **limit of 10 waiting callers**.
- When the bot can't continue, it apologizes and ends the call. **It has no fallback yet.**

## What happened

On Sunday 15 Nov, between 19:00 and 01:00, **11,400 calls** came in. Normally
there are ~300 per day. The peak was ~2,600 calls per hour.

This email arrived this morning:

> **From:** Katarína Hudecová, Head of Customer Service, Voltika
> **To:** you; cc: your account manager
> **Subject:** Last night
>
> Hello,
>
> according to your dashboard, **the bot ended 38% of calls**. It just hung up on them.
> People are tearing us apart on Facebook. Our call center would never treat
> them like that.
>
> By Wednesday we'll decide whether to turn the bot off and hand the line back to
> the call center. If it stays, we want it to **also send the restoration estimate
> by SMS starting next week**.
>
> Please send me what happened by tomorrow.
>
> K. Hudecová

## Materials

| File | What it is |
|---|---|
| `data/calls.csv` | One row = one call from Sunday night (11,400). The dashboard is built from this file. |
| `data/transcripts.jsonl` | One row = one call: utterances, tool calls and events. |
| `data/labeled_sample.jsonl` | 60 calls from the same night, hand-labeled by our colleague: `call_id`, `label`, a `note` for disputed ones, and `events` as in `transcripts.jsonl`. This is your reference. |
| `data/oms_api_metrics.txt` | Latency and error rate of Voltika's outage API in 5-minute buckets. |

### `calls.csv`

| Column | Meaning |
|---|---|
| `call_id` | e.g. `c-n1-004211` |
| `started_at` | call start, ISO 8601, **UTC** (Voltika is in Europe/Bratislava, UTC+1) |
| `duration_s` | call length in seconds |
| `ended_by` | who ended the call: `caller`, `bot`, `system`. **The list is not closed.** |
| `caller_hash` | hash of the caller's number; the same person may call multiple times |
| `flow_version` | bot flow version, e.g. `v14` |

### `transcripts.jsonl`

Each line is one JSON object: `{"call_id": "...", "events": [...]}`.
`events` are sorted by time. `t` is time in seconds from the start of the call.

```json
{"t": 0.0, "type": "bot",    "text": "Dobrý večer, poruchová linka Voltika. Povedzte mi, prosím, adresu, kde vám nejde elektrina."}
{"t": 6.2, "type": "caller", "text": "no hlavná dvanásť pezinok", "asr_conf": 0.91}
{"t": 6.9, "type": "tool_call",   "name": "resolve_address", "args": {"text": "no hlavná dvanásť pezinok"}}
{"t": 7.3, "type": "tool_result", "name": "resolve_address", "status": "ok", "latency_ms": 380, "result": {"address_id": "A-000088"}}
{"t": 7.3, "type": "bot",    "text": "Overím si: Hlavná 12, Pezinok. Je to správne?"}
{"t": 11.2, "type": "caller", "text": "áno", "asr_conf": 0.93}
{"t": 11.6, "type": "tool_call",   "name": "get_outage", "args": {"address_id": "A-000088"}}
{"t": 13.3, "type": "tool_result", "name": "get_outage", "status": "ok", "latency_ms": 1700, "result": {"outage_id": "O-5512", "eta": "2026-11-16T02:00:00+01:00"}}
{"t": 13.3, "type": "bot",    "text": "Na vašej adrese evidujeme poruchu. Elektrinu by ste mali mať späť okolo druhej hodiny v noci."}
{"t": 19.0, "type": "caller", "text": "dobre ďakujem", "asr_conf": 0.9}
{"t": 19.6, "type": "bot",    "text": "Ďakujem za zavolanie, dovidenia."}
{"t": 20.1, "type": "hangup", "by": "bot"}
```

*(The example transcript stays in Slovak because the data is Slovak. Roughly:
"Good evening, Voltika outage line. Please tell me the address where your power
is out." → "uh hlavná twelve pezinok" → "Let me confirm: Hlavná 12, Pezinok. Is
that correct?" → "yes" → "We have an outage recorded at your address. You should
have power back around two in the morning." → "ok thanks" → "Thank you for
calling, goodbye.")*

Event types:

| `type` | Fields |
|---|---|
| `bot`, `caller` | `text`; for `caller` also `asr_conf` (speech transcription confidence). Transcripts come from ASR, so they have no punctuation and contain errors. |
| `tool_call` | `name`, `args` |
| `tool_result` | `name`, `status`, `latency_ms`, `result`. `status` is `ok` or an error status. **The list of error statuses is not closed.** |
| `transfer` | `target`, `status` (`connected` or the reason it failed) |
| `route` | `target`, e.g. `customer_line`, when the bot refers the caller elsewhere |
| `hangup` | `by` |

Tools: `resolve_address`, `get_outage`, `create_ticket`.

---

## Tasks

### 1. Eval: what actually happened in each call

Write a tool that assigns each call in `transcripts.jsonl` to **exactly one**
of these groups:

| Label | When |
|---|---|
| `KNOWN_OUTAGE_INFORMED` | The bot found the address, the outage was known, and the bot told the caller the status or restoration estimate. |
| `TICKET_CREATED` | The outage was not known and the bot created a report. |
| `TRANSFERRED` | The bot transferred to dispatch and a dispatcher picked up. |
| `TRANSFER_FAILED` | The bot tried to transfer, but the transfer failed. |
| `API_ERROR` | The bot couldn't help because a tool failed (`get_outage`, `create_ticket`). |
| `ADDRESS_NOT_UNDERSTOOD` | The bot couldn't correctly identify the caller's address. |
| `OUT_OF_SCOPE` | The caller wanted something else and the bot referred them elsewhere. |
| `ENDED_EARLY` | The call ended before any of the above could happen, and it wasn't caused by a tool or transfer failure. |

**What counts is the outcome for the caller**, not what broke during the call
and was then fixed. If several labels fit, pick the one that best describes
what the caller left with. For disputed cases, look at `labeled_sample.jsonl`.

**Output:** `predictions_night1.csv` with the header `call_id,label`, one row
per call, all 11,400.

**Running it:** one command, e.g.
`python classify.py data/transcripts.jsonl > predictions.csv`.

> ⚠️ **At the workshop we'll run your tool on data from another night.** The
> format will be the same, but as in any production system, something may
> change in the meantime. The result goes live on a leaderboard. Keep this in
> mind when designing your tool.

### 2. The numbers (max. ½ page)

- What does "38%" mean? Is the client right?
- How many calls actually failed, and why? Break it down by cause.
- Who owns which fix: us on this account, our product team, or Voltika?

### 3. Reply to the client (max. 200 words)

Ready to send. Write it the way you'd actually send it.

### 4. What next (3–5 bullet points)

- What would you propose so this doesn't happen in the next storm, and in what order?
- How will you respond to the **SMS starting next week** request?
- Should Voltika turn the bot off? Argue with numbers. Hint: how many calls per
  hour could 3 night operators handle if one call takes ~4 minutes?

### 5. `NOTES.md`

- The assumptions you made.
- What you'd do with more time.
- **How you used AI tools:** what you delegated, what you verified yourself,
  and one place where the agent got it wrong.

## Submission

A link to a Git repository (public or with access for us) or a zip.
**[form: TBD]**

The repo should contain:
- the code and the command to run it,
- `predictions_night1.csv`,
- tasks 2–4 (a single markdown file is enough),
- `NOTES.md`.

## How we evaluate

The assignment score, together with the workshop, counts toward selecting the top 3:

- Eval accuracy on Sunday night (we have complete labels).
- Whether the numbers and explanation hold up, and whether you separated who owns what.
- The email: clear, with numbers, honest, no promises we can't keep.
- Judgment: what you consciously chose not to do, and why.

**At the workshop** you'll get a second night of data, another task, and a client
who will call you. Up to three of the best will be invited to an interview with
the CEO of Born Digital. We'll arrange the date after the event.

Questions: **[e-mail: TBD]**
