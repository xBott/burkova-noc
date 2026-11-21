# Búrková noc

*Zadanie na workshop Born Digital @ Night of Chances IT 2026.*

Si **forward deployed engineer** na účte **Voltika**. Je **pondelok 16. novembra
2026, 8:15**. Včera v noci prišla búrka. Klient je nahnevaný a do stredy rozhodne,
či náš bot vypne.

**Time box: 2–3 hodiny.** Keď čas vyprší, prestaň, aj keď to nie je dokonalé.
Do NOTES.md napíš, čo by si robil ďalej. Zaujíma nás, čo si sa rozhodol robiť,
nie koľko toho stihneš.

**Používaj, čo bežne používaš: Claude Code, Codex, Cursor, čokoľvek.** Takto
pracujeme aj my.

**Uzávierka: pondelok 23. 11. 2026, 23:59.** Kto zadanie odovzdá, má miesto
na workshope. Potvrdenie pošleme v utorok 24. 11.

> Klient, ľudia aj dáta sú vymyslené. Situácia je modelovaná podľa toho, čo
> v produkcii naozaj zažívame.

---

## Klient

**Voltika** je regionálny distribútor elektriny so ~600 000 odbernými miestami.
Na poruchovej linke beží od septembra náš **AI voicebot**. V noci ho dopĺňajú
3 operátori dispečingu, cez deň 12.

## Ako bot funguje

```
volajúci ──► voicebot
               │ 1. „Povedzte mi adresu, kde vám nejde elektrina.“
               │ 2. resolve_address(text)  ──► register adries Voltiky
               │ 3. get_outage(address_id) ──► systém výpadkov Voltiky (OMS)
               │
               ├─ porucha je známa   → oznámi ju a povie odhad obnovy → rozlúči sa a zloží
               ├─ porucha nie je známa → create_ticket(...) → povie číslo hlásenia
               ├─ nebezpečná situácia (spadnutý drôt, iskrí…) → transfer na dispečing
               └─ niečo iné (faktúra, odpočet…) → odkáže na zákaznícku linku
```

- `resolve_address` a `create_ticket` prevádzkujeme my. Adresy hľadáme v registri,
  ktorý nám dodáva Voltika.
- `get_outage` je **systém Voltiky**. Voláme ho cez ich API.
- Prepojenie na dispečing ide do fronty Voltiky, ktorá má **limit 10 čakajúcich**.
- Keď bot nevie pokračovať, ospravedlní sa a hovor ukončí. **Fallback zatiaľ nemá.**

## Čo sa stalo

V nedeľu 15. 11. medzi 19:00 a 01:00 prišlo **11 400 hovorov**. Bežne ich je ~300
za deň. Špička mala ~2 600 hovorov za hodinu.

Dnes ráno prišiel tento mail:

> **Od:** Katarína Hudecová, vedúca zákazníckeho servisu, Voltika
> **Komu:** ty; kópia: váš account manager
> **Predmet:** Včerajšia noc
>
> Dobrý deň,
>
> podľa vášho dashboardu **ukončil bot 38 % hovorov**. Jednoducho im zložil.
> Ľudia nás za to roznášajú na Facebooku. Naše call centrum by sa k nim takto
> nesprávalo.
>
> Do stredy rozhodneme, či bota vypneme a linku vrátime call centru. Ak zostane,
> chceme, aby **od budúceho týždňa posielal odhad obnovy aj SMS-kou**.
>
> Do zajtra mi, prosím, pošlite, čo sa stalo.
>
> K. Hudecová

## Materiály

| Súbor | Čo to je |
|---|---|
| `data/calls.csv` | Jeden riadok = jeden hovor z nedeľnej noci (11 400). Z tohto súboru je dashboard. |
| `data/transcripts.jsonl` | Jeden riadok = jeden hovor: repliky, volania nástrojov a udalosti. |
| `data/labeled_sample.jsonl` | 60 hovorov z tej istej noci, ktoré ručne olabeloval náš kolega: `call_id`, `label`, pri sporných aj `note`, a `events` ako v `transcripts.jsonl`. Je to tvoja referencia. |
| `data/oms_api_metrics.txt` | Latencia a chybovosť API výpadkov Voltiky po 5 minútach. |

### `calls.csv`

| Stĺpec | Význam |
|---|---|
| `call_id` | napr. `c-n1-004211` |
| `started_at` | začiatok hovoru, ISO 8601, **UTC** (Voltika žije v Europe/Bratislava, UTC+1) |
| `duration_s` | dĺžka hovoru v sekundách |
| `ended_by` | kto hovor ukončil: `caller`, `bot`, `system`. **Zoznam nie je uzavretý.** |
| `caller_hash` | hash čísla volajúceho; ten istý človek môže volať viackrát |
| `flow_version` | verzia flowu bota, napr. `v14` |

### `transcripts.jsonl`

Každý riadok je jeden JSON objekt: `{"call_id": "...", "events": [...]}`.
`events` sú zoradené v čase. `t` je čas v sekundách od začiatku hovoru.

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

Typy udalostí:

