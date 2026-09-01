import pandas as pd
import requests
import requests.adapters
import urllib3.util.connection as urllib3_conn

SUPABASE_URL = "https://kocihpxevlowqbguhstf.supabase.co"
SUPABASE_KEY = "sb_publishable_1MWEplxpyp0YOGW_TxZiMQ_HbvtHP5Z"
ALT_CLOUDFLARE_IPS = ["104.16.132.229", "104.18.32.7", "172.67.74.135"]


def _create_censorship_resistant_session(
    host_domain: str, alt_ip: str
) -> requests.Session:
    orig_create_connection = urllib3_conn.create_connection

    def patched_create_connection(address, *args, **kwargs):
        host, port = address
        if host == host_domain:
            host = alt_ip
        return orig_create_connection((host, port), *args, **kwargs)

    session = requests.Session()
    urllib3_conn.create_connection = patched_create_connection
    return session


def functionGetDataFromTable(
    tableName: str,
    url: str = SUPABASE_URL,
    key: str = SUPABASE_KEY,
    page_size: int = 1000,
) -> pd.DataFrame:
    """Fetches all rows from a specified Supabase REST endpoint using pagination."""
    endpoint = f"{url.rstrip('/')}/rest/v1/{tableName}?select=*"
    host_domain = url.replace("https://", "").replace("http://", "").split("/")[0]
    headers = {
        "apikey": key.strip(),
        "Authorization": f"Bearer {key.strip()}",
        "Content-Type": "application/json",
    }
    session = None

    for alt_ip in [None] + ALT_CLOUDFLARE_IPS:
        try:
            if alt_ip is None:
                test_session = requests.Session()
            else:
                test_session = _create_censorship_resistant_session(
                    host_domain, alt_ip
                )
            check_res = test_session.get(
                f"{url}/rest/v1/", headers=headers, timeout=5
            )
            if check_res.status_code < 500:
                session = test_session
                break
        except requests.exceptions.RequestException:
            continue

    if session is None:
        raise ConnectionError("Failed to reach Supabase across all routes.")

    all_data = []
    start_index = 0

    while True:
        page_headers = headers.copy()
        page_headers["Range"] = f"{start_index}-{start_index + page_size - 1}"
        response = session.get(endpoint, headers=page_headers, timeout=15)
        response.raise_for_status()
        chunk = response.json()

        if not chunk:
            break

        all_data.extend(chunk)

        if len(chunk) < page_size:
            break

        start_index += page_size

    return pd.DataFrame(all_data)