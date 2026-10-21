// Prueft web/voice.js ohne Browser (wird von test_voice.py mit Node gestartet)
const assert = require("assert");
const path = require("path");
const V = require(path.join(__dirname, "..", "web", "voice.js"));

// --- cleanForSpeech
assert.strictEqual(V.cleanForSpeech("**Fett** und `Code`"), "Fett und Code");
assert.strictEqual(V.cleanForSpeech("Vorher ```print(1)``` nachher"), "Vorher nachher");
assert.strictEqual(V.cleanForSpeech("Siehe https://example.com/a?b=c jetzt"), "Siehe Link jetzt");
assert.strictEqual(V.cleanForSpeech("# Titel\n- eins\n- zwei"), "Titel\neins\nzwei");
assert.strictEqual(V.cleanForSpeech(null), "");
assert.strictEqual(V.cleanForSpeech(undefined), "");
assert.strictEqual(V.cleanForSpeech(42), "42");

// --- splitForSpeech
assert.deepStrictEqual(V.splitForSpeech("Eins. Zwei! Drei?"), ["Eins.", "Zwei!", "Drei?"]);
assert.deepStrictEqual(V.splitForSpeech("a\nb"), ["a", "b"]);
assert.deepStrictEqual(V.splitForSpeech(""), []);
const long = ("wort ".repeat(100)).trim();            // 499 Zeichen ohne Satzende
const parts = V.splitForSpeech(long, 50);
assert(parts.length > 5);
parts.forEach((p) => assert(p.length <= 50, p.length));
assert.strictEqual(parts.join(" "), long);            // nichts geht verloren
const solid = "x".repeat(130);                        // kein Leerzeichen
assert.deepStrictEqual(V.splitForSpeech(solid, 50).map((p) => p.length), [50, 50, 30]);

// --- pickVoice
const de1 = { lang: "de-DE", localService: false, name: "online" };
const de2 = { lang: "de_AT", localService: true, name: "lokal" };
const en = { lang: "en-US", localService: true, name: "en" };
assert.strictEqual(V.pickVoice([en, de1, de2]), de2);
assert.strictEqual(V.pickVoice([en, de1]), de1);
assert.strictEqual(V.pickVoice([en]), null);
assert.strictEqual(V.pickVoice([{ lang: "deu-x" }]), null);   // "deu" ist keine de-Stimme
assert.strictEqual(V.pickVoice(undefined), null);

// --- Sprachausgabe
function makeSynth(voices) {
  const synth = { spoken: [], cancelled: 0 };
  synth.speak = (u) => synth.spoken.push(u);
  synth.cancel = () => { synth.cancelled++; };
  synth.getVoices = () => voices;
  return synth;
}
class Utt { constructor(text) { this.text = text; } }

let synth = makeSynth([en, de2]);
let voice = V.createVoice({ synth, Utterance: Utt });
assert.strictEqual(voice.canSpeak(), true);
assert.strictEqual(voice.speak("**Hallo** Sir. Alles gut.", "Fast"), true);
assert.deepStrictEqual(synth.spoken.map((u) => u.text), ["Hallo Sir.", "Alles gut."]);
synth.spoken.forEach((u) => {
  assert.strictEqual(u.lang, "de-DE");
  assert.strictEqual(u.rate, V.SPEEDS.Fast);
  assert.strictEqual(u.voice, de2);
});
assert(synth.cancelled >= 1, "altes Vorlesen muss vor dem neuen abgebrochen werden");

synth = makeSynth([]); voice = V.createVoice({ synth, Utterance: Utt });
voice.speak("Test.", "Gibtsnicht");
assert.strictEqual(synth.spoken[0].rate, 1);                  // unbekannte Geschwindigkeit -> normal
assert.strictEqual("voice" in synth.spoken[0], false);        // keine deutsche Stimme -> keine erzwungen
assert.strictEqual(voice.speak("   ", "Normal"), false);       // nichts zu sagen
assert.strictEqual(voice.speak("```nur code```", "Normal"), false);
voice.stopSpeaking();
assert(synth.cancelled >= 1);

// ohne Unterstuetzung: kein Absturz, ehrliche Antwort
const none = V.createVoice({});
assert.strictEqual(none.canSpeak(), false);
assert.strictEqual(none.canListen(), false);
assert.strictEqual(none.speak("Hallo"), false);
none.stopSpeaking(); none.stopListening();
assert.strictEqual(none.startListening({ onState() {}, onText() {} }), false);

// --- Spracheingabe
class Rec {
  constructor() { Rec.last = this; this.started = 0; this.stopped = 0; }
  start() { this.started++; if (Rec.failStart) throw new Error("busy"); }
  stop() { this.stopped++; }
}
function result(text, isFinal) { return { resultIndex: 0, results: [Object.assign([{ transcript: text }], { isFinal })] }; }

synth = makeSynth([]);
voice = V.createVoice({ synth, Utterance: Utt, Recognition: Rec });
assert.strictEqual(voice.canListen(), true);
const log = { states: [], texts: [], errors: [] };
const handlers = {
  onState: (s) => log.states.push(s),
  onText: (t) => log.texts.push(t),
  onError: (e) => log.errors.push(e),
};
const before = synth.cancelled;
assert.strictEqual(voice.startListening(handlers), true);
assert(synth.cancelled > before, "beim Sprechen muss das Vorlesen stoppen");
assert.strictEqual(Rec.last.lang, "de-DE");
assert.strictEqual(Rec.last.continuous, false);
assert.strictEqual(Rec.last.interimResults, false);
assert.strictEqual(voice.isListening(), true);
assert.strictEqual(voice.startListening(handlers), false);     // nicht doppelt
assert.strictEqual(Rec.last.started, 1);
voice.stopListening();
assert.strictEqual(Rec.last.stopped, 1);

const rec = Rec.last;
rec.onresult(result("Wie spät", false));                        // Zwischenstand zaehlt nicht
rec.onresult(result("Wie spät ist es", true));
rec.onend();
assert.deepStrictEqual(log.texts, ["Wie spät ist es"]);
assert.deepStrictEqual(log.states, ["listening", "idle"]);
assert.strictEqual(voice.isListening(), false);

// Stille: nichts wird gesendet
assert.strictEqual(voice.startListening(handlers), true);
Rec.last.onerror({ error: "no-speech" });
Rec.last.onend();
assert.deepStrictEqual(log.texts, ["Wie spät ist es"]);
assert.deepStrictEqual(log.errors, []);

// Echter Fehler wird gemeldet, Text trotzdem nicht gesendet
assert.strictEqual(voice.startListening(handlers), true);
Rec.last.onerror({ error: "not-allowed" });
Rec.last.onend();
assert.deepStrictEqual(log.errors, ["not-allowed"]);
assert.strictEqual(log.texts.length, 1);

// start() schlaegt fehl -> Zustand sauber
Rec.failStart = true;
assert.strictEqual(voice.startListening(handlers), false);
assert.strictEqual(voice.isListening(), false);
Rec.failStart = false;
assert.strictEqual(voice.startListening(handlers), true);

console.log("voice.js OK");
