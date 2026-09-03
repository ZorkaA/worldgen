import requests

try:
    res = requests.post("http://localhost:8000/api/generate", json={"seed": 42})
    print(res.status_code)
except Exception as e:
    print("Error:", e)