| `type` | Polia |
|---|---|
| `bot`, `caller` | `text`; pri `caller` aj `asr_conf` (istota prepisu reči). Prepis je z ASR, teda bez interpunkcie a s chybami. |
| `tool_call` | `name`, `args` |
| `tool_result` | `name`, `status`, `latency_ms`, `result`. `status` je `ok` alebo chybový stav. **Zoznam chybových stavov nie je uzavretý.** |
| `transfer` | `target`, `status` (`connected` alebo dôvod, prečo nie) |
| `route` | `target`, napr. `customer_line`, keď bot volajúceho odkáže inam |
| `hangup` | `by` |

Nástroje: `resolve_address`, `get_outage`, `create_ticket`.

---

## Úlohy

### 1. Eval: čo sa v každom hovore naozaj stalo

Napíš nástroj, ktorý každý hovor z `transcripts.jsonl` zaradí do **práve jednej**
z týchto skupín:

| Label | Kedy |
|---|---|
| `KNOWN_OUTAGE_INFORMED` | Bot našiel adresu, porucha bola známa a bot volajúcemu povedal stav alebo odhad obnovy. |
| `TICKET_CREATED` | Porucha nebola známa a bot založil hlásenie. |
| `TRANSFERRED` | Bot prepojil na dispečing a dispečer hovor prijal. |
| `TRANSFER_FAILED` | Bot sa pokúsil prepojiť, ale prepojenie sa nepodarilo. |
| `API_ERROR` | Bot nemohol pomôcť, lebo zlyhal nástroj (`get_outage`, `create_ticket`). |
| `ADDRESS_NOT_UNDERSTOOD` | Bot nedokázal správne určiť adresu volajúceho. |
| `OUT_OF_SCOPE` | Volajúci chcel niečo iné a bot ho odkázal inam. |
| `ENDED_EARLY` | Hovor skončil skôr, než sa niečo z vyššie uvedeného stihlo stať, a nespôsobilo to zlyhanie nástroja ani prepojenia. |

**Rozhoduje výsledok pre volajúceho**, nie to, čo sa počas hovoru pokazilo
a potom napravilo. Ak sa hodí viac labelov, vyber ten, ktorý najlepšie popisuje,
s čím volajúci odišiel. Pri sporných prípadoch sa pozri do `labeled_sample.jsonl`.

**Výstup:** `predictions_night1.csv` s hlavičkou `call_id,label`, jeden riadok
na hovor, všetkých 11 400.

**Spustenie:** jeden príkaz, napr.
`python classify.py data/transcripts.jsonl > predictions.csv`.

> ⚠️ **Na workshope tvoj nástroj spustíme na dátach z ďalšej noci.** Formát bude
> rovnaký, ale ako v každej produkcii sa medzitým môže niečo zmeniť. Výsledok
> pôjde naživo na leaderboard. Pri návrhu nástroja na to mysli.

### 2. Čísla (max. ½ strany)

- Čo znamená „38 %“? Má klientka pravdu?
- Koľko hovorov reálne zlyhalo a prečo? Rozdeľ to podľa príčin.
- Kto vlastní ktorú opravu: my na tomto účte, náš produktový tím, alebo Voltika?

### 3. Odpoveď klientke (max. 200 slov)

Pripravená na odoslanie. Napíš ju tak, ako by si ju naozaj poslal.

### 4. Čo ďalej (3–5 odrážok)

- Čo navrhneš, aby sa to pri ďalšej búrke nezopakovalo, a v akom poradí?
- Ako odpovieš na **SMS od budúceho týždňa**?
- Má Voltika bota vypnúť? Argumentuj číslami. Pomôcka: koľko hovorov by za
  hodinu zvládli 3 noční operátori, ak jeden hovor trvá ~4 minúty?

### 5. `NOTES.md`

- Predpoklady, ktoré si urobil.
- Čo by si robil, keby si mal viac času.
- **Ako si použil AI nástroje:** čo si delegoval, čo si si overil sám a jedno
  miesto, kde sa agent mýlil.

## Odovzdanie

Link na Git repozitár (verejný alebo s prístupom pre nás) alebo zip.
**[formulár: doplniť]**

Repo má obsahovať:
- kód a príkaz, ktorým sa spúšťa,
- `predictions_night1.csv`,
- body 2–4 (stačí jeden markdown),
- `NOTES.md`.

## Ako hodnotíme

Hodnotenie zadania sa spolu s workshopom ráta do výberu top 3:

- Presnosť evalu na nedeľnej noci (máme kompletné labely).
- Či čísla a vysvetlenie sedia a či si oddelil, kto čo vlastní.
- Mail: jasný, s číslami, úprimný, bez sľubov, ktoré nevieme dodržať.
- Úsudok: čo si vedome nerobil a prečo.

**Na workshope ťa čaká** druhá noc dát, ďalšia úloha a klient, ktorý zavolá. Až traja najlepší dostanú pozvánku na pohovor s CEO Born Digital. Termín dohodneme po podujatí.

Otázky: **[e-mail: doplniť]**
