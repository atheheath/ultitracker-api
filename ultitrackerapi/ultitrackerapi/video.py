import ffmpeg
import os
import subprocess


def get_thumbnail(in_filename, out_filename, time=1):
    (
        ffmpeg.input(in_filename, ss=time)
        .filter("scale", 720, -1)
        .output(out_filename, vframes=1)
        .overwrite_output()
        .run()
    )


def get_video_duration(in_filename):
    return float(ffmpeg.probe(in_filename)["streams"][0]["duration"])


def extract_frames(in_filename, out_directory, fps=1):
    (
        ffmpeg.input(in_filename)
        .filter("scale", 720, -1)
        .filter("fps", fps)
        .output(
            os.path.join(out_directory, "frame_%06d.png"),
        ).overwrite_output()
        .run()
    )


def chunk_video(in_filename, out_directory, chunk_size=60):
    """
    Parameters
    ----------
    in_filename : Path to video to chunk
    out_directory : Path to write out the video chunks
    chunk_size : Length in seconds of chunked video
    """
    # (
    #     ffmpeg.input(in_filename)
    #     .filter("segment")
    #     .filter("segment_time", chunk_size)
    #     .filter("reset_timestamps", 1)
    #     .filter("map", 0)
    #     .output(
    #         os.path.join(out_directory, "chunk_%03d.mp4")
    #     ).overwrite_output()
    #     .run()
    # )
    # (
    #     ffmpeg.input(in_filename)
    #     .filter("segment")
    #     .filter("segment_time", chunk_size)
    #     .output(
    #         os.path.join(out_directory, "chunk_%03d.mp4")
    #     ).overwrite_output()
    #     .run()
    # )
    command = "ffmpeg -i {input_filename} -codec copy -f segment -segment_time {chunk_size} {out_directory}".format(
        input_filename=in_filename,
        chunk_size=chunk_size,
        out_directory=os.path.join(out_directory, "chunk_%03d.mp4")
    ).split(" ")

    process = subprocess.Popen(command)
    out, err = process.communicate(input)
    retcode = process.poll()
    if retcode:
        raise ValueError("ffmpeg", out, err)

    return out, err