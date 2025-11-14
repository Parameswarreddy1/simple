"""
deep_url_checker.py
Full professional deep URL checker:
 - Fast aiohttp primary checks
 - Playwright fallback for JS rendering / blocked pages
 - SSL certificate inspection with cryptography (fixed UTC warning)
 - Processes in chunks of 50 URLs
 - Shows total URLs
 - Removes title extraction
 - Saves after each chunk with success message
 - Final Excel output: url_deep_check_results.xlsx
"""

import asyncio
import aiohttp
import time
import pandas as pd
import socket
import ssl
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from urllib.parse import urlparse
from aiohttp import ClientConnectorError, ClientSSLError, InvalidURL, TooManyRedirects, ClientError
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# -------------------------
# CONFIG
# -------------------------
INPUT_EXCEL = "input.xlsx"
OUTPUT_EXCEL = "url_deep_check_results.xlsx"
CONCURRENCY = 30
TIMEOUT = 12
RETRIES = 2
PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_ENABLED = True
CHUNK_SIZE = 50

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/117.0 Safari/537.36"
)

CAPTCHA_HINTS = [
    "captcha", "recaptcha", "cloudflare", "bot", "access denied",
    "verify you are human", "human verification", "cf-chl-bypass"
]

# -------------------------
# SSL Fetch and Validate  (UTC FIX APPLIED)
# -------------------------
def fetch_ssl_cert(host: str, port: int = 443, timeout: float = 5.0):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der = ssock.getpeercert(binary_form=True)
        cert = x509.load_der_x509_certificate(der, default_backend())
        return {
            "issuer": cert.issuer.rfc4514_string(),
            "subject": cert.subject.rfc4514_string(),
            "not_before": cert.not_valid_before_utc,   # FIXED
            "not_after": cert.not_valid_after_utc,     # FIXED
            "cert": cert
        }
    except Exception as e:
        raise

def ssl_is_valid_for_host(cert_obj, host: str) -> bool:
    cert = cert_obj["cert"]
    try:
        # SANs
        try:
            ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            dns = ext.value.get_values_for_type(x509.DNSName)
        except:
            dns = []

        # CN
        try:
            cn = ""
            for attr in cert.subject:
                if "CN" in attr.oid._name:
                    cn = attr.value
                    break
        except:
            cn = ""

        host = host.lower()
        for dn in dns:
            if host == dn.lower() or host.endswith("." + dn.lower().lstrip("*.")):
                return True

        if cn:
            c = cn.lower()
            if host == c or host.endswith("." + c.lstrip("*.")):
                return True

        return False
    except:
        return False

# -------------------------
# Classify HTTP & Errors
# -------------------------
def classify_status_and_error(status, error, html_snippet, final_url):
    if error:
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
        return "UNKNOWN ERROR"

    if status == 200:
        if html_snippet:
            low = html_snippet.lower()
            for hint in CAPTCHA_HINTS:
                if hint in low:
                    return "BLOCKED / CAPTCHA"
            if "page not found" in low or ("404" in low and "404" in low.split()[:50]):
                return "CONTENT NOT FOUND"
        return "WORKING"

    if status == 404:
        return "NOT FOUND"
    if status == 403:
        return "FORBIDDEN"
    if status and status >= 500:
        return "SERVER ERROR"
    if status in (301, 302):
        return "REDIRECT"
    return "OTHER"

# -------------------------
# Fast aiohttp Check
# -------------------------
async def aiohttp_check(session, url):
    last_exc = None
    for attempt in range(RETRIES + 1):
        start = time.perf_counter()
        try:
            async with session.get(url, timeout=TIMEOUT, allow_redirects=True) as resp:
                rt = (time.perf_counter() - start) * 1000
                try:
                    text = await resp.text()
                    snippet = text[:6000]
                except:
                    snippet = None
                return {
                    "http_status": resp.status,
                    "final_url": str(resp.url),
                    "html_snippet": snippet,
                    "response_time_ms": int(rt),
                    "error": None
                }
        except Exception as e:
            last_exc = e
            await asyncio.sleep(0.4)
    return {
        "http_status": None,
        "final_url": None,
        "html_snippet": None,
        "response_time_ms": None,
        "error": last_exc
    }

# -------------------------
# Playwright JS Rendering (NO TITLE)
# -------------------------
async def playwright_check(playwright, url):
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(user_agent=USER_AGENT)
    page = await context.new_page()

    try:
        await page.goto(url, timeout=PLAYWRIGHT_TIMEOUT, wait_until="networkidle")
        content = await page.content()
        final = page.url
        captcha = any(h in content.lower() for h in CAPTCHA_HINTS)

        return {
            "pw_content_snippet": content[:10000],
            "pw_final_url": final,
            "pw_captcha": captcha,
            "pw_error": None
        }
    except Exception as e:
        return {
            "pw_content_snippet": None,
            "pw_final_url": None,
            "pw_captcha": False,
            "pw_error": e
        }
    finally:
        await context.close()
        await browser.close()

