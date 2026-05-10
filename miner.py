import requests
import time

API_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxcmFwbmxxcXRqZWRqeWhsZmNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyNzUyNjQsImV4cCI6MjA5Mzg1MTI2NH0.mf0fz6kAnK0yeAXrb-XT6yikbdRmeAq5jsikVPPhaFE"

WALLET = "0xe8b85a40c81545fdc607f3ee5efe53fd0ab3dc34"
AGENT = "variz"

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

def get_puzzle():
    url = f"{API_URL}?eth={WALLET}"
    r = requests.get(url, headers=headers)
    return r.json()

while True:
    try:
        data = get_puzzle()

        puzzle = data.get("puzzle")

        if not puzzle:
            print("No puzzle. Waiting...")
            time.sleep(30)
            continue

        print("Puzzle:", puzzle)

        # TEMP ANSWER
        answer = "test"

        payload = {
            "eth_address": WALLET,
            "agent_name": AGENT,
            "puzzle_id": puzzle["id"],
            "answer": answer
        }

        r = requests.post(API_URL, headers=headers, json=payload)

        print(r.text)

        time.sleep(5)

    except Exception as e:
        print(e)
        time.sleep(10)
