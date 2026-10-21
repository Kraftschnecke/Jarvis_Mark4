// Prueft web/wake.js ohne Browser (wird von test_wake.py mit Node gestartet)
const assert = require("assert");
const path = require("path");
const W = require(path.join(__dirname, "..", "web", "wake.js"));

// --- Weckwort-Erkennung: nur am Anfang einer Aeusserung
const rest = (t) => { const m = W.matchWakeWord(t); return m === null ? null : m.rest; };
assert.strictEqual(rest("Jarvis"), "");
assert.strictEqual(rest("jarvis."), "");
assert.strictEqual(rest("Jarvis, stelle einen Timer auf 10 Sekunden"), "stelle einen Timer auf 10 Sekunden");
assert.strictEqual(rest("Hey Jarvis wie spät ist es"), "wie spät ist es");
assert.strictEqual(rest("okay, Jarvis! Öffne den Rechner"), "Öffne den Rechner");
assert.strictEqual(rest("  JARVIS   hallo  "), "hallo");
assert.strictEqual(rest("Dscharvis was geht"), "was geht");
// Nicht am Anfang, anderes Wort, nur aehnlich geschrieben: keine Reaktion
assert.strictEqual(rest("Ich finde Jarvis cool"), null);
assert.strictEqual(rest("Der Film Jarvis"), null);
assert.strictEqual(rest("Jarvisch"), null);
assert.strictEqual(rest("Jarvis2"), null);
assert.strictEqual(rest("Servus"), null);
assert.strictEqual(rest(""), null);
assert.strictEqual(rest(null), null);
assert.strictEqual(rest(undefined), null);
assert.strictEqual(rest(42), null);
assert.strictEqual(rest("hey hey Jarvis"), null);          // nur ein Gruss davor

// --- Dauer-Zuhoerer mit gefaelschtem Browser
let clock = 0;
let timers = [];
const fakeSetTimeout = (fn, ms) => { const t = { fn, ms, live: true }; timers.push(t); return t; };
const fakeClearTimeout = (t) => { if (t) t.live = false; };
function runTimers() {
  const due = timers.filter((t) => t.live);
  timers = [];
  due.forEach((t) => { t.live = false; t.fn(); });
}

let instances = [];
class Rec {
  constructor() { this.started = false; this.aborted = false; instances.push(this); }
  start() { if (Rec.failStart) throw new Error("busy"); this.started = true; }
  abort() { this.aborted = true; }
  say(text, isFinal = true) {
    if (!this.onresult) return;   // abgemeldete Handler hoert der Browser nicht mehr
    this.onresult({ resultIndex: 0, results: [Object.assign([{ transcript: text }], { isFinal })] });
  }
  end() { if (this.onend) this.onend(); }
  fail(code) { if (this.onerror) this.onerror({ error: code }); }
}

function make() {
  instances = []; timers = []; clock = 0; Rec.failStart = false;
  const log = { wakes: [], states: [], errors: [] };
  const listener = W.createWakeListener({
    Recognition: Rec,
    onWake: (r) => log.wakes.push(r),
    onState: (s) => log.states.push(s),
    onError: (c) => log.errors.push(c),
    setTimeout: fakeSetTimeout, clearTimeout: fakeClearTimeout, now: () => clock,
  });
  return { listener, log };
}

// Ohne Browser-Unterstuetzung
let h = make();
assert.strictEqual(W.createWakeListener({ Recognition: undefined }).canListen(), false);
assert.strictEqual(h.listener.canListen(), true);

// Anschalten startet kontinuierliches Zuhoeren in der gewaehlten Sprache
h.listener.setActive(true, "en-US");
assert.strictEqual(instances.length, 0, "Start erst im naechsten Takt");
runTimers();
assert.strictEqual(instances.length, 1);
let r = instances[0];
assert(r.started && r.continuous === true && r.lang === "en-US" && r.interimResults === false);
assert.deepStrictEqual(h.log.states, ["listening"]);

