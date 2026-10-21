# Sprache (Step 6)

Ziel: J.A.R.V.I.S. kann Antworten vorlesen (6.1) und du kannst ihm per Mikrofon
schreiben (6.2). Beides ist **standardmäßig aus** und wird in den Einstellungen
unter **Voice** eingeschaltet.

## Entscheidung: Browser statt Server

Die Sprache läuft im Browser (Web Speech API), nicht im Python-Server.

| | Browser (gewählt) | Server (OpenAI Sprache) |
|---|---|---|
| Aufwand und Code | klein, nur `web/voice.js` | Audio hoch- und runterladen, Kosten pro Minute |
| Sicherheit | Server bekommt nur **Text**, wie bisher | neuer Weg für Audiodaten |
| Datenschutz | Chrome/Edge schicken Audio an einen Online-Dienst des Herstellers | Audio geht an OpenAI |
| Qualität | Stimme hängt vom Betriebssystem ab, gut genug | meist besser |

Falls dir die Stimme später nicht reicht, kann man die Ausgabe in `voice.js`
austauschen, ohne den Rest anzufassen.

## Nachtrag: Stimme von OpenAI (Step 6b)

Die Browser-Stimme klang nicht gut genug. Deshalb gibt es jetzt zwei Engines
(Einstellung **Voice engine**), Standard ist **OpenAI**:

```
Antworttext ─► Browser ─► POST /api/speak {"text"} ─► Server ─► OpenAI (gpt-4o-mini-tts) ─► MP3 ─► Browser spielt ab
```

- **Der Server bestimmt die Stimme**, nicht der Browser: Er liest `voice.voice` aus den
  Einstellungen. Eine "voice" oder ein "model" in der Anfrage wird ignoriert (Test in
  `test_server.py`). So kann keine fremde Seite die Kosten treiben oder Stimmen ändern.
- **Deutsch und Englisch**: Das Modell erkennt die Sprache am Text. Die Anweisung
  beschreibt nur die Art zu sprechen (ruhiger, trocken-höflicher Butler), keine
  bestimmte reale Stimme.
- **Sechs Stimmen**: Onyx, Echo, Ash (männlich), Nova, Shimmer, Coral (weiblich).
  Mit **Try voice** probierst du sie aus. Die Liste steht nur in `settings_manager.py`
  (Test prüft, dass `speech.py` dieselben kennt).
- **Schnell beim Start**: Der erste Satz wird allein angefragt, der Rest in größeren
  Stücken und schon während des Abspielens vorgeladen.
- **Rückfall**: Fällt OpenAI aus (kein Internet, Fehler), liest die Browser-Stimme den
  Rest vor, und eine Meldung erscheint einmal. Fehlertexte nach außen enthalten keine
  Schlüssel oder Adressen.
- **Kosten**: Es geht nur der vorgelesene Antworttext an OpenAI (höchstens 1200 Zeichen
  pro Anfrage). Die Modellwahl steht in `config.py` (`TTS_MODEL`, `JARVIS_TTS_MODEL` in der `.env`).
- **Eingabesprache**: Das Mikrofon hört auf Deutsch oder Englisch (Einstellung **Input language**).

## Wie es zusammenhängt

```
Mikrofon ─► SpeechRecognition (Browser) ─► Text ─► sendMessage()  ← derselbe Weg wie Tippen
Antwort  ─► speakReply() ─► cleanForSpeech ─► splitForSpeech ─► speechSynthesis
```

- **Spracheingabe ist nur Text.** Der erkannte Text geht in `sendMessage` wie
  getippter Text. Router, Risikostufen (4.2), Rückfragen und Aktionsprotokoll
  (4.3) gelten unverändert. Ein gesprochenes „Öffne die Datei …“ fragt genauso
  nach wie ein getipptes (Abnahme V10).
- **Push-to-talk.** Das Mikrofon läuft nur, solange du den Knopf hältst (Maus,
  Finger oder Leertaste/Enter). Es gibt kein Dauerlauschen.
- **Kein Selbstgespräch.** Beim Drücken des Mikrofons und bei jeder neuen
  Nachricht wird das Vorlesen abgebrochen.
- **Nur eigene Antworten werden vorgelesen:** Jarvis-Antworten und
  Hintergrundmeldungen (Timer). Fehlermeldungen, deine Nachrichten und der
  alte Verlauf beim Wechsel der Konversation nicht.
- **Vorlesen vorbereiten.** `cleanForSpeech` entfernt Markdown, Codeblöcke und
  ersetzt Links durch „Link“. `splitForSpeech` teilt in Stücke bis 180 Zeichen,
  weil Chrome lange Äußerungen abbrechen kann.
- **Stille ist kein Fehler.** „no-speech“ sendet nichts und zeigt nichts.

## Einstellungen

| Schlüssel | Werte | Standard |
|---|---|---|
| `voice.output` | an/aus | aus |
| `voice.speed` | Slow, Normal, Fast | Normal |
| `voice.input` | an/aus | aus |

Der Server prüft jeden Wert (`server.EDITABLE_SETTINGS`). Zusätzlich verwirft
`SettingsManager` beim Laden Werte mit falschem Typ oder Wert. Das war nötig,
weil deine alte Mark-3-Datei `voice.speed` als Zahl (150) enthielt; ohne diese
Prüfung hätte sie die neue Einstellung kaputt gemacht (Test `test_settings.py`).

## Grenzen

- Spracheingabe geht nur in Browsern mit `SpeechRecognition` (Chrome, Edge).
  Sonst bleibt der Knopf versteckt. Vorlesen geht in allen gängigen Browsern.
- Ob eine deutsche Stimme vorhanden ist, bestimmt das Betriebssystem. Ohne
  deutsche Stimme nimmt der Browser seine Standardstimme.
- Die Erkennung kann sich verhören. Bei Aktionen mit Folgen sieht man das an der
  Rückfrage; die steht dann als Text im Chat.

## Geprüft

- `test/test_voice.py` + `test/voice_check.py`: Textbereinigung, Zerlegung,
  Stimmenwahl, Abbruch beim Mikrofon, Stille, Fehler, Doppelstart, Standard aus,
  Einbindung in die Seite. Läuft nur mit Node.js voll; ohne Node gibt es einen Hinweis.
- `test_server.py`, `test_settings.py`: Validierung und alte Dateien.
- Browser-Prüfung mit simulierter Sprache (Playwright) und Gegenproben (Code
  absichtlich kaputt, Test wurde rot).
- Echte Stimme und echtes Mikrofon: nur du kannst das prüfen (Abnahme V1 bis V12).
