# Bleibt als eigener Import-Weg bestehen (from database import DATABASE_URL);
# der Wert selbst kommt aus config.py.
from config import DATABASE_URL  # noqa: F401
