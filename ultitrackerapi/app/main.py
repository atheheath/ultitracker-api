"""API Definitions for ultitracker."""
# import boto3
# import logging
import datetime
import os
import posixpath
import psycopg2 as psql
import subprocess
import tempfile
import time
import uuid

from fastapi import Cookie, Depends, FastAPI, HTTPException, File, Form, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
from typing import List, Optional

from ultitrackerapi import CORS_ORIGINS, S3_BUCKET_NAME, ULTITRACKER_COOKIE_KEY, annotator_queue, auth, get_backend, get_logger, get_s3Client, models, sql_models, video

# sleep just to make sure the above happened
time.sleep(1)

backend_instance = get_backend()
s3Client = get_s3Client()
logger = get_logger(__name__, "DEBUG")


try:
    backend_instance.client._establish_connection()

except psql.DatabaseError as e:
    logger.error("main: Couldn't connect to database. Aborting")
    raise e

logger.info("CORS_ORIGINS: {}".format(CORS_ORIGINS))

app = FastAPI()

# allow cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    expose_headers=[""]
)


@app.get("/")
async def return_welcome():
    return {"message": "Welcome"}

    
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
        key=ULTITRACKER_COOKIE_KEY,
        value=access_token,
        expires=auth.EXP_LENGTH.total_seconds(),
    )
    return response


@app.post("/logout")
async def logout_from_token(
    user: models.User = Depends(auth.get_user_from_cookie)
):
    response = Response()
    response.set_cookie(
        key=ULTITRACKER_COOKIE_KEY,
        value="",
        expires=-1
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
        key=ULTITRACKER_COOKIE_KEY,
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

    video_key = posixpath.join(game_id, "video.mp4")
    thumbnail_key = posixpath.join(game_id, "thumbnail.jpg")
    
    logger.info("Submitting extract video job")
    subprocess.Popen([
        "python", "-m", 
        "ultitrackerapi.extract_and_upload_video",
        S3_BUCKET_NAME,
        local_video_filename,
        thumbnail_filename,
        video_key,
        thumbnail_key,
        game_id
    ])

    logger.info("Adding game to DB")
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
            "bucket": S3_BUCKET_NAME,
            # "length": video_length,
        },
    )

    return {"finished": True}


@app.post("/annotator/get_images_to_annotate", response_model=models.ImgLocationListResponse)
async def get_images_to_annotate(
    current_user: models.User = Depends(auth.get_user_from_cookie),
    game_ids: str = Form(...),
    annotation_type: str = Form(...),
    order_type: str = Form(...)
):
    queue_params = annotator_queue.AnnotatorQueueParams(
        game_ids=game_ids.split(),
        annotation_type=models.AnnotationTable[annotation_type],
        order_type=annotator_queue.AnnotationOrderType[order_type]
    )

    images = annotator_queue.get_next_n_images(
        backend=backend_instance, 
        queue_params=queue_params
    )

    return images


@app.post("/annotator/insert_annotation")
async def insert_annotation(
    img_id: str,
    annotation_table: str,
    annotation: dict,
    current_user: models.User = Depends(auth.get_user_from_cookie),
):
    try:
        backend_instance.insert_annotation(
            user=current_user,
            img_id=img_id,
            annotation_table=models.AnnotationTable[annotation_table],
            annotation_data=annotation
        )
    except Exception as e:
        logger.error(
            "Error with payload. "
            "img_id: {}, "
            "annotation_table: {}, "
            "annotation: {}, "
            "current_user: {}".format(
                img_id, 
                annotation_table,
                annotation,
                current_user
            )
        )
        raise e

    return True


@app.get("/get_annotations")
def get_annotations(annotation_table: str):
    table = getattr(models.AnnotationTable, annotation_table, None)
    if table is None:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND, 
            detail="annotation_table not found: {}".format(annotation_table)
        )

    annotations = backend_instance.get_annotations(table)

    return annotations


@app.get("/get_image")
def get_image(img_id: str):
    s3_path = backend_instance.get_image_path(img_id)
    if not s3_path:
        error = FileExistsError("Image path does not exist for img_id: {}".format(img_id))
        logger.error(repr(error))
        return HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Image Id does not exist")

    bucket, key = models.parse_bucket_key_from_url(s3_path)
    
    expiration_time = datetime.datetime.now() + datetime.timedelta(seconds=3600)

    return models.ImgLocationResponse(
        img_id=img_id,
        img_path=s3_path,
        annotation_expiration_utc_time=expiration_time
    )


@app.get("/query_images")
def query_images(query: str):
    """Queries all image metadata and returns all entries in `img_location` 
    where each key, value pair in the query matches the corresponding key, value 
    pair in the image metadata.
    """
    import json

    try:
        parsed_query = json.loads(query)
    except json.decoder.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Expect query as a json")

    results = backend_instance.query_images(parsed_query)

    return results
