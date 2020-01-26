"""API Definitions for ultitracker."""
# import boto3
# import datetime
# import logging
import os
import subprocess
import tempfile
import time
import uuid

# # initialize ultitracker
# import ultitrackerapi

from fastapi import Depends, FastAPI, HTTPException, File, Form, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.cors import CORSMiddleware
# from starlette.requests import Request
from starlette.responses import Response
# from starlette.responses import FileResponse, Response, RedirectResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
from typing import Optional

from ultitrackerapi import auth, get_backend, get_logger, get_s3Client, models, video

CORS_ORIGINS = ["http://localhost:3000"]

# sleep just to make sure the above happened
time.sleep(1)

app = FastAPI()

# allow cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    expose_headers=[""]
    # allow_origins=origins
    # allow_origins=origins,
    # allow_credentials=True,
    # allow_methods=["POST"],
    # allow_headers=["*"],
)

# # start s3 client
# s3Client = boto3.client("s3")

backend_instance = get_backend()
s3Client = get_s3Client()
logger = get_logger(__name__, "DEBUG")


@app.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = auth.authenticate_user(
        auth.sanitize_for_html(form_data.username), form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.construct_jwt(username=user.username)

    response = Response()

    response.set_cookie(
        key="ultitracker-api-access-token",
        value=access_token,
        expires=auth.EXP_LENGTH.total_seconds(),
    )
    return response


@app.post("/add_user")
async def add_user(userform: models.UserForm = Depends()):
    salted_password = auth.get_password_hash(userform.password)
    user = models.User(
        username=auth.sanitize_for_html(userform.username),
        email=auth.sanitize_for_html(userform.email),
        full_name=auth.sanitize_for_html(userform.full_name),
    )

    is_success = backend_instance.add_user(
        user, salted_password=salted_password)

    if is_success:
        return is_success
    else:
        raise HTTPException(status_code=400, detail="User already exists")


@app.post("/renew_token")
async def renew_access_token(
    current_user: models.User = Depends(auth.get_user_from_cookie),
):
    access_token = auth.construct_jwt(username=current_user.username)
    response = Response()
    response.set_cookie(
        key="ultitracker-api-access-token",
        value=access_token,
        expires=auth.EXP_LENGTH.total_seconds(),
    )
    return response


@app.get("/users/me", response_model=models.User)
async def get_user_info(
    current_user: models.User = Depends(auth.get_user_from_cookie),
):
    return current_user


@app.get("/get_game_list", response_model=models.GameListResponse)
async def get_game_list(
    current_user: models.User = Depends(auth.get_user_from_cookie),
):
    return backend_instance.get_game_list(current_user)


@app.get("/get_game", response_model=Optional[models.GameResponse])
async def get_game(
    game_id: str,
    current_user: models.User = Depends(auth.get_user_from_cookie),
):
    result = backend_instance.get_game(game_id=game_id, user=current_user)
    if not result:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, 
            detail="GameId not found"
        )
    else:
        return result


@app.post("/upload_file")
async def upload_file(
    current_user: models.User = Depends(auth.get_user_from_cookie),
    upload_file: UploadFile = File(...),
    name: str = Form(...),
    home: str = Form(...),
    away: str = Form(...),
    date: str = Form(...),
):
    _, local_video_filename = tempfile.mkstemp()
    game_id = str(uuid.uuid4())

    logger.debug("Local video filename: {}".format(local_video_filename))
    logger.debug("home, away, date: {}, {}, {}".format(home, away, date))
    logger.debug("game_id: {}".format(game_id))
    
    time.sleep(0.1)

    chunk_size = 10000
    with open(local_video_filename, "wb") as f:
        for chunk in iter(lambda: upload_file.file.read(chunk_size), b""):
            f.write(chunk)

    thumbnail_filename = local_video_filename + "_thumbnail.jpg"

    bucket = "ultitracker-videos-test"
    video_key = os.path.basename(local_video_filename)
    thumbnail_key = os.path.basename(thumbnail_filename)
    
    subprocess.Popen([
        "python", "-m", 
        "ultitrackerapi.extract_and_upload_video",
        bucket,
        local_video_filename,
        thumbnail_filename,
        video_key,
        thumbnail_key,
        game_id
    ])

    backend_instance.add_game(
        current_user,
        game_id=game_id,
        thumbnail_key=thumbnail_key,
        video_key=video_key,
        data={
            "name": name,
            "home": home,
            "away": away,
            "date": date,
            "bucket": bucket,
            # "length": video_length,
        },
    )

    return {"finished": True}
