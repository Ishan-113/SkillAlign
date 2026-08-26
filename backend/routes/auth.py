import hashlib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.mongodb import get_db

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


@router.post("/register")
async def register(user: UserCreate):
    db = get_db()
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    result = await db.users.insert_one({
        "username": user.username,
        "email": user.email,
        "password_hash": hash_password(user.password),
        "role": "user",
    })

    return {"message": "User registered successfully", "user_id": str(result.inserted_id), "username": user.username}


@router.post("/login")
async def login(user: UserLogin):
    db = get_db()
    found = await db.users.find_one({
        "email": user.email,
        "password_hash": hash_password(user.password),
    })

    if not found:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {
        "message": "Login successful",
        "user_id": str(found["_id"]),
        "username": found["username"],
        "role": found.get("role", "user"),
    }


@router.get("/users")
async def get_users():
    db = get_db()
    users = await db.users.find({}, {"password_hash": 0, "_id": 0}).to_list(length=None)
    return {"users": users}
