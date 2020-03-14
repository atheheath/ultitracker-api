# import argparse
import boto3
import ffmpeg
import json
import logging
import os
import posixpath
import sys
import tarfile
import tempfile

from concurrent.futures import ThreadPoolExecutor


def extract_frames(in_filename, out_directory, fps=1, height=720):
    print("\n\n\n{}\n\n\n".format(os.listdir("./")))
    (
        ffmpeg.input(in_filename)
        .filter("scale", height, -1)
        .filter("fps", fps)
        .output(
            os.path.join(out_directory, "frame_%06d.png"),
        ).overwrite_output()
        .run(cmd="./ffmpeg_bin")
    )


def handler(event, context):
    # parser = argparse.ArgumentParser()

    # parser.add_argument("s3_bucket_path")
    # parser.add_argument("s3_video_path")
    # parser.add_argument("s3_output_frames_path")
    # parser.add_argument("--num_parallel_upload_threads", default=4, type=int)

    # args = parser.parse_args()

    s3_bucket_path = event["s3_bucket_path"]
    s3_video_path = event["s3_video_path"]
    s3_output_frames_path = event["s3_output_frames_path"]
    video_metadata = event["video_metadata"]
    num_parallel_upload_threads = event.get("num_parallel_upload_threads", 4)
    logging_level = event.get("logging_level", "INFO")

    logger = logging.getLogger(name=__name__)
    logger.setLevel(logging_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.info("Event: {}".format(event))

    client = boto3.client('s3')

    _, download_filename = tempfile.mkstemp()
    frames_out_directory = tempfile.mkdtemp()
    _, tarred_frames_path = tempfile.mkstemp()

    logger.info("Downloading File")
    client.download_file(s3_bucket_path, s3_video_path, download_filename)
    logger.info("Finished downloading file")

    logger.info("Extracting frames")
    extract_frames(download_filename, frames_out_directory, height=video_metadata["height"])
    logger.info("Finished extracting frames")

    frames_info = []
    with ThreadPoolExecutor(num_parallel_upload_threads) as ex:
        for frame_path in os.listdir(frames_out_directory):
            key = posixpath.join(s3_output_frames_path, frame_path)

            ex.submit(
                client.upload_file, 
                os.path.join(frames_out_directory, frame_path), 
                s3_bucket_path, 
                posixpath.join(s3_output_frames_path, frame_path)
            )

            frames_info.append(
                {
                    "frame": frame_path,
                    "bucket": s3_bucket_path,
                    "key": key
                }
            )

    logger.info("Finished uploading files")

    return {
        "frames": frames_info
    }
    # return {
    #     "frames": [frame for frame in os.listdir(frames_out_directory)],
    #     "zipped_tar_archive": f"s3://{posixpath.join(s3_bucket_path, s3_output_frames_path)}"
    # }
