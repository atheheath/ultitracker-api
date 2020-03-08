import ultitrackerapi

from enum import Enum
from pydantic import BaseModel
from typing import List
from ultitrackerapi import get_logger, models, sql_backend


logger = get_logger(__name__, "DEBUG")

class AnnotationOrderType(Enum):
    random = 0
    sequential = 1


# class AnnotationStatusType(bool):
#     pass


# class PredictionStatusType(bool):
#     pass


class AnnotatorQueueParams(BaseModel):
    game_ids: List[str]
    annotation_type: models.AnnotationTable
    order_type: AnnotationOrderType
    # annotation_status: AnnotationStatusType
    # prediction_status: PredictionStatusType


# class AnnotatorQueue(object):
#     """Interface for handling different annotator tasks. Annotator tasks will
#      be able to separate on the following characteristics
#         * Game
#         * Annotation Type (Box, field lines, etc.)
#         * Order of Extracted Images from Video (Sequential or Random)
#         * Annotation status (Image has been annotated or not)
#         * Prediction status (Image has initial predictions)

#     When an individual would like to annotate, they will request a task by
#     qualifying on the above characteristics
#     """

#     def __init__(self, client: sql_backend.SQLClient):
#         self._client = client

def get_next_n_images(
    backend: sql_backend.SQLBackend, 
    queue_params: AnnotatorQueueParams
) -> models.ImgLocationListResponse:
    # get all images that are
    #   1) Not annotated
    #   2) Not been sent out and not expired
    available_images_query = """
    WITH images_with_annotations AS (
        SELECT DISTINCT img_id
        FROM ultitracker.annotation_transaction
        WHERE 1=1
            AND action = 'submitted'
            AND table_ref = '{table_ref}'
    ),
    images_with_camera_angle AS (
        SELECT DISTINCT img_id
        FROM ultitracker.camera_angle
        WHERE 1=1
            AND is_valid = true
    ),
    images_out_for_submission AS (
        SELECT DISTINCT A.img_id
        FROM ultitracker.annotation_transaction A
        JOIN (
            SELECT
                img_id,
                table_ref,
                MAX(timestamp) AS max_timestamp
            FROM 
                ultitracker.annotation_transaction
            GROUP BY img_id, table_ref
        ) B ON A.img_id = B.img_id AND A.table_ref = B.table_ref
        WHERE 1=1
            AND A.timestamp = B.max_timestamp
            AND A.action = 'sent'
            AND A.timestamp + INTERVAL '{expiration_duration} SECONDS' > NOW() AT TIME ZONE 'utc'
            AND B.table_ref = '{table_ref}'
    ),
    unavailable_images AS (
        SELECT * FROM (
            SELECT img_id FROM images_with_annotations
            UNION
            SELECT img_id FROM images_out_for_submission
        ) A
    ),
    values_to_insert AS (
        SELECT
            A.img_id AS img_id,
            NOW() AT TIME ZONE 'utc' AS timestamp,
            '{table_ref}' AS table_ref,
            'sent' AS action
        FROM ultitracker.img_location A
        {join_camera_angle}
        LEFT JOIN unavailable_images B ON A.img_id = B.img_id
        WHERE 1=1
            AND B.img_id IS NULL
            AND A.game_id IN {game_ids}
        {order_by}
        LIMIT {num_images}
    ),
    inserted_values AS (
        INSERT INTO ultitracker.annotation_transaction
        SELECT img_id, timestamp, CAST(table_ref AS annotation_table), CAST(action AS annotation_action)
        FROM values_to_insert
    )
    SELECT A.img_id, B.img_raw_path, NOW() AT TIME ZONE 'utc' + INTERVAL '{expiration_duration} SECONDS'
    FROM values_to_insert A
    JOIN ultitracker.img_location B ON A.img_id = B.img_id
    """.format(
        table_ref=queue_params.annotation_type.name,
        expiration_duration=ultitrackerapi.ANNOTATION_EXPIRATION_DURATION,
        num_images=ultitrackerapi.NUM_IMAGES_FOR_ANNOTATION,
        join_camera_angle="JOIN images_with_camera_angle C ON A.img_id = C.img_id" if queue_params.annotation_type.name != models.AnnotationTable.camera_angle.name else "",
        game_ids="(" + ", ".join(["'" + game_id + "'" for game_id in queue_params.game_ids]) + ")",
        order_by="ORDER BY A.frame_number" if queue_params.order_type == AnnotationOrderType.sequential else "ORDER BY RANDOM()"
    )

    results = backend.client.execute(available_images_query)

    logger.debug("get_next_n_images result: {}".format(results))

    return models.ImgLocationListResponse(img_locations=[
        models.ImgLocationResponse(
            img_id=result[0],
            img_path=result[1],
            annotation_expiration_utc_time=result[2]
        )
        for result in results
    ])