import json
import time
from datetime import datetime

import jwt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from redis import asyncio as aioredis
from starlette_discord import DiscordOAuthClient

from config import (
    ALGORITHM,
    CLIENT_ID,
    CLIENT_SECRET,
    DATABASE_NAME,
    DATABASE_URI,
    DBL_TOKEN,
    KOFI_TOKEN,
    REDIRECT_URL,
    REDIS_URL,
    SECRET,
)

app = FastAPI()

discord = DiscordOAuthClient(
    CLIENT_ID, CLIENT_SECRET, REDIRECT_URL, ("identify", "email")
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[REDIRECT_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Databases
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
redis = None


def verify_dbl_auth(req: Request):
    token = req.headers["Authorization"]

    if token != DBL_TOKEN:
        raise HTTPException(401)

    return req


async def verify_kofi_auth(req: Request):
    form_data = await req.form()

    data = get_data_from_form(form_data)

    if data is None:
        raise HTTPException(401)

    if data.get("verification_token", None) != KOFI_TOKEN:
        raise HTTPException(401)

    return req


def get_data_from_form(form_data):
    data = str(form_data.get("data", None))

    return json.loads(data)


@app.on_event("startup")
async def startup_event():
    global redis  # thomas doesn't like globals :(
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

    expire_time = int(time.time() + 60 * 60 * 24 * 32)  # giving an extra day

    await db.subscriptions.insert_one(
        {
            "_id": data["message_id"],
            "email": data["email"],
            "name": data["from_name"],
            "tier": data["tier_name"],
            "first_time": data["is_first_subscription_payment"],
            "activated_by": None,
            "expired": False,
            "expire_time": expire_time,
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


@app.get("/login")
async def start_login():
    return discord.redirect()


@app.get("/token")
async def callback(code: str):
    user = await discord.login(code)

    payload = {
        "id": user.id,
    }

    jwt_token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)

    return JSONResponse({"token": jwt_token})


@app.get("/user")
async def get_user(token: str):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(401)

    user = await db.users.find_one({"_id": payload["id"]})

    if user is None:
        raise HTTPException(404)

    user_data = {
        "id": str(user["_id"]),
        "name": user["name"],
        "discriminator": user["discriminator"],
        "avatar": user["avatar"],
    }

    return JSONResponse(user_data)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
