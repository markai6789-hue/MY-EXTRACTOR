
# ============================================================
#  Facebook Dumper \u2014 Optimized Edition
#  Improvements:
#   1. concurrent.futures.ThreadPoolExecutor  (parallel I/O)
#   2. Dynamic User-Agent rotator             (anti-block)
#   3. Graceful timeout / retry handling      (resilience)
# ============================================================

import os, sys, re, json, time, random, requests, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters  import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup as bs

# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# \u00a71  USER-AGENT POOL & ROTATOR
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

UA_POOL = [
    # Chrome \u2013 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome \u2013 macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6)   AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Firefox \u2013 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Firefox \u2013 macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]

class UARotator:
    """Thread-safe, sequential-shuffle User-Agent rotator."""

    def __init__(self, pool: list[str] = UA_POOL):
        self._pool   = pool[:]
        self._queue  = []
        self._lock   = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if not self._queue:                 # refill + shuffle when empty
                self._queue = self._pool[:]
                random.shuffle(self._queue)
            return self._queue.pop()

# Module-level singleton so every class shares one rotator
_ua_rotator = UARotator()


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# \u00a72  HEADER FACTORIES  (use rotator)
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def HeadersGet(ua: str | None = None) -> dict:
    ua = ua or _ua_rotator.get()
    return {
        "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding":           "gzip, deflate, br",
        "Accept-Language":           "en-US,en;q=0.9",
        "Cache-Control":             "max-age=0",
        "Sec-Ch-Ua-Mobile":          "?0",
        "Sec-Fetch-Dest":            "document",
        "Sec-Fetch-Mode":            "navigate",
        "Sec-Fetch-Site":            "same-origin",
        "Sec-Fetch-User":            "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent":                ua,
        "Viewport-Width":            "1280",
    }

def HeadersPost(ua: str | None = None) -> dict:
    ua = ua or _ua_rotator.get()
    return {
        "Accept":           "*/*",
        "Accept-Encoding":  "gzip, deflate, br",
        "Accept-Language":  "en-US,en;q=0.9",
        "Content-Type":     "application/x-www-form-urlencoded",
        "Origin":           "https://www.facebook.com",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Fetch-Dest":   "empty",
        "Sec-Fetch-Mode":   "cors",
        "Sec-Fetch-Site":   "same-origin",
        "User-Agent":       ua,
    }


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# \u00a73  SESSION FACTORY  (retry + timeout adapter)
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

# Global timeouts  (connect, read)  in seconds
REQUEST_TIMEOUT   = (10, 30)
MAX_RETRIES       = 3
BACKOFF_FACTOR    = 0.8            # wait = backoff * (2 ** (attempt - 1))
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)

