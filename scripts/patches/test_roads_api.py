import requests

payload = {
    "generate_roads": False,
    "seed": 1234
}

try:
    res = requests.post("http://localhost:8000/api/generate", json=payload)
    data = res.json()
    manifest = data.get("manifest", {})
    roads = manifest.get("roads", [])
    print(f"Roads generated: {len(roads)}")
except Exception as e:
    print(f"Error: {e}")
