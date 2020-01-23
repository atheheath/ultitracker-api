from enum import Enum
from fastapi import Form
from pydantic import BaseConfig, BaseModel
from typing import Dict, List, Optional, Set, Type

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


class Game(BaseModel):
    authorized_users: List[str]
    data: Dict
    game_id: str


class GameResponse(BaseModel):
    data: Dict
    game_id: str

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
                    "Key": self.data["thumbnail_key"],
                },
                ExpiresIn=10,
            )

            self.data["video"] = s3Client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.data["bucket"],
                    "Key": self.data["video_key"]
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
    name: str
    columns: List[str]
    column_types: List[Type]
    create_commands: List[str]


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


class LineId(Enum):
    top_sideline = 0
    left_back_endzone = 1
    left_front_endzone = 2
    right_front_endzone = 3
    right_back_endzone = 4
    bottom_sideline = 5


class LineSegment(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int
    line_id: LineId


class AnnotationTable(Enum):
    player_bbox = 0
    field_lines = 1
    gameplay_state = 2


class Database(BaseModel):
    name: str
    tables: Set[Table]
