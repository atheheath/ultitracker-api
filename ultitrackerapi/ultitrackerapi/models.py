import datetime 
import posixpath 

from enum import Enum
from fastapi import Form
from pydantic import BaseConfig, BaseModel
from typing import Dict, List, Optional, Set, Type
from ultitrackerapi import ANNOTATION_EXPIRATION_DURATION, ULTITRACKER_AUTH_JWT_ALGORITHM, get_logger


logger = get_logger(__name__)


# NOTE: Header and Payload information is readable by everyone
class Header(BaseModel):
    alg: str = ULTITRACKER_AUTH_JWT_ALGORITHM
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
    user_id: str


class UserInDBwPass(UserInDB):
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


class Game(BaseModel):
    authorized_users: List[str]
    data: Dict
    game_id: str


class GameResponse(BaseModel):
    data: Dict
    game_id: str
    thumbnail_key: str
    video_key: str

    def __init__(self, *args, **kwargs):

        # put this import here to not mess with import orders
        from ultitrackerapi import get_s3Client
        s3Client = get_s3Client()

        super().__init__(*args, **kwargs)
        
        if len(self.data) != 0:
            self.data["thumbnail"] = s3Client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.data["bucket"],
                    "Key": self.thumbnail_key,
                },
                ExpiresIn=10,
            )

            self.data["video"] = s3Client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.data["bucket"],
                    "Key": self.video_key
                },
                ExpiresIn=60 * 60 * 2,
            )
    
    
class GameList(BaseModel):
    game_list: List[Game]

    def add_game(self, game: Game):
        self.game_list.append(game)


class GameListResponse(BaseModel):
    game_list: List[GameResponse]


class ArbitraryModelConfig(BaseConfig):
    arbitrary_types_allowed = True


class Table(BaseModel):
    # Want to allow Type for column_types, so we need
    # to allow aribitrary types for pydantic
    Config = ArbitraryModelConfig
    table_name: str
    schema_name: str
    columns: List[str]
    column_types: List[Type]
    create_commands: List[str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if len(self.columns) != len(self.column_types):
            raise ValueError("columns and column_types must have the same length")

    def __hash__(self):
        return hash(self.table_name + self.schema_name + ",".join(self.columns))

    @staticmethod
    def construct_full_name(schema_name, table_name):
        return ".".join([schema_name, table_name])

    @property
    def full_name(self):
        return self.construct_full_name(self.schema_name, self.table_name)


class ImgEncoding(Enum):
    jpeg = 0
    png = 1
    tiff = 2


class Box(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    player_id: Optional[str]


class PlayerBbox(Box):
    player_id: Optional[str]


class LineId(Enum):
    top_sideline = 0
    left_back_endzone = 1
    left_front_endzone = 2
    right_front_endzone = 3
    right_back_endzone = 4
    bottom_sideline = 5
    fifty_yardline = 6
    top_hash = 7
    bottom_hash = 8


class LineSegment(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    line_id: LineId


class ImgLocation(BaseModel):
    img_id: str
    img_raw_path: str
    img_type: ImgEncoding
    img_metadata: dict
    game_id: Optional[str]
    frame_number: Optional[int]


def parse_bucket_key_from_url(url):
    stripped_url = url.split("//")[1]
    if url[:4] == "http":
        bucket = stripped_url.split(".")[0]
        key = posixpath.sep.join(stripped_url.split("?")[0].split(posixpath.sep)[1:])
    elif url[:5] == "s3://":
        bucket = stripped_url.split(posixpath.sep)[0]
        key = posixpath.sep.join(stripped_url.split(posixpath.sep)[1:])
    else:
        raise ValueError("Invalid url passed")

    return bucket, key


def is_not_presigned_url(url):
    if url[:4] == "http" and "?AWSAccessKeyId" in url and "&Expires=" in url:
        return False

    return True
    
class ImgLocationResponse(BaseModel):
    img_id: str
    img_path: str
    annotation_expiration_utc_time: datetime.datetime

    def __init__(self, *args, **kwargs):

        # put this import here to not mess with import orders
        from ultitrackerapi import get_s3Client
        s3Client = get_s3Client()

        super().__init__(*args, **kwargs)

        if is_not_presigned_url(self.img_path):
            bucket, key = parse_bucket_key_from_url(self.img_path)
            self.img_path = s3Client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": bucket,
                    "Key": key,
                },
                ExpiresIn=ANNOTATION_EXPIRATION_DURATION,
            )


class ImgLocationListResponse(BaseModel):
    img_locations: List[ImgLocationResponse]


class AnnotationTable(Enum):
    player_bbox = 0
    field_lines = 1
    camera_angle = 2


class AnnotationAction(Enum):
    sent = 0
    submitted = 1


class Annotation(BaseModel):
    img_id: str

    @staticmethod
    def construct_full_name(schema_name, table_name):
        return ".".join([schema_name, table_name])

    @property
    def full_name(self):
        return self.construct_full_name(self.schema_name, self.table_name)


class AnnotationPlayerBboxes(Annotation):
    bboxes: List[PlayerBbox]


class AnnotationFieldLines(Annotation):
    img_id: str
    line_coords: List[LineSegment]


class AnnotationCameraAngle(Annotation):
    img_id: str
    is_valid: bool


class Database(BaseModel):
    name: str
    tables: Set[Table]
