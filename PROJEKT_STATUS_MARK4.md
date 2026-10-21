# J.A.R.V.I.S. -- Project Status (Mark 4)

_Started: 2026-10-19. Baseline: Mark 3 (tag `mark3` in the old repository `Jarvis_Mark3`)._

The description of the Mark 3 architecture, its decisions and its cleanup pass
is no longer part of this repository. It is kept in the old repository
`Jarvis_Mark3` (tag `mark3`, file `PROJEKT_STATUS_MARK3.md`) and in the Claude project.
Everything there still applies to Mark 4 unless this file says otherwise.

## Project Goal (long term)

Personal AI assistant inspired by J.A.R.V.I.S.: modular, with its own memory,
project management, tools, voice and several access points -- and built so that
its owner understands every part of it.

---

# Mark 4 -- Goals

Mark 3 is a stable foundation. Mark 4 makes it **faster, safer and more
capable**, in this order:

1. **Faster and cheaper.** Fewer AI calls per message, no new database
   connection per query, no unlimited conversation history.
2. **Everything in the cloud, everything visible.** Project context and memory live in the
   database and can be seen and edited in the web interface.
3. **Safe before autonomous.** Clear risk levels for actions, tool results are only
   data, every action is logged. This is the precondition for step 4.
4. **First real agent abilities.** A planner for multi-step requests and a
   capability list ("what can you do?").
5. **Voice.** Jarvis can speak and listen (in the web interface).

Not goals of Mark 4 (see "Deferred"): public website with login, proactive
behavior, computer control, perception, hardware.

## Development rules (unchanged from Mark 3)

> **Only work on one unchecked point at a time.**
> After each point: implement -> test -> check off -> commit.

- Every step ends with a green `py run_tests.py` and one commit.
- Every step has a "Done when" line. If it is not true, the step is not finished.
- Measure before optimizing. No speed change without a before/after number.
- Tests never use the real database, the AI API or start programs.
- The roadmap checkboxes are ticked by the owner.
- Mark 3 data in Neon stays safe: before the first database change, make a backup
  (Neon branch or export), see Step 0.3.

---

# Mark 4 -- One-Step-at-a-Time Roadmap

## Phase 0 -- Fresh Start

### Step 0.1
- [x] New folder `Jarvis_Mark4`, new Git repository, new GitHub repository, first commit "Mark 3 baseline".
  - Done when: `git status` is clean, `.env`, `settings.json`, `programs.json` and `projects/` do not appear in Git, `py run_tests.py` is 13 of 13.

### Step 0.2
- [x] Version string "Mark 4", this status document in place, `env.example` renamed to `.env.example`.
  - Done when: the settings dialog "About" shows "Mark 4".

### Step 0.3
- [x] Back up the Neon database before any schema change (Neon branch or export).
  - Done when: a restore point exists and is noted here (name/date).
  - Restore point: ____ (owner: please enter name and date).

---

## Phase 1 -- Loose Ends from Mark 3 (bug fixes only)

### Step 1.1
- [x] Opening a project by chat command ("Öffne Projekt X") also loads the conversation history in the chat window, not only the sidebar highlight.

### Step 1.2
- [x] Test that the server is not reachable from another device in the network (Mark 3 test F5).

### Step 1.3
- [x] Fresh-clone test of the new repository with only the documented setup.

---

## Phase 2 -- Measure, then Faster and Cheaper

### Step 2.1
- [x] Measure first: log per message how many AI calls happen and how long each takes (simple timing log, switchable).
  - Done when: a table "call -> seconds" for 10 typical messages is in this file. These are the "before" numbers.

### Step 2.2
- [x] Design: which of the five calls (command, task, memory, project analysis, answer) can be merged into one structured call? Write the design down and agree on it before coding.
  - Done when: a half-page design with the new JSON schema is in this file.

### Step 2.3
- [x] Implement the merged call (structured output); the old calls stay as fallback until the tests pass.
  - Done when: all tests green, the acceptance checklist still passes, "after" numbers are lower than the "before" numbers.

### Step 2.4
- [x] Connection pool for the database instead of one connection per function.

### Step 2.5
- [x] Limit the conversation sent to the model (last N messages) and summarize older parts.

### Step 2.6
- [ ] Streaming: the answer appears word by word in the web interface.
  - Optional: do it only if the numbers from 2.1 show that waiting time is the main annoyance.
  - **Skipped for Mark 4** (optional). Candidate for Mark 5, see "Deferred".

---

## Phase 3 -- Data in the Cloud, Memory Under Control

### Step 3.1
- [x] Move `projects/<id>/project.md` into the database (with a one-time migration of existing files).
  - Done when: deleting the local `projects/` folder changes nothing.

### Step 3.2
- [x] Memory view in the web interface: list all stored memories.

### Step 3.3
- [x] Edit and delete single memories in the web interface.

### Step 3.4
- [x] Decide for each stored-but-unused setting (language, name, address, personality, voice, accent color, UI scale): make it work or remove it.

---

## Phase 4 -- Safety Before Autonomy

### Step 4.1
- [x] Web results and other tool results are marked as data for the answer and can never trigger further actions (prompt-injection protection), with a test that tries it.

### Step 4.2
- [x] Risk levels for every action: `safe` (just do it), `confirm` (ask first), `forbidden` (never). Confirmation works in the web interface.

### Step 4.3
- [x] Action log: what did Jarvis do, when, with which result. Visible in the web interface.

---

## Phase 5 -- Planner and Capabilities

### Step 5.1
- [x] Plan format: a plan is a validated list of steps (task + parameters), never free text that is executed.

### Step 5.2
- [x] Execute a plan: step limit, abort, result of one step available to the next.

