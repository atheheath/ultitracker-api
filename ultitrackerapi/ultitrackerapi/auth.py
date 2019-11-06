"""Schemas and functions for handling authentication."""
import bleach

from authlib.jose import jwt
from authlib.jose.errors import DecodeError, ExpiredTokenError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import pbkdf2_sha256
from starlette.status import HTTP_401_UNAUTHORIZED
from typing import Dict

from ultitrackerapi import db, models

SECRET_KEY = "secret"
EXP_LENGTH = timedelta(seconds=60)

DB = Dict[str, models.UserInDB]

user_db: DB = {
    "test": models.UserInDB(
        username="test",
        email="test@test.com",
        full_name="Jane Doe",
        salted_password=pbkdf2_sha256.hash("test")
    )
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def verify_password(password, salted_password):
    return pbkdf2_sha256.verify(password, salted_password)


def get_password_hash(password):
    return pbkdf2_sha256.hash(password)


def sanitize_for_html(string):
    return bleach.clean(string)


def is_valid_username(username: str) -> bool:
    return username in user_db


def construct_jwt(username: str) -> str:
    # we need to use dict here so that jwt can use encode
    header = models.Header().dict()
    payload = models.Payload(
        iss="https://ultitracker.com",
        exp=(datetime.utcnow() + EXP_LENGTH).timestamp(),
        iat=datetime.utcnow().timestamp(),
        sub=username,
    ).dict()

    encoded_bytes_token = jwt.encode(
        header=header, payload=payload, key=SECRET_KEY)
    encoded_unicode_token = encoded_bytes_token.decode()

    return encoded_unicode_token


def get_user(username: str):
    return user_db.get(username, None)


def authenticate_user(username: str, password: str):
    user = get_user(username=username)
    if not user:
        return False

    if not verify_password(password, user.salted_password):
        return False

    return user


def add_user(user: models.UserInDB):
    if user.username in user_db:
        raise HTTPException(status_code=400, detail="User already exists")

    user.disabled = False

    user_db.update({user.username: user})
    db.initialize_user(user)

    return True


def decode_payload(payload: Dict[str, str]) -> dict:
    return {"decoded": "payload"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    timeout_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Token expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        claims = jwt.decode(token, SECRET_KEY)
        try:
            claims.validate(now=datetime.utcnow().timestamp())
        except ExpiredTokenError:
            raise timeout_exception

        username: str = claims.get("sub")

        if username is None:
            raise credentials_exception

        token_data = models.TokenData(username=username)

    except DecodeError:
        raise credentials_exception

    user = get_user(username=token_data.username)

    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
