import logging
import os  # for: os.getcwd; os.mkdir; os.listdir;
from os import path  # for: os.path.abspath
import shutil  # for: shutil.move

# for: cv2.imread; cv2.namedWindow; cv2.imshow;
# cv2.waitKey; cv2.destroyAllWindows; cv2.IMREAD_COLOR
import cv2

logging.basicConfig(level=logging.INFO)

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

firstFolderName = input("Enter first folder name: [a] ")
secondFolderName = input("Enter second folder name: [d] ")

currentPath = os.path.abspath(
    os.getcwd()
)  # Stolen from: https://stackoverflow.com/q/3430372
os.chdir(currentPath)  # Change working directory to the path where the python file is

if (
    path.isdir(firstFolderName) != 1
):  # Check if folder already exists, if it does not make it
    os.mkdir(firstFolderName)
if path.isdir(secondFolderName) != 1:
    os.mkdir(secondFolderName)

for filename in os.listdir(
    os.getcwd()
):  # Go through every file in the working directory
    if (filename.lower()).endswith(
        IMAGE_EXTENSION
    ):  # If the file name ends with image extension
        logging.info(filename)
        image = cv2.imread(filename, cv2.IMREAD_COLOR)
        window_name = filename.split(".")[0]
        cv2.namedWindow(window_name)  # Window name is the same as image file name
        cv2.imshow(window_name, image)
        key = cv2.waitKey()
        if key == RIGHT_FOLDER_CODE:
            shutil.move(
                currentPath + "/" + filename,
                currentPath + "/" + firstFolderName + "/" + filename,
            )
        elif key == LEFT_FOLDER_CODE:
            shutil.move(
                currentPath + "/" + filename,
                currentPath + "/" + secondFolderName + "/" + filename,
            )
        # else:
        #    print(key)
        cv2.destroyAllWindows()