### Step 5.3
- [x] Show the plan to the user before running it; risky steps need confirmation (uses 4.2).

### Step 5.4
- [x] Capability list generated from the task registry: Jarvis can answer "what can you do?" correctly.

---

## Phase 6 -- Voice

### Step 6.1
- [x] Voice output: Jarvis reads answers aloud (switchable in settings).

### Step 6.2
- [x] Voice input: speak instead of typing (push-to-talk button).

### Added during Phase 6 (the owner's idea list, all accepted and checked off in `ABNAHMETEST_WEB.md`)
- [x] Better voice: OpenAI voice (default Onyx, man/woman choice, German and English), browser voice as fallback (`DESIGN_VOICE.md`).
- [x] Stop button for running speech and running plan.
- [x] Short status report at start ("Guten Morgen, Sir. ...", open timers).
- [x] Several named timers, cancel one by name, number or "shorter/longer".
- [x] Wake word "Jarvis" (own switch, default off, same security gates as typing).
- [x] Guest mode (`py server.py --guest`): chat only, no actions, no memory (`DESIGN_GUEST.md`).
- [x] Right sidebar with three selectable widgets: clock/date/calendar, notes/goals, ice hockey (Oilers via NHL, Adler Mannheim via their calendar file) (`DESIGN_WIDGETS.md`).
- [x] Calendar with own entries; Jarvis can add and list entries (`ADD_CALENDAR_EVENT`, `LIST_CALENDAR_EVENTS`).
- [x] Daily recurring goals; collapsible left and right sidebars.

---

## Phase 7 -- Mark 4 Final Validation

### Step 7.1
- [X] Acceptance test through the web interface (new checklist `ABNAHMETEST_MARK4.md`, based on the Mark 3 checklists).
  - Done when: 0 deviations, run on a fresh clone of the repository.

### Step 7.2
- [X] Stability test (server running for a longer time, many messages, errors in between).
  - `py stabilitaetstest.py 300`: the real `server.py` under mixed load with deliberate errors (invalid input, aborted connections, wrong host/origin, an error inside the AI call). Measures answer time, threads, handles, memory.
  - Done when: it prints `STABILITY TEST PASSED` (also row 9.1 of the acceptance test). Result (own run, 300 s, 16 workers): ~40,000 requests, 820 deliberate errors, no unexpected status, threads and handles back to start, memory +4.5 MB, 95% under 0.4 s. Owner run: rund 39.800 Anfragen, Median 24 ms, Threads am Ende 2, +4,1 MB

### Step 7.3
- [X] Status document up to date, commit, tag `mark4`, push. Declare Mark 4 complete.

---

# Deferred (not Mark 4)

Proposed for **Mark 5 -- "Go online"**:
- [ ] Login, separate users, HTTPS (per-visitor conversations: guests currently share one conversation)
- [ ] Swap the standard-library server for FastAPI
- [ ] Deployment (hosting, domain), public website

Ideas collected during Mark 4 (not decided):
- [ ] Reading files and documents
- [ ] Real calendar connection (e.g. Google Calendar), reminders and repeating entries
- [ ] Weather and news as a task or widget; a daily briefing
- [ ] Installable app (PWA) so Jarvis opens like a program
- [ ] Offline wake word (the browser version sends audio to the browser maker's service)
- [ ] Streaming answers (2.6), results for Adler Mannheim
- [ ] More teams for the ice hockey widget

Later:
- [ ] Proactive behavior
- [ ] Self-development / adding new capabilities
- [ ] Computer control
- [ ] Perception: screen, camera and sensors
- [ ] Hardware / smart-home integration

---

# Open Decisions

Decided during Mark 4:

- Voice (Phase 6) **stayed in Mark 4** and was extended (see Phase 6).
- The website with login moves to **Mark 5**. Mark 4 only prepared it (guest mode, local-only server, allow-lists).
- The planner (Phase 5) came before the website, as in the roadmap.

Still open:

- **Results for Adler Mannheim.** The official calendar file has only pairings and times. Results exist only as HTML on `penny-del.org` (no data interface, can change any time). Decide: leave as is, or add a fragile reader.
- **Streaming (2.6).** Skipped. Worth doing if the wait for long answers still annoys.
- **Which Mark 5 topic first:** login and HTTPS, or the next abilities (read files, real calendar, weather/news)?

---

# Mark 4 Definition of Done

Mark 4 is complete when:

1. [x] A normal message needs clearly fewer AI calls than in Mark 3 (numbers in this file).
   - `MESSUNGEN_MARK4.md`: ten identical messages, **32 -> 24 AI calls**, **55.5 s -> 36.4 s** (about a third less); database share per message 0.5-0.7 s -> 0.15-0.3 s.
2. [x] Project context and memory are in the database and can be seen and edited in the web interface.
3. [x] Every action has a risk level and is logged; tool results can never trigger actions.
4. [x] A multi-step request is planned, shown to the user and executed safely.
5. [x] Jarvis can speak and listen in the web interface.
6. [ ] The acceptance test and the stability test pass. (`ABNAHMETEST_MARK4.md`, `py stabilitaetstest.py 300`)
7. [ ] Mark 4 is committed and tagged as a stable release.

## How to close Mark 4 (Step 7.3)

```
py run_tests.py
git status
git add -A
git commit -m "Mark 4: final validation, status document"
git tag -a mark4 -m "Mark 4 complete"
git push
git push origin mark4
```

Then tick 7.1, 7.2, 7.3 and Definition points 6 and 7 and commit that last change too (`git commit -am "Tick Mark 4 complete"`, `git push`).
The tag stays on the commit that was tested; if the status file changes afterwards, that is fine.
