// Hilfen fuer die Seitenleisten-Widgets (Etappe C). Reine Funktionen ohne Seite,
// damit sie sich mit Node pruefen lassen. Das Zeichnen steht in app.js.
(function (root) {
  "use strict";

  const pad = (n) => String(n).padStart(2, "0");

  // "14:05:09" (24 Stunden)
  function formatClock(date) {
    return pad(date.getHours()) + ":" + pad(date.getMinutes()) + ":" + pad(date.getSeconds());
  }

  // "Mittwoch, 21. Oktober 2026"
  function formatDateLong(date, locale) {
    return new Intl.DateTimeFormat(locale || "de-DE", {
      weekday: "long", day: "numeric", month: "long", year: "numeric",
    }).format(date);
  }

  // "Oktober 2026"
  function monthTitle(year, month, locale) {
    return new Intl.DateTimeFormat(locale || "de-DE", { month: "long", year: "numeric" })
      .format(new Date(year, month, 1));
  }

  // Wochentage, Montag zuerst: ["Mo", "Di", ...]
  function weekdayNames(locale) {
    const format = new Intl.DateTimeFormat(locale || "de-DE", { weekday: "short" });
    const names = [];
    for (let day = 1; day <= 7; day++) names.push(format.format(new Date(2024, 0, day)).replace(".", ""));  // 1.1.2024 = Montag
    return names;
  }

  // Monatsraster, Montag zuerst: Liste von Wochen, jede mit 7 Eintraegen (Tag oder null)
  function calendarWeeks(year, month) {
    const first = (new Date(year, month, 1).getDay() + 6) % 7;     // 0 = Montag
    const days = new Date(year, month + 1, 0).getDate();
    const cells = Array(first).fill(null);
    for (let day = 1; day <= days; day++) cells.push(day);
    while (cells.length % 7 !== 0) cells.push(null);
    const weeks = [];
    for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
    return weeks;
  }

  // Ein Spiel fuer die Anzeige. game kommt vom Server (widgets.py).
  // { teamName, opponent, home, score: "3 : 1" | null, outcome: "win"|"loss"|null, when, live }
  function describeGame(game, options) {
    const opts = options || {};
    const mine = game.team_is_home ? game.home : game.away;
    const other = game.team_is_home ? game.away : game.home;
    const hasScore = Number.isInteger(game.home.score) && Number.isInteger(game.away.score);
    let outcome = null;
    if (game.state === "final" && hasScore && mine.score !== other.score) {
      outcome = mine.score > other.score ? "win" : "loss";
    }
    const start = new Date(game.start);
    const when = Number.isNaN(start.getTime()) ? "" : new Intl.DateTimeFormat(opts.locale || "de-DE", {
      weekday: "short", day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit",
      timeZone: opts.timeZone,
    }).format(start);
    return {
      teamName: mine.name,
      opponent: other.name,
      home: game.team_is_home === true,
      // Immer Heimteam zuerst, so wie im Sport ueblich
      score: hasScore ? game.home.score + " : " + game.away.score : null,
      outcome,
      when,
      live: game.state === "live",
    };
  }

  // "2026-10-23" (so speichert der Server Tage)
  function dateKey(year, month, day) {
    return year + "-" + pad(month + 1) + "-" + pad(day);
  }

  // Termine nach Tag: { "2026-10-23": [termin, ...] }
  function eventsByDate(events) {
    const result = {};
    (Array.isArray(events) ? events : []).forEach((event) => {
      if (!event || typeof event.date !== "string") return;
      (result[event.date] = result[event.date] || []).push(event);
    });
    return result;
  }

  // "Freitag, 23. Oktober" fuer einen Tag im Format JJJJ-MM-TT
  function formatDayLong(key, locale) {
    const [year, month, day] = key.split("-").map(Number);
    return new Intl.DateTimeFormat(locale || "de-DE", { weekday: "long", day: "numeric", month: "long" })
      .format(new Date(year, month - 1, day));
  }

  const api = { formatClock, formatDateLong, monthTitle, weekdayNames, calendarWeeks, describeGame,
                dateKey, eventsByDate, formatDayLong };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.JarvisWidgets = api;
})(typeof window !== "undefined" ? window : this);
