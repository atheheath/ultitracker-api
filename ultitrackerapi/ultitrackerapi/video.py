import ffmpeg
import os


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
