from fastapi import Form
from pydantic import BaseModel
from typing import List

ALGORITHM = "HS256"


# NOTE: Header and Payload information is readable by everyone
class Header(BaseModel):
    alg: str = ALGORITHM
    typ: str = "JWT"


class Payload(BaseModel):
    exp: int
    iat: int
    iss: str = None
    sub: str = None
    aud: List[str] = []
    nbf: int = None


class User(BaseModel):
    username: str
    email: str = None
    full_name: str = None
    disabled: bool = None


class UserInDB(User):
    salted_password: str


class UserForm:
    def __init__(
        self,
        username: str = Form(...),
        password: str = Form(...),
        email: str = Form(...),
        full_name: str = Form(...),
    ):
        self.username = username
        self.password = password
        self.email = email
        self.full_name = full_name


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str = None
