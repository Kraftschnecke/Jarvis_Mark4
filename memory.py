import db
from config import MODEL
from llm_json import parse_llm_json


# Erlaubte Typen und Laenge eines Werts (gilt fuer das Bearbeiten ueber die Seite)
VALID_TYPES = ("fact", "preference")
MAX_VALUE_LENGTH = 500


class Memory:
    EMPTY_CONTEXT = "No stored information about the user."

    def __init__(self):
        self.memories = {}
        self.ensure_table()

    def ensure_table(self):
        """Legt die Tabelle an, falls sie fehlt (z.B. frische Datenbank)."""
        with db.connect() as connection:
            connection.cursor().execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    type TEXT NOT NULL
                )
                """
            )

    def save(self, key, value, memory_type):
        # "with" committet bei Erfolg, rollt bei Fehler zurueck und gibt die
        # Verbindung in jedem Fall an den Pool zurueck.
        with db.connect() as connection:
            connection.cursor().execute(
                """
                INSERT INTO memories (key, value, type)
                VALUES (%s, %s, %s)
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    type = EXCLUDED.type
                """,
                (key, value, memory_type)
            )

        # Erst nach erfolgreichem Speichern im Arbeitsspeicher uebernehmen,
        # damit Datenbank und Cache nicht auseinanderlaufen.
        self.memories[key] = {
            "value": value,
            "type": memory_type
        }

    def get(self, key):
        with db.connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                "SELECT value FROM memories WHERE key = %s",
                (key,)
            )

            result = cursor.fetchone()

        if result is not None:
            return result[0]

        return None

    def load(self):
        with db.connect() as connection:
            cursor = connection.cursor()

            cursor.execute("SELECT key, value, type FROM memories")

            memories = cursor.fetchall()

        for key, value, memory_type in memories:
            self.memories[key] = {
                "value": value,
                "type": memory_type
            }

    def list_all(self):
        """Alle gespeicherten Eintraege aus der Datenbank (fuer die Anzeige).

        Liest bewusst die Datenbank und nicht den Zwischenspeicher: Die Seite
        soll zeigen, was wirklich gespeichert ist.
        """
        with db.connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                "SELECT key, value, type FROM memories ORDER BY type, key"
            )

            rows = cursor.fetchall()

        return [
            {"key": key, "value": value, "type": memory_type}
            for key, value, memory_type in rows
        ]

    def update(self, key, value, memory_type):
        """Aendert Wert und Typ eines vorhandenen Eintrags.

        Gibt False zurueck, wenn es den Eintrag nicht (mehr) gibt. Neue
        Eintraege entstehen nur ueber save().
        """
        with db.connect() as connection:
            cursor = connection.cursor()

            cursor.execute(
                "UPDATE memories SET value = %s, type = %s WHERE key = %s",
                (value, memory_type, key)
            )

            found = cursor.rowcount > 0

        if found:
            self.memories[key] = {"value": value, "type": memory_type}
        else:
            self.memories.pop(key, None)

        return found

    def delete(self, key):
        """Loescht einen Eintrag. False, wenn es ihn nicht (mehr) gibt."""
        with db.connect() as connection:
            cursor = connection.cursor()

            cursor.execute("DELETE FROM memories WHERE key = %s", (key,))

            found = cursor.rowcount > 0

        self.memories.pop(key, None)

        return found

    def delete_all(self):
        """Loescht ALLE Eintraege. Gibt die Anzahl der geloeschten zurueck."""
        with db.connect() as connection:
            cursor = connection.cursor()

            cursor.execute("DELETE FROM memories")

            count = max(cursor.rowcount, 0)

        self.memories.clear()

        return count

    def get_context(self):
        if not self.memories:
            return self.EMPTY_CONTEXT

        memory_lines = []

        for key, memory in self.memories.items():
            memory_lines.append(
                f"{memory['type']}: {key} = {memory['value']}")

        return "\n".join(memory_lines)

    def analyze(self, client, message):
        response = client.responses.create(
            model=MODEL,
            input=f"""
    Analyze this message:

    "{message}"

    Determine whether the message contains a lasting personal
    fact about the user
    that would be useful for a personal AI assistant to remember.

    Store information such as:
    - name
    - age
    - date of birth
    - preferences
    - hobbies
    - interests
    - favorite things
    - location
    - occupation
    - habits
    - other meaningful personal facts

    Personal facts explicitly stated by the user should be remembered,
    even if they seem simple, such as the user's age.

    Determine the type of personal information.

    Use exactly one of these types:

    - fact: objective information about the user, such as name, age,
    date of birth, location, occupation, etc.
    - preference: likes, dislikes, favorite things, hobbiess, interests,
    or other personal preferences.

    Do not store:
    - questions
    - temporary events
    - random statements that are not useful long-term
    - Random or irrelevant facts about other people

    If it should be remembered, create a short, descriptive snake_case key
    that clearly represents the information.

    The value should contain only the actual information, 
    not a sentence about the user.

    Return ONLY valid JSON in this exact format:
    {{"key": "short_key", "value": "value", "type": "fact_or_preference"}}

    If it should not be remembered, return ONLY:
    {{"key": null, "value": null, "type": null}}

    Do not include any other text.
    """
        )

        return parse_llm_json(
            response.output_text,
            {"key": None, "value": None, "type": None}
        )

    def process(self, client, message):
        result = self.analyze(client, message)

        if (
            result["key"] is not None
            and result["value"] is not None
            and result["type"] in ("fact", "preference")
        ):
            self.save(
                result["key"],
                result["value"],
                result["type"]
            )
