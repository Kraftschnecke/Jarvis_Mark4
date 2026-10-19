import psycopg
from config import MODEL
from llm_json import parse_llm_json
from database import DATABASE_URL


class Memory:
    EMPTY_CONTEXT = "No stored information about the user."

    def __init__(self):
        self.memories = {}
        self.ensure_table()

    def ensure_table(self):
        """Legt die Tabelle an, falls sie fehlt (z.B. frische Datenbank)."""
        with psycopg.connect(DATABASE_URL) as connection:
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
        # "with" committet bei Erfolg, rollt bei Fehler zurueck und schliesst
        # die Verbindung in jedem Fall.
        with psycopg.connect(DATABASE_URL) as connection:
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
        with psycopg.connect(DATABASE_URL) as connection:
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
        with psycopg.connect(DATABASE_URL) as connection:
            cursor = connection.cursor()

            cursor.execute("SELECT key, value, type FROM memories")

            memories = cursor.fetchall()

        for key, value, memory_type in memories:
            self.memories[key] = {
                "value": value,
                "type": memory_type
            }

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
