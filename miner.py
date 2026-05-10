import requests
import time
import hashlib
import base64
import json
import os
import re

# ── Configuration ────────────────────────────────────────────────────────────

API_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxcmFwbmxxcXRqZWRqeWhsZmNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyNzUyNjQsImV4cCI6MjA5Mzg1MTI2NH0.mf0fz6kAnK0yeAXrb-XT6yikbdRmeAq5jsikVPPhaFE"
WALLET = "0xe8b85a40c81545fdc607f3ee5efe53fd0ab3dc34"
AGENT  = "variz"

CACHE_FILE      = "answers.json"
RETRY_LIMIT     = 3
SLEEP_SUCCESS   = 5
SLEEP_NO_PUZZLE = 30
SLEEP_ERROR     = 10
SLEEP_RATE      = 2   # between retries

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json",
}

# ── Cache helpers ─────────────────────────────────────────────────────────────

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}

def save_cache(cache: dict) -> None:
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except IOError as e:
        print(f"[cache] Failed to save: {e}")

# ── Puzzle solvers ────────────────────────────────────────────────────────────

def solve_sha256(prompt: str) -> str | None:
    """
    Detect patterns like:
      'sha256 of <value>'  /  'hash of <value>'  /  'sha256(<value>)'
    Returns the hex digest.
    """
    patterns = [
        r"sha256\s+of\s+['\"]?([^'\"?\n]+?)['\"]?\s*\??$",
        r"hash\s+of\s+['\"]?([^'\"?\n]+?)['\"]?\s*\??$",
        r"sha256\(([^)]+)\)",
    ]
    for pat in patterns:
        m = re.search(pat, prompt, re.IGNORECASE)
        if m:
            value = m.group(1).strip()
            return hashlib.sha256(value.encode()).hexdigest()
    return None

def solve_base64(prompt: str) -> str | None:
    """
    Detect patterns like:
      'decode base64: <value>'  /  'base64 decode <value>'
    Returns the decoded string.
    """
    patterns = [
        r"decode\s+base64[:\s]+([A-Za-z0-9+/=]+)",
        r"base64\s+decode[:\s]+([A-Za-z0-9+/=]+)",
        r"base64\s+of\s+['\"]?([^'\"?\n]+?)['\"]?\s*\??$",
    ]
    for pat in patterns:
        m = re.search(pat, prompt, re.IGNORECASE)
        if m:
            value = m.group(1).strip()
            try:
                # Encode direction: if prompt says "encode", encode instead
                if re.search(r"\bencode\b", prompt, re.IGNORECASE):
                    return base64.b64encode(value.encode()).decode()
                return base64.b64decode(value).decode()
            except Exception:
                pass
    # Fallback: try to encode if prompt says "base64 encode"
    m = re.search(r"base64\s+encode[:\s]+(.+)", prompt, re.IGNORECASE)
    if m:
        try:
            return base64.b64encode(m.group(1).strip().encode()).decode()
        except Exception:
            pass
    return None

def solve_reverse(prompt: str) -> str | None:
    """
    Detect patterns like:
      'reverse of <value>'  /  'reverse the string <value>'
    Returns the reversed string.
    """
    patterns = [
        r"reverse\s+(?:of\s+|the\s+string\s+)['\"]?([^'\"?\n]+?)['\"]?\s*\??$",
        r"reverse[:\s]+['\"]?([^'\"?\n]+?)['\"]?\s*\??$",
    ]
    for pat in patterns:
        m = re.search(pat, prompt, re.IGNORECASE)
        if m:
            return m.group(1).strip()[::-1]
    return None

def solve_math(prompt: str) -> str | None:
    """
    Detect simple arithmetic expressions like:
      'what is 3 + 5?'  /  'calculate 10 * 4'  /  '7 - 2 = ?'
    Returns the result as a string (int if whole number, else float).
    """
    # Extract a math expression: numbers with +, -, *, /, ^, (, )
    m = re.search(
        r"(-?\d+(?:\.\d+)?)\s*([\+\-\*\/\^])\s*(-?\d+(?:\.\d+)?)",
        prompt,
    )
    if m:
        a_str, op, b_str = m.group(1), m.group(2), m.group(3)
        a, b = float(a_str), float(b_str)
        if op == "+":
            result = a + b
        elif op == "-":
            result = a - b
        elif op == "*":
            result = a * b
        elif op == "/":
            result = a / b if b != 0 else None
        elif op == "^":
            result = a ** b
        else:
            return None
        if result is None:
            return None
        return str(int(result)) if result == int(result) else str(result)
    return None

# ── Auto-detect and solve ─────────────────────────────────────────────────────

SOLVERS = [
    ("SHA256",   solve_sha256),
    ("Base64",   solve_base64),
    ("Reverse",  solve_reverse),
    ("Math",     solve_math),
]

def auto_solve(prompt: str) -> str | None:
    for name, solver in SOLVERS:
        try:
            answer = solver(prompt)
            if answer is not None:
                print(f"[solver] {name} matched → {answer!r}")
                return answer
        except Exception as e:
            print(f"[solver] {name} raised: {e}")
    return None

# ── API helpers ───────────────────────────────────────────────────────────────

def get_puzzle() -> dict:
    url = f"{API_URL}?eth={WALLET}"
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()

def submit_answer(puzzle_id: str, answer: str) -> requests.Response:
    payload = {
        "eth_address": WALLET,
        "agent_name":  AGENT,
        "puzzle_id":   puzzle_id,
        "answer":      answer,
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=15)
    return r

# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    cache = load_cache()
    print("[miner] Smart solver started.")

    while True:
        try:
            data = get_puzzle()
            puzzle = data.get("puzzle")

            if not puzzle:
                print("[miner] No puzzle available. Waiting…")
                time.sleep(SLEEP_NO_PUZZLE)
                continue

            puzzle_id = puzzle.get("id", "unknown")
            prompt    = puzzle.get("prompt") or puzzle.get("question") or ""
            print(f"[puzzle] id={puzzle_id}  prompt={prompt!r}")

            # ── Cache lookup ──────────────────────────────────────────────
            if puzzle_id in cache:
                answer = cache[puzzle_id]
                print(f"[cache] Hit — using cached answer: {answer!r}")
            else:
                answer = auto_solve(prompt)
                if answer is None:
                    print("[solver] No solver matched. Skipping puzzle.")
                    time.sleep(SLEEP_NO_PUZZLE)
                    continue
                cache[puzzle_id] = answer
                save_cache(cache)

            # ── Submit with retry ─────────────────────────────────────────
            for attempt in range(1, RETRY_LIMIT + 1):
                try:
                    resp = submit_answer(puzzle_id, answer)
                    print(f"[submit] attempt={attempt} status={resp.status_code} body={resp.text}")
                    if resp.status_code == 200:
                        break
                    time.sleep(SLEEP_RATE)
                except requests.RequestException as e:
                    print(f"[submit] attempt={attempt} error: {e}")
                    time.sleep(SLEEP_RATE)

            time.sleep(SLEEP_SUCCESS)

        except requests.RequestException as e:
            print(f"[error] Network error: {e}")
            time.sleep(SLEEP_ERROR)
        except Exception as e:
            print(f"[error] Unexpected: {e}")
            time.sleep(SLEEP_ERROR)

if __name__ == "__main__":
    main()