// Gespraech ohne Weckwort wird verworfen, Zwischenstand zaehlt nie
r.say("Jarvis hilf mir", false);
r.say("ich habe gestern einen Film gesehen");
assert.deepStrictEqual(h.log.wakes, []);

// Weckwort: Befehl wird gemeldet, Zuhoerer haelt an (hoert sich nicht selbst zu)
r.say("Jarvis stelle einen Timer");
assert.deepStrictEqual(h.log.wakes, ["stelle einen Timer"]);
assert(r.aborted, "nach dem Weckwort darf der Zuhoerer nicht weiterlaufen");
assert.strictEqual(h.log.states[h.log.states.length - 1], "off");
r.say("Jarvis nochmal");                        // nachgelieferte Ereignisse werden ignoriert
r.end();
runTimers();
assert.strictEqual(instances.length, 1, "ohne setActive kein Neustart");
assert.strictEqual(h.log.wakes.length, 1);

// Nach der Reaktion: App meldet "wieder zuhoeren" -> neuer Start
h.listener.setActive(true);
runTimers();
assert.strictEqual(instances.length, 2);
r = instances[1];

// Chrome beendet das Zuhoeren von selbst (nach Stille): automatischer Neustart
clock = 20000; r.end(); runTimers();
assert.strictEqual(instances.length, 3);
r = instances[2];

// Pausieren (z.B. waehrend Jarvis spricht oder antwortet)
h.listener.setActive(false);
assert(r.aborted);
assert.strictEqual(h.log.states[h.log.states.length - 1], "off");
r.end(); runTimers();
assert.strictEqual(instances.length, 3, "pausiert: kein Neustart");
h.listener.setActive(false);                    // doppelt ausschalten schadet nicht
assert.strictEqual(instances.length, 3);

// Wiederholtes Anschalten startet nur einen Zuhoerer
h.listener.setActive(true); h.listener.setActive(true); h.listener.setActive(true);
runTimers();
assert.strictEqual(instances.length, 4);
h.listener.setActive(true);
runTimers();
assert.strictEqual(instances.length, 4);

// Spracheinstellung geaendert: neuer Zuhoerer mit neuer Sprache
h.listener.setActive(true, "de-DE");
runTimers();
assert.strictEqual(instances.length, 5);
assert.strictEqual(instances[4].lang, "de-DE");
assert(instances[3].aborted);

// Fatale Fehler: aufhoeren und melden (Mikrofon verweigert)
h = make();
h.listener.setActive(true, "de-DE"); runTimers();
instances[0].fail("not-allowed");
assert.deepStrictEqual(h.log.errors, ["not-allowed"]);
assert.strictEqual(h.listener.isActive(), false);
runTimers();
assert.strictEqual(instances.length, 1);

// Harmlose Fehler (keine Sprache gehoert) fuehren zum Neustart, nicht zum Aufgeben
h = make();
h.listener.setActive(true, "de-DE"); runTimers();
instances[0].fail("no-speech"); clock = 8000; instances[0].end(); runTimers();
assert.strictEqual(instances.length, 2);
assert.deepStrictEqual(h.log.errors, []);

// Dauernde Fehlstarts: nach einigen Versuchen aufgeben statt endlos zu kreisen
h = make();
h.listener.setActive(true, "de-DE");
for (let i = 0; i < 20 && h.listener.isActive(); i++) {
  runTimers();
  const last = instances[instances.length - 1];
  clock += 100; last.end();
}
assert.strictEqual(h.listener.isActive(), false);
assert.deepStrictEqual(h.log.errors, ["unstable"]);
assert(instances.length <= 8, instances.length);

// start() wirft (Mikrofon belegt): aufgeben mit Meldung, kein Absturz
h = make(); Rec.failStart = true;
h.listener.setActive(true, "de-DE"); runTimers();
assert.deepStrictEqual(h.log.errors, ["start-failed"]);
assert.strictEqual(h.listener.isActive(), false);

console.log("wake.js OK");
