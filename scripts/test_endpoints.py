import requests
import json
import time

BASE = 'http://127.0.0.1:5000'

sample_text = (
    "ACME P2P Ltd is building a peer-to-peer payments network. We do not yet have a deployed monitoring system; "
    "Our policy retains certain records for 7 years. Paid-Up Capital: QAR 1,000,000. Data stored in Qatar. "
    "We have a compliance officer and a board-approved AML policy. AoA: signed."
)

print('Waiting 1s for server warmup...')
time.sleep(1)

payload = {"full_startup_text": sample_text}

print('\nPOST /api/map_startup_data')
try:
    r = requests.post(BASE + '/api/map_startup_data', json=payload, timeout=10)
    print('Status:', r.status_code)
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print('Error calling map_startup_data:', e)

print('\nPOST /api/scorecard')
try:
    r = requests.post(BASE + '/api/scorecard', json=payload, timeout=10)
    print('Status:', r.status_code)
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print('Error calling scorecard:', e)
