import json
import logging
import os
import sys
import zipfile
from re import finditer

import coloredlogs
import cv2
import imageio
import numpy as np
import requests
from PIL import Image
from config import Config as conf


def read_image(path):
    """
    Read a file image
    :param path: <string> Path of the image
    :return: <RGB> image
    """
    # Read image
    with open(path, "rb") as file:
        image_bytes = bytearray(file.read())
        np_image = np.asarray(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
    # See if image loaded correctly
    if image is None:
        conf.log.error("{} file is not valid image".format(path))
        sys.exit(1)
    return image


def write_image(image, path):
    """
    Write a file image to the path (create the directory if needed)
    :param image: <RGB> image to write
    :param path: <string> location where write the image
    :return: None
    """
    dir = os.path.dirname(path)
    if dir != '':
        os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.splitext(path)[1] not in cv2_supported_extension():
        conf.log.error("{} invalid extension format.".format(path))
        sys.exit(1)

    cv2.imwrite(path, image)

    if not check_image_file_validity(path):
        conf.log.error(
            "Something gone wrong writing {} image file. The final result is not a valid image file.".format(path))
        sys.exit(1)


def check_shape(path, shape=conf.desired_shape):
    """
    Valid the shape of an image
    :param image: <RGB> Image to check
    :param shape: <(int,int,int)> Valid shape
    :return: None
    """
    if os.path.splitext(path)[1] != ".gif":
        img_shape = read_image(path).shape
    else:
        img_shape = imageio.mimread(path)[0][:, :, :3].shape

    if img_shape != shape:
        conf.log.error("Image is not 512 x 512, got shape: {}".format(img_shape))
        conf.log.error("You should use one of the rescale options".format(img_shape))
        sys.exit(1)


def check_image_file_validity(image_path):
    """
    Check is a file is valid image file
    :param image_path: <string> Path to the file to check
    :return: <Boolean> True if it's an image file
    """
    try:
        im = Image.open(image_path)
        im.verify()
    except Exception:
        return False
    return True if os.stat(image_path).st_size != 0 else False


def setup_log(log_lvl=logging.INFO):
    """
    Setup a logger
    :param log_lvl: <loggin.LVL> level of the log
    :return: <Logger> a logger
    """
    log = logging.getLogger(__name__)
    coloredlogs.install(level=log_lvl, fmt='[%(levelname)s] %(message)s')
    return log


def camel_case_to_str(identifier):
    """
    Return the string representation of a Camel case word
    :param identifier: <string> camel case word
    :return: a string representation
    """
    matches = finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', identifier)
    return " ".join([m.group(0) for m in matches])


def cv2_supported_extension():
    """
    List of extension supported by cv2
    :return: <string[]> extensions list
    """
    return [".bmp", ".dib", ".jpeg", ".jpg", ".jpe", ".jp2", ".png",
            ".pbm", ".pgm", "ppm", ".sr", ".ras", ".tiff", ".tif"]


def json_to_argv(data):
    """
    Json to args parameters
    :param data: <json>
    :return: <Dict>
    """
    l = []
    for k, v in data.items():
        if not isinstance(v, bool):
            l.extend(["--{}".format(k), str(v)])
        elif v:
            l.append("--{}".format(k))
    return l


def dll_file(url, file_path):
    """
    Download a file
    :param url: <string> url of the file to download
    :param file_path: <string> file path where save the file
    :return: <string> full path of downloaded file
    """
    conf.log.debug("Download url : {} to path: {}".format(url, file_path))
    response = requests.get(url, stream=True)
    dir = os.path.dirname(file_path)
    if dir != '':
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as f:

        total_length = response.headers.get('content-length')

        if total_length is None:  # no content length header
            f.write(response.content)
        else:
            dl = 0
            total_length = int(total_length)
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                f.write(data)
                done = int(50 * dl / total_length)
                print("[{}{}]".format('=' * done, ' ' * (50 - done)), end="\r")
            print(" "*80, end="\r")
        conf.log.info("{} Downloaded".format(url,))
    return file_path


def unzip(zip_path, extract_path):
    """
    Extract a zip
    :param zip_path: <string> path to zip to extract
    :param extract_path: <string> path to dir where to extract
    :return: None
    """
    conf.log.debug("Extracting zip : {} to path: {}".format(zip_path, extract_path))
    if not os.path.exists(extract_path):
        os.makedirs(extract_path, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        uncompress_size = sum((file.file_size for file in zf.infolist()))
        extracted_size = 0

        for file in zf.infolist():
            done = int(50 * extracted_size / uncompress_size)
            print("[{}{}]".format('=' * done, ' ' * (50 - done)), end="\r")
            zf.extract(file, path=extract_path)
            extracted_size += file.file_size
        print(" "*80, end="\r")
