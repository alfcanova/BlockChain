import os
os.environ.setdefault("BLOCKCHAIN_DB", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "__smoke_au.db"))
from fastapi.testclient import TestClient
import web_app
from web_app import registry, au_chains, app

with TestClient(app) as c:
    print("AU_SMOKE chains:", sorted(au_chains))
    print("AU_SMOKE registry arvore raizes:", sorted(registry.filhos_de("@")))
    r = c.post("/api/auth/login", json={"username": "admin01", "password": "@dmin01BR"})
    print("AU_SMOKE login admin01:", r.status_code)
    if r.status_code == 200:
        tok = r.json()["data"]["token"]
        h = {"Authorization": f"Bearer {tok}"}
        r2 = c.post("/api/au", json={
            "nome": "Autoridade UF", "nivel": 1, "escopo": "pf",
            "uf": "SP", "cidade": "", "data": "", "motivo": "seed teste",
        }, headers=h)
        print("AU_SMOKE criar N1:", r2.status_code, r2.text[:200])
