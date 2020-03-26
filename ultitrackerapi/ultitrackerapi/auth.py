"""Schemas and functions for handling authentication."""
import bleach

from authlib.jose import jwt
from authlib.jose.errors import DecodeError, ExpiredTokenError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Cookie
from fastapi.security import OAuth2PasswordBearer
from passlib.hash import pbkdf2_sha256
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED

from ultitrackerapi import ULTITRACKER_AUTH_SECRET_KEY, ULTITRACKER_AUTH_TOKEN_EXP_LENGTH, ULTITRACKER_COOKIE_KEY, ULTITRACKER_URL, models, get_backend, get_logger


EXP_LENGTH = timedelta(seconds=ULTITRACKER_AUTH_TOKEN_EXP_LENGTH)
LOGGER = get_logger(__name__)

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
        iss=ULTITRACKER_URL,
        exp=(datetime.utcnow() + EXP_LENGTH).timestamp(),
        iat=datetime.utcnow().timestamp(),
        sub=username,
        nbf=datetime.utcnow().timestamp(),
    ).dict()

    encoded_bytes_token = jwt.encode(
        header=header, 
        payload=payload, 
        key=ULTITRACKER_AUTH_SECRET_KEY
    )
    encoded_unicode_token = encoded_bytes_token.decode()

    return encoded_unicode_token


async def get_user_from_cookie(request: Request):
    token = request.cookies.get(ULTITRACKER_COOKIE_KEY)
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

    if token is None:
        raise credentials_exception
    
    try:
        claims = jwt.decode(token, ULTITRACKER_AUTH_SECRET_KEY)
        try:
            claims.validate(now=datetime.utcnow().timestamp())
        except ExpiredTokenError:
            raise timeout_exception

        LOGGER.info(f"claims: {claims}")
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
        return

    if not verify_password(password, user.salted_password):
        return

    return user