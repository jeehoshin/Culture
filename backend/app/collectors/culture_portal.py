from collections.abc import Iterable

import httpx


def _find_items(node: object) -> Iterable[dict]:
    if isinstance(node, list):
        for item in node:
            yield from _find_items(item)
    elif isinstance(node, dict):
        if any(key.upper() in {"TITLE", "SUBJECT", "EVENT_NM"} for key in node):
            yield node
        else:
            for child in node.values():
                yield from _find_items(child)


def parse_json_payload(payload: dict) -> list[dict]:
    return list(_find_items(payload))


class CulturePortalClient:
    def __init__(self, api_key: str, api_url: str, client: httpx.AsyncClient | None = None):
        self.api_key = api_key
        self.api_url = api_url
        self.client = client or httpx.AsyncClient(timeout=30)

    async def list_events(self, page: int = 1, rows: int = 100) -> list[dict]:
        response = await self.client.get(
            self.api_url,
            params={"serviceKey": self.api_key, "numOfRows": rows, "pageNo": page, "type": "json"},
        )
        response.raise_for_status()
        return parse_json_payload(response.json())
