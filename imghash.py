import imagehash
from PIL import Image
import sys
import random
import os
import subprocess
from pathlib import Path
import re
import datetime
import time

Image.MAX_IMAGE_PIXELS = 1000000000


white = (255, 255, 255, 255)


def has_transparency(img):
    if img.mode == "P":
        transparent = img.info.get("transparency", -1)
        for _, index in img.getcolors():
            if index == transparent:
                return True
    elif img.mode == "RGBA":
        extrema = img.getextrema()
        if extrema[3][0] < 255:
            return True
    return False


def process_transparency(img):
    try:
        if has_transparency(img):
            img.load()  # needed for split()
            if len(img.split()) > 3:
                background = Image.new("RGB", img.size, white)
                background.paste(img, mask=img.split()[3])
                img = background
    except:  # noqa: E722
        pass
    return img


def clean_temp():
    path = f"{Path.home()}/imghash/temp/"
    now = time.time()
    for f in os.listdir(path):
        f = os.path.join(path, f)
        if os.stat(f).st_mtime < now - 60:
            if os.path.isfile(f):
                os.remove(f)


source_file = str(sys.argv[1])
if not os.path.exists(f"{Path.home()}/imghash/temp"):
    os.mkdir(f"{Path.home()}/imghash/temp")

filename_in = str(sys.argv[1])
filename_out = (
    f"{Path.home()}/imghash/temp/temp_image_{random.randint(100000, 999999)}.png"
)
proc = subprocess.Popen(["ffmpeg", "-i", filename_in], stderr=subprocess.PIPE)
_, result = proc.communicate()
image = False
is_video = False
for data in re.finditer(
    r"Stream\s#[^:]+:[^:]+:\s(?P<type>(Video)|Audio):\s(?P<format>[^,]+),\s(?(2)(?P<colorspace>[^,]+(?:\([^)]+\))?),\s(?P<width>\d+)x(?P<height>\d+)(?P<is_video>.*, [^\s]+ fps)?|(?P<frequency>\d+)\sHz.\s(?P<channels>[^,]+))",
    result.decode("utf-8"),
):
    if data["type"] == "Video":
        image = True
        if data["is_video"] is not None:
            is_video = True
        height = data["height"]
        width = data["width"]
        datatype = data["format"]
        break
if image:
    if is_video:
        m = re.search(
            r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)(?:\s|,)", result.decode("utf-8")
        )
        duration = datetime.timedelta(
            hours=int(m.group(1)),
            minutes=int(m.group(2)),
            seconds=int(m.group(3)),
            milliseconds=int(m.group(4)) * 10,
        ).total_seconds()
        target = f"{max(0, min(duration * 0.5, duration - 0.1)):.3f}"
        args = [
            "ffmpeg",
            "-ss",
            target,
            "-i",
            filename_in,
            "-map",
            "v:0",
            "-frames:v",
            "1",
            filename_out,
        ]
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        proc.communicate()
        img = Image.open(filename_out)
        source_file = filename_out
    else:
        img = Image.open(filename_in)
    out = subprocess.Popen(
        [f"{Path.home()}/imghash/image-intensities", source_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    stdout, stderr = out.communicate()
    quadrants = stdout.decode("utf-8")[:-1].split("\t")
    try:
        img = process_transparency(img)
        phash = str(imagehash.phash(img, hash_size=16))
    except:  # noqa: E722
        phash = ""
    print(
        f'{{"phash":"{phash}", "height":{height}, "width":{width}, "quadrants":{[float(x) for x in quadrants]}}}'
    )
    if os.path.exists(filename_out):
        os.remove(filename_out)
        if random.randint(100) == 1:
            clean_temp()
else:
    print(f'{{"phash":"", "height":0, "width":0, "quadrants":[]}}')
