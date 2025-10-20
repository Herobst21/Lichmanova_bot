SHELL := /bin/bash
.ONESHELL:
.RECIPEPREFIX := >

.PHONY: health rk-env rk-result-ok

health:
> docker compose exec -T app-web sh -lc 'curl -sS http://127.0.0.1:8080/health; echo'

rk-env:
> docker compose exec -T app-web sh -lc 'curl -sS http://127.0.0.1:8080/robokassa/_env; echo'

rk-result-ok:
> set -euo pipefail
> SIG=$(docker compose exec -T app-web python - <<'PY'
import os,hashlib
login=os.getenv("ROBOKASSA_LOGIN",""); p2=os.getenv("ROBOKASSA_PASSWORD2","")
out_sum="123.45"; inv_id="42"; shp={"Shp_plan":"m1","Shp_user":"u1"}
base=f"{login}:{out_sum}:{inv_id}:{p2}"
for k,v in sorted(shp.items()):
    base+=f":{k}={v}"
print(hashlib.sha256(base.encode()).hexdigest())
PY
)
> docker compose exec -T app-web sh -lc "curl -sS -i -X POST http://127.0.0.1:8080/robokassa/result -H 'Content-Type: application/x-www-form-urlencoded' --data 'OutSum=123.45&InvId=42&SignatureValue=$$SIG&Shp_user=u1&Shp_plan=m1'; echo"
