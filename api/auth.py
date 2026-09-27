import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONFIG
# =========================================================

JWT_SECRET = os.getenv(
    "TRAVELOPS_JWT_SECRET",
    "CHANGE_THIS_SECRET_BEFORE_DEPLOYMENT"
)

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 8 * 60


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password: str, salt: Optional[str] = None):

    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    )

    return f"{salt}${hashed.hex()}"


def verify_password(password: str, stored_hash: str):

    try:
        salt, expected_hash = stored_hash.split("$", 1)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120000,
        ).hex()

        return secrets.compare_digest(
            actual_hash,
            expected_hash
        )

    except Exception:
        return False


# =========================================================
# DEMO USERS
# =========================================================

def get_users():

    return {
        "ops@travelops360.com": {
            "email": "ops@travelops360.com",
            "role": "operator",
            "password": os.getenv(
                "TRAVELOPS_OPS_PASSWORD",
                "TravelOps@123"
            ),
        },

        "admin@travelops360.com": {
            "email": "admin@travelops360.com",
            "role": "admin",
            "password": os.getenv(
                "TRAVELOPS_ADMIN_PASSWORD",
                "Admin@123"
            ),
        },
    }


# =========================================================
# LOGIN REQUEST
# =========================================================

class LoginRequest(BaseModel):

    email: str
    password: str


# =========================================================
# TOKEN
# =========================================================

def create_access_token(
    email: str,
    role: str
):

    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=JWT_EXPIRATION_MINUTES
    )

    payload = {
        "sub": email,
        "role": role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def decode_access_token(token: str):

    try:

        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Session expired. Please login again."
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token."
        )


# =========================================================
# AUTHENTICATE REQUEST
# =========================================================

def authenticate_request(request: Request):

    authorization = request.headers.get(
        "Authorization"
    )

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authentication required."
        )

    if not authorization.startswith("Bearer "):

        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header."
        )

    token = authorization.split(
        " ",
        1
    )[1]

    payload = decode_access_token(token)

    request.state.user = payload

    return payload


# =========================================================
# ROLE CHECK
# =========================================================

def require_role(request: Request, allowed_roles):

    user = authenticate_request(request)

    role = user.get("role")

    if role not in allowed_roles:

        raise HTTPException(
            status_code=403,
            detail="You do not have permission for this operation."
        )

    return user