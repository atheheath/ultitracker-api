"""API Definitions for ultitracker."""
import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse
from starlette.status import HTTP_401_UNAUTHORIZED

from ultitrackerapi import auth

CORS_ORIGINS = ["*"]

# sleep just to make sure the above happened
time.sleep(1)

app = FastAPI()

# allow cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    # allow_origins=origins
    # allow_origins=origins,
    # allow_credentials=True,
    # allow_methods=["POST"],
    # allow_headers=["*"],
)


@app.post("/token", response_model=auth.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = auth.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.construct_jwt(username=user.username)
    return {"access_token": access_token, "token_type": "Bearer"}


@app.post("/add_user")
async def add_user(userform: auth.UserForm = Depends()):
    salted_password = auth.get_password_hash(userform.hashed_password)
    user = auth.UserInDB(
        username=userform.username,
        salted_password=salted_password,
        email=userform.email,
        full_name=userform.full_name,
        disabled=userform.disabled,
    )
    is_success = auth.add_user(user)
    return is_success


@app.get("/users/me", response_model=auth.User)
async def get_user_info(
    current_user: auth.User = Depends(auth.get_current_active_user)
):
    return current_user
