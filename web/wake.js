// Weckwort "Jarvis" (Step 6c): hoert im Browser dauernd zu, aber reagiert nur,
// wenn eine Aeusserung MIT "Jarvis" beginnt. Alles andere wird sofort vergessen.
// Der erkannte Befehl geht danach denselben Weg wie getippter Text (gleiche Pruefungen).
(function (root) {
  "use strict";

  // Wie der Browser "Jarvis" schreibt, wenn er es verhoert (deutsch und englisch gesprochen)
  const WAKE_WORDS = ["jarvis", "jarwis", "jarvies", "jarvice", "jarves", "jarvas", "dscharvis", "tscharvis", "charvis"];
  const GREETINGS = ["hey", "hi", "hallo", "hello", "ok", "okay", "ey"];

  const PATTERN = new RegExp(
    "^\\s*(?:(?:" + GREETINGS.join("|") + ")[\\s,.!?:;-]+)?(?:" + WAKE_WORDS.join("|") + ")(?![\\p{L}\\p{N}])[\\s,.!?:;-]*(.*)$",
    "isu"
  );

  // Gibt null zurueck, wenn der Satz nicht mit dem Weckwort beginnt, sonst { rest }:
  // der Befehl hinter dem Weckwort (leer, wenn nur "Jarvis" gesagt wurde).
  function matchWakeWord(transcript) {
    if (typeof transcript !== "string") return null;
    const match = PATTERN.exec(transcript);
    return match ? { rest: match[1].trim() } : null;
  }

  // Dauer-Zuhoerer. Chrome beendet kontinuierliches Zuhoeren von selbst (nach Stille,
  // nach einigen Minuten), darum starten wir es nach jedem Ende neu.
  // env: Recognition, onWake(rest), onState("listening"|"off"), onError(code),
  //      setTimeout, clearTimeout, now (fuer Tests austauschbar)
  function createWakeListener(env) {
    const Recognition = env.Recognition;
    const onWake = env.onWake || (() => {});
    const onState = env.onState || (() => {});
    const onError = env.onError || (() => {});
    const later = env.setTimeout || setTimeout;
    const cancel = env.clearTimeout || clearTimeout;
    const now = env.now || (() => Date.now());

    const RESTART_DELAY = 300;     // ms bis zum Neustart
    const QUICK_END = 1500;        // Ende kuerzer als das = Fehlstart
    const MAX_QUICK_ENDS = 6;      // so viele Fehlstarts hintereinander: aufgeben

    let active = false;
    let language = "de-DE";
    let rec = null;
    let timer = null;
    let quickEnds = 0;
    let lastState = "off";

    function setState(state) {
      if (state === lastState) return;
      lastState = state;
      onState(state);
    }

    function canListen() { return typeof Recognition === "function"; }

    function stopRecognition() {
      const current = rec;
      rec = null;
      if (current) {
        current.onresult = current.onend = current.onerror = null;
        try { current.abort(); } catch (error) { /* war schon beendet */ }
      }
    }

    function give(code) {
      active = false;
      stopRecognition();
      setState("off");
      onError(code);
    }

    function run() {
      timer = null;
      if (!active || rec || !canListen()) return;

      const mine = new Recognition();
      const startedAt = now();
      mine.lang = language;
      mine.continuous = true;
      mine.interimResults = false;
      mine.maxAlternatives = 1;

      mine.onresult = (event) => {
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (!event.results[i].isFinal) continue;
          const hit = matchWakeWord(event.results[i][0].transcript);
          if (!hit) continue;           // alles ohne Weckwort wird verworfen
          quickEnds = 0;
          stopRecognition();            // waehrend Jarvis reagiert, hoert der Zuhoerer nicht mit
          setState("off");
          onWake(hit.rest);
          return;
        }
      };
      mine.onerror = (event) => {
        const code = event && event.error;
        if (code === "not-allowed" || code === "service-not-allowed" || code === "audio-capture" ||
            code === "language-not-supported") {
          give(code);
        }
        // "no-speech", "aborted", "network": onend startet neu (bei Dauerfehlern gibt quickEnds auf)
      };
      mine.onend = () => {
        if (rec !== mine) return;
        rec = null;
        if (!active) return;
        quickEnds = now() - startedAt < QUICK_END ? quickEnds + 1 : 0;
        if (quickEnds >= MAX_QUICK_ENDS) { give("unstable"); return; }
        setState("off");
        timer = later(run, RESTART_DELAY);
      };

      rec = mine;
      try {
        mine.start();
      } catch (error) {
        rec = null;
        give("start-failed");
        return;
      }
      setState("listening");
    }

    // Anschalten oder pausieren. Wiederholtes Aufrufen mit demselben Wert tut nichts.
    function setActive(value, lang) {
      if (lang && lang !== language) {
        language = lang;
        if (active && rec) stopRecognition();   // neue Sprache gilt ab dem naechsten Start
      }
      if (value === active) {
        if (active && !rec && !timer) timer = later(run, 0);
        return;
      }
      active = value;
      if (active) {
        quickEnds = 0;
        if (!timer) timer = later(run, 0);
      } else {
        if (timer) { cancel(timer); timer = null; }
        stopRecognition();
        setState("off");
      }
    }

    function isActive() { return active; }

    return { canListen, setActive, isActive };
  }

  const api = { matchWakeWord, createWakeListener, WAKE_WORDS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.JarvisWake = api;
})(typeof window !== "undefined" ? window : this);
