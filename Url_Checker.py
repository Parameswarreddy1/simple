import pandas as pd
import asyncio
import aiohttp
from aiohttp import ClientConnectorError, ClientSSLError, InvalidURL, TooManyRedirects, ClientError

df = pd.read_excel("input.xlsx")
urls = df.iloc[:, 0].dropna().tolist()

results = []

# -----------------------------------------------------
# AUTO ERROR CLASSIFIER
# -----------------------------------------------------
def classify_error(status, error):
    if status == 200:
        return "WORKING"
    if status == 404:
        return "NOT FOUND"
    if status == 403:
        return "FORBIDDEN"
    if status in (301, 302):
        return "REDIRECT"
    if status and status >= 500:
        return "SERVER ERROR"

    # Error-based classification
    if isinstance(error, ClientConnectorError):
        return "DNS ERROR"
    if isinstance(error, asyncio.TimeoutError):
        return "TIMEOUT"
    if isinstance(error, ClientSSLError):
        return "SSL ERROR"
    if isinstance(error, TooManyRedirects):
        return "TOO MANY REDIRECTS"
    if isinstance(error, InvalidURL):
        return "INVALID URL"
    if isinstance(error, ClientError):
        return "CLIENT ERROR"
    if error:
        return "UNKNOWN ERROR"

    return "OTHER"


# -----------------------------------------------------
# CHECK URL FUNCTION
# -----------------------------------------------------
async def check_url(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            status = response.status
            error = None
    except Exception as e:
        status = None
        error = e

    results.append({
        "url": url,
        "status": status,
        "status_type": classify_error(status, error),
        "error_message": str(error) if error else None
    })


# -----------------------------------------------------
# RUN PARALLEL WORKERS
# -----------------------------------------------------
async def main():
    conn = aiohttp.TCPConnector(limit=20)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [check_url(session, url) for url in urls]
        await asyncio.gather(*tasks)


asyncio.run(main())

# -----------------------------------------------------
# SAVE OUTPUT
# -----------------------------------------------------
pd.DataFrame(results).to_excel("url_status_output.xlsx", index=False)
print("DONE! Saved to url_status_output.xlsx")