# -------------------------
# Worker
# -------------------------
async def process_url(sem, session, url, playwright_obj):
    async with sem:
        row = {
            "url": url,
            "http_status": None,
            "final_url": None,
            "status_type": None,
            "error_message": None,
            "content_length": None,
            "is_js_page": False,
            "captcha_detected": False,
            "ssl_valid": None,
            "ssl_issuer": None,
            "ssl_notBefore": None,
            "ssl_notAfter": None,
            "response_time_ms": None
        }

        # Normalize URL
        if not url.lower().startswith(("http://", "https://")):
            url_to_check = "http://" + url
        else:
            url_to_check = url

        # 1) Fast check
        a = await aiohttp_check(session, url_to_check)
        row["http_status"] = a["http_status"]
        row["final_url"] = a["final_url"]
        row["content_length"] = len(a["html_snippet"]) if a["html_snippet"] else 0
        row["response_time_ms"] = a["response_time_ms"]
        row["error_message"] = str(a["error"]) if a["error"] else None
        row["status_type"] = classify_status_and_error(
            a["http_status"], a["error"], a["html_snippet"], a["final_url"]
        )

        snippet = a["html_snippet"] or ""
        maybe_js = (
            a["http_status"] == 200 and
            ("<script" in snippet.lower() or len(snippet) < 800)
        )

        needs_pw = row["status_type"] in ("BLOCKED / CAPTCHA", "UNKNOWN ERROR") or maybe_js

        # 2) Playwright fallback
        if PLAYWRIGHT_ENABLED and playwright_obj and needs_pw:
            pw = await playwright_check(playwright_obj, url_to_check)
            row["is_js_page"] = True
            row["captcha_detected"] = pw["pw_captcha"]
            if pw["pw_final_url"]:
                row["final_url"] = pw["pw_final_url"]
            if pw["pw_captcha"]:
                row["status_type"] = "BLOCKED / CAPTCHA"
            elif pw["pw_content_snippet"]:
                row["status_type"] = "WORKING (JS_RENDERED)"
            if pw["pw_error"]:
                row["error_message"] = str(pw["pw_error"])

        # 3) SSL check (UTC FIX APPLIED)
        try:
            parsed = urlparse(url_to_check)
            host = parsed.hostname
            if parsed.scheme == "https" and host:
                cert_obj = fetch_ssl_cert(host)
                row["ssl_issuer"] = cert_obj["issuer"]
                row["ssl_notBefore"] = cert_obj["not_before"]   # FIXED
                row["ssl_notAfter"] = cert_obj["not_after"]     # FIXED

                now = pd.Timestamp.utcnow().to_pydatetime()
                valid = (
                    cert_obj["not_before"] <= now <= cert_obj["not_after"]
                    and ssl_is_valid_for_host(cert_obj, host)
                )
                row["ssl_valid"] = valid
        except Exception as e:
            row["ssl_valid"] = False
            row["error_message"] = row["error_message"] or f"SSL error: {e}"

        return row

# -------------------------
# Run All URLs
# -------------------------
async def run_all(urls):
    sem = asyncio.Semaphore(CONCURRENCY)
    timeout = aiohttp.ClientTimeout(sock_connect=10, sock_read=10)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)

    playwright_obj = None
    if PLAYWRIGHT_ENABLED:
        playwright_obj = await async_playwright().start()

    results = []

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT}
    ) as session:
        tasks = [process_url(sem, session, url, playwright_obj) for url in urls]

        for fut in asyncio.as_completed(tasks):
            r = await fut
            results.append(r)
            print(f"Done: {r['url']} -> {r['status_type']} ({r['http_status']})")

    if playwright_obj:
        await playwright_obj.stop()

    return results

# -------------------------
# MAIN (with chunking + totals)
# -------------------------
def main():
    df = pd.read_excel(INPUT_EXCEL)
    urls = df.iloc[:, 0].dropna().astype(str).tolist()

    if not urls:
        print("No URLs in input.xlsx")
        return

    total = len(urls)
    all_results = []
    chunk_id = 1

    for i in range(0, total, CHUNK_SIZE):
        chunk = urls[i:i + CHUNK_SIZE]

        print(f"\n🔥 Processing Chunk {chunk_id} "
              f"(URLs {i+1} to {i+len(chunk)} of TOTAL {total})...")

        chunk_results = asyncio.run(run_all(chunk))
        all_results.extend(chunk_results)

        pd.DataFrame(all_results).to_excel(OUTPUT_EXCEL, index=False)
        print(f"✅ Chunk {chunk_id} saved successfully!")

        chunk_id += 1

    pd.DataFrame(all_results).to_excel(OUTPUT_EXCEL, index=False)
    print("\n🎉 ALL chunks processed and saved successfully!")
    print(f"📁 Output File: {OUTPUT_EXCEL}")

if __name__ == "__main__":
    main()
