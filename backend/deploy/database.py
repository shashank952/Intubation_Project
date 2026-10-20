from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime, timezone
from .config import settings

client: AsyncIOMotorClient = None


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.mongo_url)


async def close_db():
    global client
    if client:
        client.close()


def get_db() -> AsyncIOMotorDatabase:
    return client[settings.mongo_db]


async def audit_log(
    db: AsyncIOMotorDatabase,
    actor: str,
    action: str,
    resource: str,
    resource_id: str = "",
    detail: str = "",
) -> None:
    await db.audit_logs.insert_one({
        "actor": actor,
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "detail": detail,
        "created_at": datetime.now(timezone.utc),
    })


async def ensure_indexes():
    db = get_db()
    await db.patients.create_index("patient_id", unique=True)
    await db.predictions.create_index([("patient_id", 1), ("created_at", -1)])
    await db.users.create_index("email", unique=True)
    await db.llm_reports.create_index([("prediction_id", 1)])
    await db.patients.create_index([("owner_id", 1), ("created_at", -1)])
    await db.predictions.create_index([("owner_id", 1), ("created_at", -1)])
    await db.audit_logs.create_index([("created_at", -1)])
