import argparse
import boto3
import datetime
import json
import os
import posixpath
import re
import shutil
import tempfile
import uuid

from concurrent import futures
from multiprocessing import Pool
from ultitrackerapi import get_backend, get_logger, get_s3Client, video    

backend_instance = get_backend()
logger = get_logger(__name__, level="DEBUG")
s3Client = get_s3Client()


def update_game_video_length(game_id, video_length):
    command = """
    UPDATE ultitracker.game_metadata
    SET data = jsonb_set(data, '{{length}}', '"{video_length}"', true)
    WHERE game_id = '{game_id}'
    """.format(
        video_length=video_length,
        game_id=game_id
    )
    backend_instance.client.execute(command)


def get_frame_number(key, chunk_multiplier=60):
    frame_number = int(posixpath.splitext(posixpath.basename(key))[0].split("_")[1])
    chunk_number = int(posixpath.basename(posixpath.dirname(key)).split("_")[1])
    return chunk_number * chunk_multiplier + frame_number


def insert_images(
    img_raw_paths, 
    img_types, 
    img_metadatas, 
    game_id, 
    frame_numbers
):
    command = """
    INSERT INTO ultitracker.img_location (img_id, img_raw_path, img_type, img_metadata, game_id, frame_number) VALUES
    """

    for i, (img_raw_path, img_type, img_metadata, frame_number) in enumerate(zip(img_raw_paths, img_types, img_metadatas, frame_numbers)):
        command += """('{img_id}', '{img_raw_path}', '{img_type}', '{img_metadata}', '{game_id}', {frame_number}){include_comma}
        """.format(
            img_id=uuid.uuid4(),
            img_raw_path=img_raw_path,
            img_type=img_type,
            img_metadata=json.dumps(img_metadata),
            game_id=game_id,
            frame_number=frame_number,
            include_comma="," if i < (len(img_raw_paths) - 1) else ""
        )
    
    backend_instance.client.execute(command)


def extract_and_upload_video(
    bucket,
    video_filename, 
    thumbnail_filename, 
    video_key,
    thumbnail_key,
    game_id
):
    logger.debug("extract_and_upload_video: Getting video length")
    video_length_seconds = int(video.get_video_duration(video_filename))
    video_length = str(datetime.timedelta(seconds=video_length_seconds))
    logger.debug("extract_and_upload_video: Finished getting video length")

    logger.debug("extract_and_upload_video: Getting video height and width")
    video_height_width = video.get_video_height_width(video_filename)
    logger.debug("extract_and_upload_video: Finished getting height and width")

    logger.debug("extract_and_upload_video: Updating length in db")
    update_game_video_length(game_id, video_length)
    logger.debug("extract_and_upload_video: Finished updating length in db")
    
    logger.debug("extract_and_upload_video: Extracting thumbnail")
    video.get_thumbnail(video_filename, thumbnail_filename, time=video_length_seconds // 2)
    logger.debug("extract_and_upload_video: Finished extracting thumbnail")

    logger.debug("extract_and_upload_video: Uploading thumbnail")
    s3Client.upload_file(
        thumbnail_filename, 
        bucket, 
        thumbnail_key
    )
    logger.debug("extract_and_upload_video: Finished uploading thumbnail")

    logger.debug("extract_and_upload_video: Uploading video to S3")
    s3Client.upload_file(
        video_filename, 
        bucket, 
        video_key
    )
    logger.debug("extract_and_upload_video: Finished uploading video to S3")

    logger.debug("extract_and_upload_video: Chunking video")
    chunked_video_dir = tempfile.mkdtemp()
    video.chunk_video(video_filename, chunked_video_dir, chunk_size=60)
    logger.debug("extract_and_upload_video: Finished chunking video")

    logger.debug("extract_and_upload_video: Uploading video chunks")
    with futures.ThreadPoolExecutor(8) as ex:
        for vid in os.listdir(chunked_video_dir):
            ex.submit(
                s3Client.upload_file,
                os.path.join(chunked_video_dir, vid),
                bucket,
                posixpath.join(
                    posixpath.dirname(video_key),
                    "chunks",
                    vid
                )
            )
    logger.debug("extract_and_upload_video: Finished uploading video chunks")
    
    logger.debug("extract_and_upload_video: Submitting lambda frame extraction")
    
    aws_lambda_payloads = [
        json.dumps({
            "s3_bucket_path": "ultitracker-videos-test",
            "s3_video_path": posixpath.join(posixpath.dirname(video_key), "chunks", basename),
            "s3_output_frames_path": posixpath.join(posixpath.dirname(video_key), "frames", posixpath.splitext(basename)[0]),
            "video_metadata": video_height_width
        }).encode()
        for basename in os.listdir(chunked_video_dir)
    ]

    client = boto3.client('lambda')
 
    aws_lambda_responses = []
    with futures.ThreadPoolExecutor(max_workers=16) as ex:

        result_futures = []
        for payload in aws_lambda_payloads:
            result_futures.append(ex.submit(
                client.invoke,
                FunctionName="extractFrames",
                # InvocationType="Event",
                Payload=payload
            ))
            
        logger.debug("extract_and_upload_video: Submitted lambda frame extraction")

        for result_future in futures.as_completed(result_futures):
            aws_lambda_response = json.loads(result_future.result()["Payload"].read().decode("utf-8"))
            aws_lambda_responses.append(aws_lambda_response)

            raw_paths = ["s3://" + posixpath.join(frame["bucket"], frame["key"]) for frame in aws_lambda_response["frames"]]

            img_types = ["png" for frame in aws_lambda_response["frames"]]
            metadatas = [
                {"bucket": bucket}
                for frame in aws_lambda_response["frames"]
            ]

            frame_numbers = [-1 for frame in aws_lambda_response["frames"]]

            insert_images(
                raw_paths,
                img_types,
                metadatas,
                game_id,
                frame_numbers
            )

    logger.debug("extract_and_upload_video: Received all lambda responses")


    logger.debug("extract_and_upload_video: Finished inserting image metadata")

    os.remove(video_filename)
    os.remove(thumbnail_filename)
    shutil.rmtree(chunked_video_dir)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("bucket")
    parser.add_argument("video_filename")
    parser.add_argument("thumbnail_filename")
    parser.add_argument("video_key")
    parser.add_argument("thumbnail_key")
    parser.add_argument("game_id")

    args = parser.parse_args()

    extract_and_upload_video(
        bucket=args.bucket,
        video_filename=args.video_filename, 
        thumbnail_filename=args.thumbnail_filename,
        video_key=args.video_key, 
        thumbnail_key=args.thumbnail_key,
        game_id=args.game_id
    )


if __name__ == "__main__":
    main()