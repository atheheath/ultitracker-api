import argparse
import datetime
import json
import os
import posixpath
import shutil
import tempfile
import uuid

from concurrent import futures
from ultitrackerapi import get_backend, get_logger, get_s3Client, video    

backend_instance = get_backend()
logger = get_logger(__name__)
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
    video_length = str(
        datetime.timedelta(seconds=int(video.get_video_duration(video_filename)))
    )
    logger.debug("extract_and_upload_video: Finished getting video length")

    logger.debug("extract_and_upload_video: Updating length in db")
    update_game_video_length(game_id, video_length)
    logger.debug("extract_and_upload_video: Finished updating length in db")
    
    logger.debug("extract_and_upload_video: Extracting thumbnail")
    video.get_thumbnail(video_filename, thumbnail_filename)
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

    logger.debug("extract_and_upload_video: Extracting frames")
    tempdir = tempfile.mkdtemp()
    video.extract_frames(video_filename, tempdir)
    logger.debug("extract_and_upload_video: Finished extracting frames")
    
    def get_frame_number_from_filename(filename):
        return int(os.path.splitext(filename)[0].split("_")[-1])

    def get_frames(directory):
        return sorted(os.listdir(tempdir), key=get_frame_number_from_filename)

    logger.debug("extract_and_upload_video: Uploading frames")
    with futures.ThreadPoolExecutor(8) as ex:
        for frame in os.listdir(tempdir):
            ex.submit(
                s3Client.upload_file,
                os.path.join(tempdir, frame),
                bucket,
                posixpath.join(
                    video_key + "_frames",
                    frame
                )
            )
    logger.debug("extract_and_upload_video: Finished uploading frames")


    logger.debug("extract_and_upload_video: Inserting image metadata")
    raw_paths = [
        posixpath.join(video_key + "_frames", frame) 
        for frame in get_frames(tempdir)
    ]
    img_types = ["png" for frame in get_frames(tempdir)]
    metadatas = [
        {"bucket": bucket}
        for frame in get_frames(tempdir)
    ]
    frame_numbers = [get_frame_number_from_filename(frame) for frame in get_frames(tempdir)]

    insert_images(
        raw_paths,
        img_types,
        metadatas,
        game_id,
        frame_numbers
    )

    logger.debug("extract_and_upload_video: Finished inserting image metadata")

    os.remove(video_filename)
    os.remove(thumbnail_filename)
    shutil.rmtree(tempdir)


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