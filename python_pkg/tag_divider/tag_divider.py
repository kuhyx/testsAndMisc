"""Sort images into folders using keyboard input."""

import logging
import os  # for: os.chdir
from pathlib import Path
import shutil  # for: shutil.move

# for: cv2.imread; cv2.namedWindow; cv2.imshow;
# cv2.waitKey; cv2.destroyAllWindows; cv2.IMREAD_COLOR
import cv2

_logger = logging.getLogger(__name__)

IMAGE_EXTENSION = (
    ".bmp",
    ".dib",
    ".jpeg",
    ".jpg",
    ".jpe",
    ".jp2",
    ".png",
    ".pbm",
    ".pgm",
    ".ppm",
    ".pxm",
    ".pnm",
    ".pfm",
    ".sr",
    ".ras",
    ".tiff",
    ".tif",
    ".exr",
    ".hdr",
    ".pic",
)  # From: https://docs.opencv.org/4.5.2/d4/da8/group__imgcodecs.html
# Note: .webp excluded because animated images don't work
LEFT_FOLDER_CODE = 100  # Default 100 - 'd'
RIGHT_FOLDER_CODE = 97  # Default 97 - 'a'
# Change by checking: https://www.ascii-code.com/

first_folder_name = input("Enter first folder name: [a] ")
second_folder_name = input("Enter second folder name: [d] ")

current_path = Path.cwd().resolve()
os.chdir(current_path)  # Change working directory to the path where the python file is

if not Path(
    first_folder_name
).is_dir():  # Check if folder already exists, if not make it
    Path(first_folder_name).mkdir()
if not Path(second_folder_name).is_dir():
    Path(second_folder_name).mkdir()

for file_path in Path.cwd().iterdir():  # Go through every file in the working directory
    filename = file_path.name
    if (filename.lower()).endswith(
        IMAGE_EXTENSION
    ):  # If the file name ends with image extension
        _logger.info(filename)
        image = cv2.imread(filename, cv2.IMREAD_COLOR)
        window_name = filename.split(".")[0]
        cv2.namedWindow(window_name)  # Window name is the same as image file name
        cv2.imshow(window_name, image)
        key = cv2.waitKey()
        if key == RIGHT_FOLDER_CODE:
            shutil.move(
                current_path / filename,
                current_path / first_folder_name / filename,
            )
        elif key == LEFT_FOLDER_CODE:
            shutil.move(
                current_path / filename,
                current_path / second_folder_name / filename,
            )
        cv2.destroyAllWindows()
