"""Schemas and functions for handling authentication."""
import bleach

from authlib.jose import jwt
from authlib.jose.errors import DecodeError, ExpiredTokenError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import pbkdf2_sha256
from starlette.status import HTTP_401_UNAUTHORIZED

from ultitrackerapi import models, get_backend

SECRET_KEY = "secret"
EXP_LENGTH = timedelta(seconds=3600)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
backend_instance = get_backend()


def verify_password(password, salted_password):
    return pbkdf2_sha256.verify(password, salted_password)


def get_password_hash(password):
    return pbkdf2_sha256.hash(password)


def sanitize_for_html(string):
    return bleach.clean(string)


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
        header=header, 
        payload=payload, 
        key=SECRET_KEY
    )
    encoded_unicode_token = encoded_bytes_token.decode()

    return encoded_unicode_token


async def get_user_from_cookie(token: str = Depends(oauth2_scheme)):
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

    user = backend_instance.get_user(username=token_data.username)

    if user is None:
        raise credentials_exception
    return user


def authenticate_user(username: str, password: str) -> models.UserInDBwPass:
    user = backend_instance.get_user(username=username, include_password=True)
    if not user:
        return False

    if not verify_password(password, user.salted_password):
        return False

    return user