# Storm Night — report

Night of 15 Nov 2026, 11,400 calls. Numbers come from `predictions_night1.csv` (`classify.py`,
60/60 on the hand-labeled sample) and the EDA in `eda.ipynb`.

## 2. The numbers

**"38%" counts who pressed hang up, not how many calls failed.** `ended_by = bot` is 4,332 calls.
3,028 of them (70%) are the bot's normal goodbye after it told the caller the outage and the ETA.
The other 1,304 really are the bot giving up. So the client is right that it happens, but not about
the size: it was **about 1 caller in 9, not 4 in 10**.

**1,368 calls (12.0%) actually failed.** 9,120 (80%) got what they called for: 5,928 heard the
outage and ETA, 2,052 got a ticket, 798 reached dispatch, 342 were sent to the customer line.
912 (8%) hung up before the bot could help (639 at the greeting, 273 while the outage lookup was
still running); we don't count those as failures.

| Cause | Calls | During OMS outage* | Who fixes it |
|---|---:|---:|---|
| `get_outage` timed out, bot apologized and hung up | 560 | 512 | **Voltika** (OMS API); **product**: fallback |
| Caller hung up waiting for `get_outage`, which then failed | 64 | 55 | **Voltika**; **product**: fallback |
| `create_ticket` timed out | 60 | 54 | **us** (our tool) |
| Address not found after 3 tries | 396 | 48 | **us** (resolver) |
| Address resolved to the wrong place, caller rejected it | 60 | 10 | **us** (resolver); registry data may be Voltika's |
| Dispatch queue full (limit 10) | 160 | 22 | **Voltika** (queue, staffing); **product**: fallback |
| Transfer to dispatch timed out, nobody picked up | 68 | 11 | **Voltika** (staffing); **product**: fallback |
| **Total** | **1,368** | **712** | |

\* 20:40–21:30 UTC (21:40–22:30 local), when Voltika's OMS API ran at ~30% errors and hit the 8 s
timeout.

- **Half of all failures (712) fell in those 50 minutes.** 31.6% of calls failed then, compared
  with 7.2% the rest of the night. 91% of the API errors come from Voltika's OMS.
- **228 dangerous calls (wire down, sparks, fire) never reached a person.** This is the most
  serious item, whatever the cause.
- **The bot has no fallback (product).** Every one of the 912 tool and transfer failures ended
  the call. A fallback (create a ticket, mark danger calls urgent) would have saved most of them.
- **Address failures are ours and not caused by the storm.** The rate is flat all night. Lookups
  with ASR confidence below 0.7 almost never resolve, and house numbers with a slash ("5/a") fail
  33% of the time even with a clean transcript.
- **Also ours:**
  - Every ticket request (2,112) was sent with the bot's own prompt as the description, never the
    caller's words.
  - The dashboard shows who hung up instead of the outcome (product).
  - 54 of the 60 `create_ticket` timeouts also fell in the OMS window. That still needs a check:
    our tool may depend on Voltika's backend.
- **Failures inflate the volume.** 411 failed calls were followed by a callback from the same
  number, and 360 of those later calls succeeded.

## 3. Email to the client

**Predmet:** Re: Včerajšia noc

Dobrý deň, pani Hudecová,

ďakujem za správu a ospravedlňujem sa všetkým, ktorým bot v nedeľu nepomohol.

Čo ukazujú dáta z 11 400 hovorov:

- 38 % ukazuje, kto hovor ukončil, nie koľko hovorov zlyhalo. 70 % z nich je bežné rozlúčenie
  po tom, ako bot oznámil poruchu a odhad obnovy.
- Bot reálne nepomohol 1 368 volajúcim (12 %). 9 120 (80 %) dostalo informáciu o poruche,
  založené hlásenie alebo prepojenie na dispečing.
- Polovica zlyhaní prišla medzi 21:40 a 22:30, keď váš systém výpadkov vracal chyby. 456 zlyhaní
  je na našej strane: bot nerozpoznal adresu.
- Najvážnejšie: 228 volajúcich s nebezpečnou situáciou sa nedostalo k dispečerovi.

Chyba je aj u nás: keď niečo zlyhá, bot sa ospravedlní a hovor ukončí. Ako prvú opravu navrhujeme
náhradný postup: hlásenie sa uloží a nebezpečné prípady pôjdu dispečingu ako urgentné.

K vypnutiu: traja noční operátori zvládnu približne 45 hovorov za hodinu. V špičke ich prišlo 2 600.

K SMS: navrhujeme začať s číslom hlásenia. Odhad obnovy zatiaľ nie: 6 % odhadov z vášho systému
bolo v čase hovoru už v minulosti, po polnoci až 29 %. Chceme to vyriešiť s vaším IT.

Do stredy vám pošlem plán opráv s odhadom termínov. Môžeme si zajtra zavolať?

S pozdravom
Roman


## 4. What next

1. **First, a fallback when a tool or transfer fails (product).** Today all 912 of these calls end
   with an apology. If `get_outage` or `create_ticket` fails, the bot should save the report and
   tell the caller it's recorded. If dispatch is full, a danger call (228 last night) should become
   an urgent ticket with a callback. This is the biggest fix, and the only one that protects
   callers whatever breaks next.
2. **Then storm readiness with Voltika.** OMS errors caused 624 of the failures, 567 of them in
   those 50 minutes. Voltika needs to tell us how much load their API can take, and both sides
   need an alert when its error rate rises. The dispatch queue (limit 10, 228 failed transfers) needs a storm-night
   plan for staffing or a bigger queue.
3. **Then our own fixes on this account.**
   - Address resolution (456 failures): ask again differently when ASR confidence is low, for
     example town first, then street. Fix the parsing of house numbers with a slash ("5/a").
   - Put the caller's own words into ticket descriptions. Today all 2,112 contain the bot's prompt.
   - Show outcomes on the dashboard (from `classify.py`) instead of who hung up, so nobody reads
     "38%" as a failure rate again.
4. **SMS from next week: not with the ETA yet.** We can send the SMS. The problem is the content:
   377 of the 6,201 ETAs (6%) that Voltika's OMS returned were already in the past when the bot read
   them out, and 29% after midnight. Those ETAs were a median of 43 minutes in the past and up to
   2 hours. A wrong time is worse in writing than on the phone. Our proposal:
   - Next week, start with an SMS that carries the ticket or outage number. It doesn't depend on
     the ETA.
   - Add the ETA once Voltika keeps it up to date, and only send it when it's still in the future.
5. **Don't turn the bot off.** Three night operators at ~4 minutes a call handle ~45 calls an hour.
   - Peak volume was 2,600 an hour, 58× that. Even the quietest hour (1,200) was 27× that.
   - Over the 6 hours they could have taken ~270 of the 11,400 calls (2.4%).
   - The bot fully handled 9,120 calls, which is ~608 operator-hours of work. The 3 operators had
     18 hours between them.
   - Without the bot, nearly everyone who got an answer last night would have heard a busy line.
     The right move is to fix the 12% that failed, starting with point 1.
