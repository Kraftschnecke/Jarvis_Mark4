# J.A.R.V.I.S. -- Project Status (Mark 5)

_Started: 2026-10-22. Baseline: Mark 4 (tag `mark4`, this repository)._

Everything in `PROJEKT_STATUS_MARK4.md` (architecture, rules, risk levels, guest mode, widgets) still
applies unless this file says otherwise.

## Project Goal (long term)

Personal AI assistant inspired by J.A.R.V.I.S.: modular, with its own memory, project management, tools,
voice and several access points -- and built so that its owner understands every part of it.

---

# Mark 5 -- Goals

Mark 4 made Jarvis fast, safe and able to plan. Mark 5 makes him **useful in daily life and reachable
from anywhere**:

1. **Many more abilities.** Weather, news, files, real calendar, reminders, briefings, and more
   (Phases 1 and 2).
2. **A way to reach Jarvis outside the local browser tab** -- one of two paths, decided in Phase 3:
   - **Path A: go online.** Login, HTTPS, own data per user, deployment.
   - **Path B: a "really cool app".** Same functions as the web interface, but nicer and closer to the system.
   The two are not enemies: both need the same cleaned-up server interface. Path B can also be
   combined with A later.

Order matters: **abilities first.** They are needed for every path, and an app or website with
nothing new inside is just a new coat of paint.

Not goals of Mark 5 (see "Deferred"): computer control beyond the allow-list, camera/screen perception,
smart-home hardware, self-modification.

## Development rules (unchanged)

> **Only work on one unchecked point at a time.**
> After each point: implement -> test -> check off -> commit.

- Every step ends with a green `py run_tests.py` and one commit.
- Every step has a "Done when" line. If it is not true, the step is not finished.
- Tests never use the real database, the AI API, the internet or start programs.
- **New rule for abilities:** every new ability gets (1) a risk level in `risk.py`, (2) an entry in the
  capability list, (3) a test with a fake service, (4) a line in the acceptance test. Without all four it is not done.
- **Secrets** (API keys, tokens) only in `.env`. Anything an ability fetches from outside is **untrusted data**
  (wrapped like web search results) and can never trigger an action.
- Prefer services **without an API key and without cost** (Open-Meteo, RSS). Anything with a bill gets an
  on/off switch in Settings, default off.
- The roadmap checkboxes are ticked by the owner.

---

# Mark 5 -- One-Step-at-a-Time Roadmap

## Phase 0 -- Start

### Step 0.1
- [ ] Version string "Mark 5", this document in place, README line updated.
  - Done when: Settings -> About shows "Mark 5", tests green, one commit on `main` (same repository, baseline is tag `mark4`).

## Phase 1 -- The ability platform (so that adding an ability is routine)

Until now every ability was added by hand in several files. Before adding twenty more, make it one pattern.

### Step 1.1
- [ ] Write down "How to add an ability" in `DESIGN_ABILITIES.md`: where the task is declared, where the executor
      lives, how the risk level is set, how the capability list learns about it, how the test looks, which settings it may have.
  - Done when: the checklist exists and was followed once on a trivial new ability (see 2.1).

### Step 1.2
- [ ] A small shared helper for **outside services**: one place for timeouts, host allow-list, size limit,
      error messages and "untrusted" wrapping (today `widgets.fetch_text` and web search each do their own).
  - Done when: weather, news and the hockey widget use the same helper; one test covers timeout, wrong host, too-large answer.

### Step 1.3
- [ ] **Per-ability switches** in Settings (Abilities page): each ability can be turned off; abilities with cost or
      privacy impact start off.
  - Done when: a turned-off ability is not offered to the router, not listed under "What can you do?", and a direct attempt is refused.

### Step 1.4
- [ ] Cost guard: a daily limit for paid calls (voice output, AI), visible in Settings, Jarvis says so when it is reached.
  - Done when: with a limit of 1 call the second call is refused with a clear message (test with fake counter).

## Phase 2 -- Abilities, in batches (one ability = one step)

Risk levels: **safe** = runs at once, **confirm** = asks "yes/no" first. Within a batch the order is a suggestion;
the owner can reorder or cancel items.

### Batch A -- Information (read-only, safe)
- [ ] 2.1 **Weather** now and forecast for a place (Open-Meteo, no key). Also a weather line in the startup status report.
- [ ] 2.2 **News** headlines from a few chosen RSS feeds (list editable in Settings), summary on request.
- [ ] 2.3 **Calculator and conversions** (units, currencies with daily rates, percentages) -- exact math in code, not by the AI.
- [ ] 2.4 **Time zones / world clock** ("Wie spät ist es in Edmonton?").
- [ ] 2.5 **Wikipedia lookup** ("Wer war ...", with source).
- [ ] 2.6 **Read a web page and summarize it** (a link in the chat; content is untrusted).
- [ ] 2.7 **Translate** (AI) with the target language chosen by voice or text.
- [ ] 2.8 **System info**: battery, disk, memory, network, what is running ("Wie voll ist die Festplatte?").
  - Done when (each): the owner asks for it in German and English, the answer is right, an error case (no internet, wrong place) gives a clear sentence, the ability is in `Was kannst du?`.

