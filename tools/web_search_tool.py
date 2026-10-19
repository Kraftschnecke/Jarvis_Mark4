import requests
from config import BRAVE_API_KEY
from tools.tool_result import ToolResult

SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

# Ohne Timeout wuerde ein haengender Server Jarvis (und die GUI) blockieren.
REQUEST_TIMEOUT_SECONDS = 10


def search_web(query):
    if not BRAVE_API_KEY:
        return ToolResult(
            success=False,
            error="BRAVE_API_KEY fehlt in der .env, die Websuche ist nicht eingerichtet."
        )

    try:
        response = requests.get(
            SEARCH_URL,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": BRAVE_API_KEY
            },
            params={
                "q": query
            },
            timeout=REQUEST_TIMEOUT_SECONDS
        )

        response.raise_for_status()

        results = response.json().get("web", {}).get("results", [])

        structured_results = []

        for result in results:
            structured_results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "description": result.get("description", "")
            })

        return ToolResult(
            success=True,
            data=structured_results
        )

    except requests.exceptions.Timeout:
        return ToolResult(
            success=False,
            error="Die Websuche hat nicht rechtzeitig geantwortet."
        )

    except Exception as error:
        return ToolResult(
            success=False,
            error=str(error)
        )
