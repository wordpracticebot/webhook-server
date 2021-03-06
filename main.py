from datetime import datetime

import aioredis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient

from config import DATABASE_NAME, DATABASE_URI, DBL_TOKEN, REDIS_URL

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


@app.post("/vote")
async def vote(request: Request = Depends(verify_dbl_auth)):
    data = await request.json()

    # Getting the user id from the request
    if "id" in data:
        user_id = data["id"]
        site = "dbls"
    elif "user" in data:
        user_id = data["user"]
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
        {"$set": {"votes": votes, f"last_voted.{site}": now}, "$inc": {"xp": 1000}},
    )
    await redis.hdel("user", user["_id"])

    return "Thomas is happy!"


uvicorn.run(app, host="0.0.0.0", port=8080)
