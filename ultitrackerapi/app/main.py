"""API Definitions for ultitracker."""
import boto3
import datetime
import logging
import os
import tempfile
import time

from fastapi import Depends, FastAPI, HTTPException, File, Form, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, Response, RedirectResponse
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
from typing import Optional

from ultitrackerapi import auth, db, models, video

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

# start s3 client
s3Client = boto3.client("s3")

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
    user = models.UserInDB(
        username=auth.sanitize_for_html(userform.username),
        salted_password=salted_password,
        email=auth.sanitize_for_html(userform.email),
        full_name=auth.sanitize_for_html(userform.full_name),
    )
    is_success = auth.add_user(user)
    return is_success


@app.post("/renew_token")
async def renew_access_token(
    current_user: models.User = Depends(auth.get_current_active_user),
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
    current_user: models.User = Depends(auth.get_current_active_user),
):
    return current_user


@app.get("/get_game_list", response_model=db.GameListResponse)
async def get_game_list(
    current_user: models.User = Depends(auth.get_current_active_user),
):
    return db.get_game_list(current_user)


@app.get("/get_game", response_model=Optional[db.GameResponse])
async def get_game(
    game_id: str,
    current_user: models.User = Depends(auth.get_current_active_user),
):
    result = db.get_game(game_id=game_id, user=current_user)
    if not result:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail="GameId not found"
        )
    else:
        return result


@app.post("/upload_file")
async def upload_file(
    current_user: models.User = Depends(auth.get_current_active_user),
    upload_file: UploadFile = File(...),
    name: str = Form(...),
    home: str = Form(...),
    away: str = Form(...),
    date: str = Form(...)
):
    _, new_filename = tempfile.mkstemp()
    print("New filename: {}".format(new_filename))
    print("home, away, date: {}, {}, {}".format(home, away, date))
    time.sleep(0.1)

    chunk_size = 10000
    with open(new_filename, "wb") as f:
        for chunk in iter(lambda: upload_file.file.read(chunk_size), b''):
            f.write(chunk)

    thumbnail_name = new_filename + "_thumbnail.jpg"
    video.get_thumbnail(new_filename, thumbnail_name)
    video_length = str(datetime.timedelta(seconds=int(video.get_video_duration(new_filename))))

    s3Client.upload_file(
        new_filename,
        "ultitracker-videos-test",
        os.path.basename(new_filename)
    )

    s3Client.upload_file(
        thumbnail_name,
        "ultitracker-videos-test",
        os.path.basename(thumbnail_name)
    )

    os.remove(new_filename)
    os.remove(thumbnail_name)

    db.add_game(
        current_user,
        game_id=os.path.basename(new_filename),
        data={
            "name": name,
            "home": home,
            "away": away,
            "date": date,
            "bucket": "ultitracker-videos-test",
            "thumbnail_key": os.path.basename(thumbnail_name),
            "video_key": os.path.basename(new_filename),
            "length": video_length
        }
    )

    return {"finished": True}
