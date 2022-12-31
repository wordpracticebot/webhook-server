import json
from datetime import datetime

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient
from redis import asyncio as aioredis

from config import DATABASE_NAME, DATABASE_URI, DBL_TOKEN, KOFI_TOKEN, REDIS_URL

app = FastAPI()

# Databases
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
redis = None


def verify_dbl_auth(req: Request):
    token = req.headers["Authorization"]

    if token != DBL_TOKEN:
        raise HTTPException(401)

    return req


def get_data_from_form(form_data):
    data = str(form_data.get("data", None))

    return json.loads(data)


async def verify_kofi_auth(req: Request):
    form_data = await req.form()

    data = get_data_from_form(form_data)

    if data is None:
        raise HTTPException(401)

    if data.get("verification_token", None) != KOFI_TOKEN:
        raise HTTPException(401)

    return req


@app.on_event("startup")
async def startup_event():
    global redis
    redis = await aioredis.from_url(REDIS_URL, socket_timeout=10, max_connections=2)


@app.on_event("shutdown")
async def shutdown_event():
    await redis.close()


@app.get("/")
def main():
    return "Thomas is ready!"


@app.post("/premium")
async def premium(request: Request = Depends(verify_kofi_auth)):
    data = get_data_from_form(await request.form())

    if data["type"] != "Subscription":
        raise HTTPException(401)

    await db.premium.insert_one(
        {
            "_id": "c1b6754f-b43d-454b-97b2-423876716273",
            "email": data["email"],
            "name": data["from_name"],
            "tier": data["tier_name"],
            "first_time": data["is_first_subscription_payment"],
        }
    )

    return "Thomas is very happy!"


@app.post("/vote")
async def vote(request: Request = Depends(verify_dbl_auth)):
    data = await request.json()

    # Getting the user id from the request
    if "id" in data:
        user_id = data["id"]
        site = "dbls"
    elif "user" in data:
        user_id = data["user"]
        if "guild" in data:
            site = "topgg-server"
        else:
            site = "topgg"
    else:
        raise HTTPException(400)

    user_id = int(user_id)

    user = await db.users.find_one({"_id": user_id})

    if user is None:
        raise HTTPException(400)

    votes = user["votes"] + 1
    now = datetime.utcnow()

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"votes": votes, f"last_voted.{site}": now}, "$inc": {"xp": 750}},
    )
    await redis.hdel("user", user["_id"])

    return "Thomas is happy!"


uvicorn.run(app, host="0.0.0.0", port=8080)