def make_session() -> requests.Session:
    """
    Returns a requests.Session pre-configured with:
      \u2022 automatic retries on transient HTTP errors
      \u2022 connection pool keep-alive
    """
    session = requests.Session()
    retry = Retry(
        total            = MAX_RETRIES,
        backoff_factor   = BACKOFF_FACTOR,
        status_forcelist = RETRY_STATUS_CODES,
        allowed_methods  = ["GET", "POST"],
        raise_on_status  = False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    return session


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# \u00a74  HELPERS
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def ConvertURL(i: str) -> str:
    i = str(i).strip()
    if "http" in i:
        for old in ("m.facebook.com", "mbasic.facebook.com"):
            i = i.replace(old, "www.facebook.com")
        return i
    for old in ("m.facebook.com", "mbasic.facebook.com"):
        i = i.replace(old, "www.facebook.com")
    if "facebook.com" in i.lower():
        return "https://www.facebook.com" + re.sub(r"(?i)facebook\.com", "", i)
    return f"https://www.facebook.com/{i}"


def GetData(req: str) -> dict:
    """Extract GraphQL / DTSG tokens from a raw HTML page string."""
    def _g(pattern):
        m = re.search(pattern, req)
        return m.group(1) if m else ""

    av       = _g(r'"actorID":"(.*?)"')
    fb_dtsg  = _g(r'"DTSGInitialData",\[\],\{"token":"(.*?)"\}')
    jazoest  = _g(r'jazoest=(.*?)"')
    lsd      = _g(r'"LSD",\[\],\{"token":"(.*?)"\}')

    return {
        "av":          av,
        "__user":      av,
        "__a":         str(random.randint(1, 6)),
        "__hs":        _g(r'"haste_session":"(.*?)"'),
        "dpr":         "1.5",
        "__ccg":       _g(r'"connectionClass":"(.*?)"'),
        "__rev":       _g(r'"__spin_r":(.*?),'),
        "__spin_r":    _g(r'"__spin_r":(.*?),'),
        "__spin_b":    _g(r'"__spin_b":"(.*?)"'),
        "__spin_t":    _g(r'"__spin_t":(.*?),'),
        "__hsi":       _g(r'"hsi":"(.*?)"'),
        "__comet_req": "15",
        "fb_dtsg":     fb_dtsg,
        "jazoest":     jazoest,
        "lsd":         lsd,
    }


def _safe_get(session, url, cookie, retries=3, **kwargs) -> str:
    """GET with timeout + retry + UA rotation, returns '' on total failure."""
    for attempt in range(1, retries + 1):
        try:
            r = session.get(
                url,
                headers  = HeadersGet(),
                cookies  = {"cookie": cookie},
                timeout  = REQUEST_TIMEOUT,
                allow_redirects = True,
                **kwargs,
            )
            r.raise_for_status()
            return r.text
        except requests.exceptions.Timeout:
            print(f"\[WARN] GET timeout  (attempt {attempt}/{retries}): {url}", end="")
            time.sleep(BACKOFF_FACTOR * (2 ** attempt))
        except requests.exceptions.ConnectionError as e:
            print(f"\[WARN] Connection error (attempt {attempt}/{retries}): {e}", end="")
            time.sleep(BACKOFF_FACTOR * (2 ** attempt))
        except requests.exceptions.HTTPError as e:
            print(f"\[WARN] HTTP error (attempt {attempt}/{retries}): {e}", end="")
            if e.response is not None and e.response.status_code == 429:
                time.sleep(5 + random.uniform(1, 3))   # back-off on rate-limit
            else:
                break
    return ""


def _safe_post(session, url, data, cookie, retries=3, **kwargs):
    """POST with timeout + retry + UA rotation, returns None on total failure."""
    for attempt in range(1, retries + 1):
        try:
            r = session.post(
                url,
                data    = data,
                headers = HeadersPost(),
                cookies = {"cookie": cookie},
                timeout = REQUEST_TIMEOUT,
                **kwargs,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            print(f"\[WARN] POST timeout  (attempt {attempt}/{retries})", end="")
            time.sleep(BACKOFF_FACTOR * (2 ** attempt))
        except requests.exceptions.ConnectionError as e:
            print(f"\[WARN] Connection error (attempt {attempt}/{retries}): {e}", end="")
            time.sleep(BACKOFF_FACTOR * (2 ** attempt))
        except requests.exceptions.HTTPError as e:
            print(f"\[WARN] HTTP error (attempt {attempt}/{retries}): {e}", end="")
            if e.response is not None and e.response.status_code == 429:
                time.sleep(5 + random.uniform(1, 3))
            else:
                break
        except (ValueError, KeyError):
            print(f"\[WARN] JSON parse error (attempt {attempt}/{retries})", end="")
            break
    return None


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# \u00a75  THREAD-SAFE WRITER
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

class SafeFileWriter:
    """
    Buffers lines and flushes to disk in a dedicated writer thread.
    All dump workers push to an in-memory queue; one thread drains it.
    This removes file-lock contention from hot paths.
    """

    SENTINEL = None     # poison pill

    def __init__(self, filepath: str, buffer_size: int = 50):
        import queue
        self._path   = filepath
        self._q      = queue.Queue()
        self._buf    = buffer_size
        self._thread = threading.Thread(target=self._writer, daemon=True)
        self._thread.start()

    def write(self, line: str):
        self._q.put(line)

    def close(self):
        self._q.put(self.SENTINEL)
        self._thread.join()

    def _writer(self):
        import queue
        lines = []
        while True:
            try:
                item = self._q.get(timeout=1)
            except queue.Empty:
                if lines:
                    self._flush(lines); lines = []
                continue
            if item is self.SENTINEL:
                if lines: self._flush(lines)
                return
            lines.append(item)
            if len(lines) >= self._buf:
                self._flush(lines); lines = []

    def _flush(self, lines: list):
        with open(self._path, "a", encoding="utf-8") as f:
            f.write("\
".join(lines) + "\
")


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# \u00a76  DUMP PROFILE  (optimised)
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

class DumpProfile:
    """
    Dumps friend-lists and follower lists from Facebook profiles.

    Parallel strategy
    -----------------
    *  Page-fetching is inherently sequential (cursor-based pagination).
    *  Parallelism is applied at the *target* level: multiple profile
       URLs are processed concurrently via ThreadPoolExecutor.
    *  Inside each target a dedicated session + UA is used so threads
       don't share mutable state.
    """

    MAX_WORKERS = 4     # concurrent profile targets

    def __init__(self):
        self._cookie     = open("login/cookie.json", "r").read().strip()
        self._seen_lock  = threading.Lock()
        self._count_lock = threading.Lock()
        self._seen       = set()
        self._total      = 0
        os.makedirs("dump", exist_ok=True)

    # \u2500\u2500 public entry points \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def SortTarget(self, dump_type: int):
        print("Banyak ID/URL, Pisahkan Dengan Koma (,)")
        raw_targets = input("Target : ").split(",")
        targets     = [ConvertURL(t.strip()) for t in raw_targets if t.strip()]
        print("Tekan Ctrl+C untuk skip/berhenti\
")

        fn_map = {1: self._dump_friendlist_target,
                  2: self._dump_followers_target}
        fn = fn_map.get(dump_type)
        if fn is None:
            print("Tipe tidak valid!")
            return

        try:
            with ThreadPoolExecutor(max_workers=self.MAX_WORKERS,
                                    thread_name_prefix="profile") as pool:
                futures = {pool.submit(fn, url): url for url in targets}
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        future.result()
                    except KeyboardInterrupt:
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise
                    except Exception as exc:
                        print(f"\
[ERROR] {url}: {exc}")
        except KeyboardInterrupt:
            print("\
Dihentikan oleh pengguna.")

    # \u2500\u2500 profile validation (per-thread session) \u2500\u2500

    def _check_profile(self, url: str, session: requests.Session):
        html = _safe_get(session, url, self._cookie)
        if not html:
            return None, None, None
        try:
            uid  = re.search(r'"userID":"(.*?)"',           html).group(1)
            name = re.search(r'"profile_owner":\{"id":"%s","name":"(.*?)"' % uid, html).group(1)
            return uid, name, html
        except AttributeError:
            return None, None, None

    # \u2500\u2500 friendlist \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _dump_friendlist_target(self, url: str):
        session = make_session()
        uid, name, html = self._check_profile(url, session)
        if not uid:
            print(f"[SKIP] Profile not found: {url}\
")
            return

        print(f"ID   : {uid}\
Name : {name}")
        try:
            flid = re.search(r'\{"tab_key":"friends_all","id":"(.*?)"\}', html).group(1)
        except AttributeError:
            print(f"[SKIP] Cannot find friend-list tab for {url}\
")
            return

        data_base = GetData(html)
        data_base.update({
            "fb_api_caller_class":      "RelayModern",
            "fb_api_req_friendly_name": "ProfileCometAppCollectionListRendererPaginationQuery",
            "server_timestamps":        True,
            "doc_id":                   "6709724792472394",
        })

        filepath = f"dump/{uid}friend.txt"
        open(filepath, "w").close()          # truncate
        writer  = SafeFileWriter(filepath)
        counter = {"n": 0}

        self._paginate_friendlist(session, data_base, flid, None, writer, counter)
        writer.close()

        if counter["n"] == 0:
            print(f"\[FAIL] No IDs dumped for {uid}\
")
        else:
            print(f"\[OK]   Dumped {counter['n']} IDs \u2192 {filepath}\
")

    def _paginate_friendlist(self, session, data, flid, cursor, writer, counter):
        """Recursive cursor-based paginator (runs inside a worker thread)."""
        payload = {**data, "variables": json.dumps({
            "count":   8,
            "cursor":  cursor,
            "scale":   1.5,
            "search":  None,
            "id":      flid,
        })}
        resp = _safe_post(session,
                          "https://www.facebook.com/api/graphql/",
                          payload, self._cookie)
        if resp is None:
            return

        try:
            edges = resp["data"]["node"]["pageItems"]["edges"]
        except (KeyError, TypeError):
            return

        for edge in edges:
            try:
                owner = (edge["node"]["actions_renderer"]
                             ["action"]["client_handler"]
                             ["profile_action"]["restrictable_profile_owner"])
                rec = f"{owner['id']}|{owner['name']}"
                with self._seen_lock:
                    if rec in self._seen:
                        continue
                    self._seen.add(rec)
                writer.write(rec)
                with self._count_lock:
                    counter["n"] += 1
                    self._total  += 1
                print(f"\Dumped {self._total} IDs (total)", end="")
                sys.stdout.flush()
            except (KeyError, TypeError):
                continue

        try:
            page_info = resp["data"]["node"]["pageItems"]["page_info"]
            if page_info["has_next_page"]:
                self._paginate_friendlist(session, data, flid,
                                          page_info["end_cursor"],
                                          writer, counter)
        except (KeyError, TypeError):
            pass

    # \u2500\u2500 followers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

    def _dump_followers_target(self, url: str):
        session = make_session()
        uid, name, html = self._check_profile(url, session)
        if not uid:
            print(f"[SKIP
