import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.deploy.api import app
from backend.deploy.config import settings

EMAIL = f"systest_{int(time.time())}@example.com"
PASSWORD = "TestPass123!"
PATIENT_ID = f"TEST-{int(time.time())}"

results = {}

print("=" * 70)
print("END-TO-END HTTP TEST (real app + real MongoDB Atlas + real model)")
print("=" * 70)

with TestClient(app) as client:
    # 1) health
    r = client.get("/health")
    results["health"] = (r.status_code, r.json())
    print(f"1) GET /health                 -> {r.status_code} {r.json()}")

    # 2) register a fresh doctor
    r = client.post("/api/auth/register", json={"email": EMAIL, "password": PASSWORD, "role": "doctor"})
    results["register"] = (r.status_code, r.json())
    print(f"2) POST /api/auth/register     -> {r.status_code} {r.json()}")

    # 3) login
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    results["login"] = r.status_code
    print(f"3) POST /api/auth/login        -> {r.status_code}")
    if r.status_code != 200:
        print("   LOGIN FAILED:", r.text)
        raise SystemExit("ABORT: login failed")
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 4) create patient
    patient_payload = {
        "patient_id": PATIENT_ID,
        "age": 45,
        "gender": "male",
        "bmi": 28.0,
        "mallampati": "Class II",
        "tmd": 7.0,
        "neck_circumference": 40.0,
    }
    r = client.post("/api/patients", json=patient_payload, headers=headers)
    results["create_patient"] = (r.status_code, r.json())
    print(f"4) POST /api/patients          -> {r.status_code} {r.json()}")

    # 5) predict (full model output + LLM summary/recommendations)
    predict_payload = {
        "patient_id": PATIENT_ID,
        "age": 45,
        "gender": "male",
        "bmi": 28.0,
        "mallampati_score": 2,
        "tmd": 7.0,
        "neck_circumference": 40.0,
        "mouth_opening": 40.0,
        "smd": 16.0,
        "neck_movement": 80.0,
    }
    t0 = time.time()
    r = client.post("/api/predictions", json=predict_payload, headers=headers)
    elapsed = time.time() - t0
    results["predict"] = (r.status_code, r.json())
    print(f"5) POST /api/predictions       -> {r.status_code}  ({elapsed:.1f}s)")
    if r.status_code == 200:
        body = r.json()
        pred = body["prediction"]
        print(f"     prediction       : {pred['prediction']}  (confidence {pred['confidence']})")
        print(f"     probabilities    : {pred['probabilities']}")
        print(f"     risk_score       : {pred['risk_score']}")
        print(f"     clinical_summary :")
        for line in body["clinical_summary"].splitlines():
            print(f"        {line}")
        print(f"     recommendations  :")
        for line in body["recommendations"].splitlines():
            print(f"        {line}")
        print(f"     report_sources   : {body['report_sources']}")
    else:
        print("     PREDICTION FAILED:", r.text)

print()
print("=" * 70)
print("CLEANUP (remove test user/patient/prediction from Atlas)")
print("=" * 70)


async def cleanup():
    from motor.motor_asyncio import AsyncIOMotorClient
    c = AsyncIOMotorClient(settings.mongo_url, serverSelectionTimeoutMS=8000)
    db = c[settings.mongo_db]
    d1 = await db.patients.delete_many({"patient_id": PATIENT_ID})
    d2 = await db.predictions.delete_many({"patient_id": PATIENT_ID})
    d3 = await db.users.delete_many({"email": EMAIL})
    d4 = await db.llm_reports.delete_many({"prediction_id": PATIENT_ID})
    d5 = await db.audit_logs.delete_many({"actor": EMAIL})
    print(f"  deleted patients={d1.deleted_count}, predictions={d2.deleted_count}, "
          f"users={d3.deleted_count}, llm_reports={d4.deleted_count}, audit_logs={d5.deleted_count}")
    c.close()


asyncio.run(cleanup())

print()
print("=" * 70)
ok = results.get("health", (0,))[0] == 200 and results.get("register", (0,))[0] == 201 \
     and results.get("login", 0) == 200 and results.get("create_patient", (0,))[0] == 201 \
     and results.get("predict", (0,))[0] == 200
print("END-TO-END RESULT:", "ALL PASSED" if ok else "SOMETHING FAILED")
print("=" * 70)