### Batch B -- Time and reminders (builds on timers and calendar)
- [ ] 2.9 **Reminders at a clock time** ("Erinnere mich um 18 Uhr an ...") that survive a restart.
- [ ] 2.10 **Repeating calendar entries** (weekly, monthly, birthdays) and repeating reminders.
- [ ] 2.11 **Alarm clock / wake-up routine** (time + a short spoken briefing).
- [ ] 2.12 **Daily briefing** on request and optionally at the first start of the day: date, weather, calendar, goals, news, open timers.
- [ ] 2.13 **Pomodoro / focus timer** with break reminders.
  - Done when (each): restart the server and the entry is still there; it fires once at the right time.

### Batch C -- Files and documents (confirm, folder allow-list)
- [ ] 2.14 **Folder allow-list** in Settings (like `programs.json`): Jarvis may only read inside these folders.
- [ ] 2.15 **Find files** by name or content in those folders.
- [ ] 2.16 **Read and summarize** `.txt`, `.md`, `.pdf`, `.docx` (content is untrusted).
- [ ] 2.17 **Answer questions about a document** ("Was steht im Vertrag zu Kündigung?").
- [ ] 2.18 **Write notes to a file** in an allowed folder (always confirm, never overwrite without asking).
  - Done when: a file outside the allow-list is refused without a question; `..\` and shortcuts do not escape the folder; a prompt injected in a document opens nothing.

### Batch D -- Accounts (OAuth; read is safe-ish, write is confirm)
- [ ] 2.19 **Real calendar** (Google Calendar): show today/tomorrow, add an entry (confirm). Replaces the local calendar only if the owner wants.
- [ ] 2.20 **E-mail**: read the subject lines of new mails (read-only first); drafts only, **never send without confirm** (and likely never in Mark 5).
- [ ] 2.21 **Music**: play / pause / next / "Spiel etwas von ..." (Spotify or system media keys).
- [ ] 2.22 **Contacts / birthdays** from the calendar account.
  - Done when: token stored outside Git, can be revoked in Settings, scope as small as possible, Jarvis never shows the token.

### Batch E -- On the computer (confirm, allow-list)
- [ ] 2.23 **Media keys and window basics**: play/pause, mute, brightness, lock screen.
- [ ] 2.24 **Clipboard**: "Fasse zusammen, was in meiner Zwischenablage steht" (confirm, content is untrusted).
- [ ] 2.25 **Screenshot -> describe** ("Was siehst du auf meinem Bildschirm?", confirm each time, picture never stored).
- [ ] 2.26 **Open a website / search in a browser tab** (allow-list of schemes: https only).
  - Done when: each has a risk level of at least `confirm`, and an entry in the action log.

### Batch F -- Jarvis gets smarter about you
- [ ] 2.27 **Search past conversations** ("Worüber haben wir letzte Woche beim Projekt X gesprochen?").
- [ ] 2.28 **Habits and goals**: streak for daily goals (gym), weekly overview, Jarvis asks in the evening what is open.
- [ ] 2.29 **Proactive hints** (opt-in): upcoming appointment in 30 min, timer done, tomorrow's weather -- shown in the interface, never executed by themselves.
- [ ] 2.30 **Shopping / packing lists** as a widget and by chat.
  - Done when: everything stays visible and editable in the web interface (rule from Mark 4).

> Ideas welcome at any time: add them here as new lines in the right batch. The owner decides what is built.

## Phase 3 -- Decision: online, app, or both (decision step, no code)

### Step 3.1
- [ ] Decide the path with the numbers and experiences from Phases 1 and 2. Options:

| | Path A: go online | Path B: "cool app" |
|---|---|---|
| What you get | Jarvis from phone/other PCs via a link | A real program with its own window, tray icon, hotkey |
| Needs | Login, HTTPS, hosting, per-user data, cost limits | A shell around the existing web interface (e.g. Tauri or Electron) or a PWA |
| Security work | **A lot**: public server, attacks, passwords, rate limits | **Little** while the server stays on `127.0.0.1` |
| Risk | Someone else controls your Jarvis; bill from abuse | Low |
| Cost | Hosting (a few euros a month) | Free |
| Shows off | Anyone can try the guest mode | Looks and feels premium |
| Does Jarvis still run at home? | Yes, but the actions (Notepad, volume) must stay local | Yes, same machine |

  - Options for B, from cheap to big: (1) **PWA** (installable from the browser, one afternoon), (2) **desktop app** with Tauri/Electron
    (own window, tray, global hotkey "Strg+Leertaste", system notifications, start with Windows), (3) **mobile app** (much later).
  - Important: Jarvis' actions (open programs, volume, files) only work on **your** PC. Online, they would need a small
    home agent that connects out to the server. That is a separate, security-critical design; do not start it without its own document.
  - Done when: the owner writes the decision here ("A", "B", "B then A", ...) and the unchosen phase is moved to "Deferred".

## Phase 4A -- Go online (only if chosen)

- [ ] 4A.1 Design document `DESIGN_ONLINE.md`: threat model, what runs where (server vs. home PC), which abilities may run online at all.
- [ ] 4A.2 Clean server interface (versioned `/api/v1`, one error format); swap the standard-library server for FastAPI **only if** needed for sessions and tests.
- [ ] 4A.3 Login (password hashed, sessions with expiry, logout, rate limit on login attempts). One owner account first.
- [ ] 4A.4 Per-visitor conversations (today guests share one conversation).
- [ ] 4A.5 HTTPS (reverse proxy), secure cookies, CSRF protection, security headers.
- [ ] 4A.6 Guest mode online with its own tight limits (messages per minute/day, answer length).
- [ ] 4A.7 Deployment (host, domain, `.env` on the server, backups, logs, restart on crash).
- [ ] 4A.8 Security review and penetration checklist (own checks of every endpoint: not logged in, wrong user, huge input, injection).
- [ ] 4A.9 Home agent (only if actions should work remotely) -- own design first.
  - Done when: not logged in = nothing reachable except the login page and the guest chat; stability test repeated against the deployed server.

## Phase 4B -- The "really cool app" (only if chosen)

- [ ] 4B.1 Design document `DESIGN_APP.md`: look and feel goals (sketches/mockups first), what is better than the web page, technology choice with reasons.
- [ ] 4B.2 **PWA first**: manifest, icon, installable, works full-screen; check the wake word in the installed app.
- [ ] 4B.3 Desktop shell (Tauri or Electron): starts the server itself, one window, tray icon, closes to tray, start with Windows (switchable).
- [ ] 4B.4 System integration: global hotkey to open Jarvis or push-to-talk, notifications for timers/reminders, quick-input bar.
- [ ] 4B.5 New look: animated "Jarvis core" visual that reacts to listening/speaking, smoother transitions, themes, widgets that can be moved.
- [ ] 4B.6 Installer (one file to install and update), version shown in About.
  - Done when: a person who has never seen the project can install and start it with one file; the server still listens only on `127.0.0.1`.

## Phase 5 -- Mark 5 Final Validation

- [ ] 5.1 Acceptance test `ABNAHMETEST_MARK5.md` on a fresh clone (new abilities + the chosen path + everything from Mark 4 still working).
- [ ] 5.2 Stability test (`stabilitaetstest.py`) extended with the new endpoints and abilities.
- [ ] 5.3 Status document up to date, commit, tag `mark5`, push.

---

# Open Decisions

- **Same repository or new?** Proposal: same repository (baseline = tag `mark4`). Mark 4 started fresh because of the cleanup; there is nothing to clean now.
- **Which batch first?** Proposal: A (quick wins, almost no risk), then B, then C. D and E touch accounts and the computer and come after the safety work in Phase 1.
- **Web or app (or both)?** Decided in Phase 3 with real experience. Proposal: B (PWA -> desktop shell) first, because it is safe and fast; A only when you really want it from the phone.
- **Voice in the app:** the wake word needs an open tab and the browser's online recognition. An app can improve that; a fully offline wake word is a separate research step.

# Deferred (not Mark 5)

- Smart-home / hardware integration
- Camera and continuous screen perception
- Controlling any program freely (mouse/keyboard) -- only through the allow-list
- Self-development (Jarvis writes new abilities himself)
- Streaming answers (Mark 4, 2.6) and results for Adler Mannheim -- decide whenever they annoy you

# Mark 5 Definition of Done

Mark 5 is complete when:

1. [ ] The ability pattern is documented and every new ability has a risk level, a capability entry, a test and an acceptance row.
2. [ ] The chosen abilities of Batches A to F are built (the owner decides the final list).
3. [ ] Outside content (web, files, mails, documents) can never trigger an action.
4. [ ] The chosen path (A, B or both) works and is documented.
5. [ ] Acceptance test and stability test pass on a fresh clone.
6. [ ] Mark 5 is committed and tagged `mark5`.
