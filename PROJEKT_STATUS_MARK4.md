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
- [ ] New folder `Jarvis_Mark4`, new Git repository, new GitHub repository, first commit "Mark 3 baseline".
  - Done when: `git status` is clean, `.env`, `settings.json`, `programs.json` and `projects/` do not appear in Git, `py run_tests.py` is 13 of 13.

### Step 0.2
- [ ] Version string "Mark 4", this status document in place, `env.example` renamed to `.env.example`.
  - Done when: the settings dialog "About" shows "Mark 4".

### Step 0.3
- [ ] Back up the Neon database before any schema change (Neon branch or export).
  - Done when: a restore point exists and is noted here (name/date).

---

## Phase 1 -- Loose Ends from Mark 3 (bug fixes only)

### Step 1.1
- [ ] Opening a project by chat command ("Öffne Projekt X") also loads the conversation history in the chat window, not only the sidebar highlight.

### Step 1.2
- [ ] Test that the server is not reachable from another device in the network (Mark 3 test F5).

### Step 1.3
- [ ] Fresh-clone test of the new repository with only the documented setup.

---

## Phase 2 -- Measure, then Faster and Cheaper

### Step 2.1
- [ ] Measure first: log per message how many AI calls happen and how long each takes (simple timing log, switchable).
  - Done when: a table "call -> seconds" for 10 typical messages is in this file. These are the "before" numbers.

### Step 2.2
- [ ] Design: which of the five calls (command, task, memory, project analysis, answer) can be merged into one structured call? Write the design down and agree on it before coding.
  - Done when: a half-page design with the new JSON schema is in this file.

### Step 2.3
- [ ] Implement the merged call (structured output); the old calls stay as fallback until the tests pass.
  - Done when: all tests green, the acceptance checklist still passes, "after" numbers are lower than the "before" numbers.

### Step 2.4
- [ ] Connection pool for the database instead of one connection per function.

### Step 2.5
- [ ] Limit the conversation sent to the model (last N messages) and summarize older parts.

### Step 2.6
- [ ] Streaming: the answer appears word by word in the web interface.
  - Optional: do it only if the numbers from 2.1 show that waiting time is the main annoyance.

---

## Phase 3 -- Data in the Cloud, Memory Under Control

### Step 3.1
- [ ] Move `projects/<id>/project.md` into the database (with a one-time migration of existing files).
  - Done when: deleting the local `projects/` folder changes nothing.

### Step 3.2
- [ ] Memory view in the web interface: list all stored memories.

### Step 3.3
- [ ] Edit and delete single memories in the web interface.

### Step 3.4
- [ ] Decide for each stored-but-unused setting (language, name, address, personality, voice, accent color, UI scale): make it work or remove it.

---

## Phase 4 -- Safety Before Autonomy

### Step 4.1
- [ ] Web results and other tool results are marked as data for the answer and can never trigger further actions (prompt-injection protection), with a test that tries it.

### Step 4.2
- [ ] Risk levels for every action: `safe` (just do it), `confirm` (ask first), `forbidden` (never). Confirmation works in the web interface.

### Step 4.3
- [ ] Action log: what did Jarvis do, when, with which result. Visible in the web interface.

---

## Phase 5 -- Planner and Capabilities

### Step 5.1
- [ ] Plan format: a plan is a validated list of steps (task + parameters), never free text that is executed.

### Step 5.2
- [ ] Execute a plan: step limit, abort, result of one step available to the next.

### Step 5.3
- [ ] Show the plan to the user before running it; risky steps need confirmation (uses 4.2).

### Step 5.4
- [ ] Capability list generated from the task registry: Jarvis can answer "what can you do?" correctly.

---

## Phase 6 -- Voice

### Step 6.1
- [ ] Voice output: Jarvis reads answers aloud (switchable in settings).

### Step 6.2
- [ ] Voice input: speak instead of typing (push-to-talk button).

---

## Phase 7 -- Mark 4 Final Validation

### Step 7.1
- [ ] Acceptance test through the web interface (new checklist `ABNAHMETEST_MARK4.md`, based on the Mark 3 checklists).

### Step 7.2
- [ ] Stability test (server running for a longer time, many messages, errors in between).

### Step 7.3
- [ ] Status document up to date, commit, tag `mark4`, push. Declare Mark 4 complete.

---

# Deferred (not Mark 4)

Proposed for **Mark 5 -- "Go online"**:
- [ ] Login, separate users, HTTPS
- [ ] Swap the standard-library server for FastAPI
- [ ] Deployment (hosting, domain), public website

Later:
- [ ] Proactive behavior
- [ ] Self-development / adding new capabilities
- [ ] Computer control
- [ ] Perception: screen, camera and sensors
- [ ] Hardware / smart-home integration

---

# Open Decisions

- Is voice (Phase 6) part of Mark 4, or does it move behind the website (Mark 5)?
- Should the website (Mark 5) come before the planner (Phase 5)?

---

# Mark 4 Definition of Done

Mark 4 is complete when:

1. A normal message needs clearly fewer AI calls than in Mark 3 (numbers in this file).
2. Project context and memory are in the database and can be seen and edited in the web interface.
3. Every action has a risk level and is logged; tool results can never trigger actions.
4. A multi-step request is planned, shown to the user and executed safely.
5. Jarvis can speak and listen in the web interface.
6. The acceptance test and the stability test pass.
7. Mark 4 is committed and tagged as a stable release.
