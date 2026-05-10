import requests
import time
import hashlib
import base64
import json
import re
import os
import google.generativeai as genai

API_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxcmFwbmxxcXRqZWRqeWhsZmNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyNzUyNjQsImV4cCI6MjA5Mzg1MTI2NH0.mf0fz6kAnK0yeAXrb-XT6yikbdRmeAq5jsikVPPhaFE"

WALLET = "0xe8b85a40c81545fdc607f3ee5efe53fd0ab3dc34"
AGENT = "variz"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

model = None

if GEMINI_API_KEY:
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

headers = {
"apikey": API_KEY,
"Content-Type": "application/json"
}

CACHE_FILE = "answers.json"

try:
with open(CACHE_FILE, "r") as f:
cache = json.load(f)
except:
cache = {}

def save_cache():
with open(CACHE_FILE, "w") as f:
json.dump(cache, f, indent=2)

def get_puzzle():
url = f"{API_URL}?eth={WALLET}"

```
r = requests.get(
    url,
    headers=headers,
    timeout=60
)

return r.json()
```

def solve_sha256_empty():
h = hashlib.sha256(b"").hexdigest()
return h[:6]

def solve_base64(prompt):
matches = re.findall(r"['"](.*?)['"]", prompt)

```
if not matches:
    return None

try:
    return base64.b64decode(matches[0]).decode()
except:
    return None
```

def solve_reverse(prompt):
matches = re.findall(r"['"](.*?)['"]", prompt)

```
if not matches:
    return None

return matches[0][::-1]
```

def solve_math(prompt):
expression = re.findall(r"([0-9+-*/() ]+)", prompt)

```
if not expression:
    return None

try:
    return str(eval(expression[0]))
except:
    return None
```

def ask_gemini(prompt):
if not model:
return None

```
try:
    response = model.generate_content(
        f"""
```

You are a cryptographic puzzle solving AI.

Return ONLY the final answer.
No explanation.

Puzzle:
{prompt}
"""
)

```
    return response.text.strip().lower()

except Exception as e:
    print("[gemini error]", e)
    return None
```

def solve_puzzle(puzzle):
prompt = puzzle["prompt"]
prompt_lower = prompt.lower()

```
print("[puzzle]", prompt)

if prompt in cache:
    print("[cache] Using cached answer")
    return cache[prompt]

answer = None

if "sha-256 hash of the empty string" in prompt_lower:
    answer = solve_sha256_empty()

elif "base64" in prompt_lower:
    answer = solve_base64(prompt)

elif "reverse" in prompt_lower:
    answer = solve_reverse(prompt)

elif any(x in prompt_lower for x in [
    "calculate",
    "+",
    "-",
    "*",
    "/"
]):
    answer = solve_math(prompt)

if not answer:
    print("[ai] Using Gemini AI...")
    answer = ask_gemini(prompt)

if answer:
    answer = str(answer).strip().lower()

    cache[prompt] = answer
    save_cache()

return answer
```

def submit_answer(puzzle_id, answer):
payload = {
"eth_address": WALLET,
"agent_name": AGENT,
"puzzle_id": puzzle_id,
"answer": answer
}

```
r = requests.post(
    API_URL,
    headers=headers,
    json=payload,
    timeout=60
)

return r.json()
```

print("[miner] Smart solver started.")

while True:
try:
data = get_puzzle()

```
    puzzle = data.get("puzzle")

    if not puzzle:
        print("[miner] No puzzle available...")
        time.sleep(30)
        continue

    answer = solve_puzzle(puzzle)

    if not answer:
        print("[solver] Could not solve puzzle")
        time.sleep(10)
        continue

    print("[answer]", answer)

    result = submit_answer(
        puzzle["id"],
        answer
    )

    print("[submit]", result)

    if result.get("correct"):
        print("[reward] SUCCESS +500 NTC")
    else:
        print("[reward] Wrong answer")

    time.sleep(5)

except Exception as e:
    print("[error]", e)
    time.sleep(15)

