import ffmpeg


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
