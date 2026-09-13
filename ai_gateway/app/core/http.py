import httpx


http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(5.0),
)
