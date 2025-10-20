import urllib.request, urllib.parse, urllib.error

BASE = "http://localhost:8080"

def ping_success():
    r = urllib.request.urlopen(f"{BASE}/robokassa/success")
    print("success:", r.status, r.read().decode()[:120])

def ping_result():
    data = urllib.parse.urlencode({
        "OutSum":"1.00",
        "InvId":"123",
        "SignatureValue":"deadbeef"
    }).encode()
    req = urllib.request.Request(f"{BASE}/robokassa/result", data=data, method="POST")
    try:
        r = urllib.request.urlopen(req)
        print("result:", r.status, r.read().decode()[:120])
    except urllib.error.HTTPError as e:
        print("result:", e.code, e.read().decode()[:120])

if __name__ == "__main__":
    ping_success()
    ping_result()
