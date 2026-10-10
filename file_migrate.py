import sys
import argparse
from pathlib import Path

from canvasapi import Canvas
import yaml
import jsonpickle
import time
from datetime import datetime

from course_dl import CourseDownloader
from error_handler import  CanvasErrorHandler
from util import clean_obj, write_obj_json, print12, short_fname, valid_fname

API_URL = ""
API_KEY = ""
USER_ID = 0
COOKIES = {} # <<<<<<<<<<<<<<<<< NOTE: canvasapi does not support cookies by default

# DL_LOCATION = "./output"
DL_LOCATION: Path = Path("./output")

COURSE_SELECTION = []
COURSES_TO_SKIP = []

FILE_SIZE_THRESH = -1

# code for _load_credentials, arg parsing, and initial Canvas connection setup based on
# https://github.com/davekats/canvas-student-data-export/blob/master/export.py

def _load_credentials(path: str) -> dict:
    """Return a dict with API_URL, API_KEY, USER_ID, etc, or empty dict if file missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.full_load(f) or {}
    except FileNotFoundError:
        return {}

if __name__ == "__main__":

    # Setup / Arg Parsing =========================================================

    parser = argparse.ArgumentParser(description="Archives data and associated files from Canvas courses.")
    parser.add_argument("-c", "--config", default="credentials.yaml", help="Path to YAML credentials file (default: credentials.yaml)")
    # parser.add_argument("-o", "--output", default="./output", help="Directory to store exported data (default: ./output)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output for debugging.")
    # parser.add_argument("--version", action="version", version="")
    parser.add_argument("-i","--input", help = "input / source dir of files")
    parser.add_argument("-o","--output", help = "output / target, destination dir of files")

    args = parser.parse_args()

    # Load credentials from YAML
    creds = _load_credentials(args.config)
    
    # Validate credentials
    required = ["API_URL", "API_KEY", "USER_ID"]
    missing = [k for k in required if not creds.get(k)]

    if missing:
        print12(f"Error: {args.config} is missing required field(s): {', '.join(missing)}.")
        print12("Please create the YAML file with the following structure:\n"
              "API_URL: https://<your>.instructure.com\n"
              "API_KEY: <your key>\n"
              "USER_ID: 123456\n")
        sys.exit(1)

    # Populate globals expected throughout the script
    API_URL = creds["API_URL"].strip().rstrip('/')
    API_KEY = creds["API_KEY"].strip()  # Remove leading/trailing whitespace which is a common issue
    USER_ID = creds["USER_ID"]
    # Use .get() to safely access optional/conditionally required keys
    COURSE_SELECTION = creds.get("COURSE_SELECTION", [])
    COURSES_TO_SKIP = creds.get("COURSES_TO_SKIP", [])

    COOKIES = creds.get("COOKIES",{}) # <<<<<<<<<<<<<<<<< NOTE: canvasapi does not support cookies by default

    FILE_SIZE_THRESH = creds.get("FILE_SIZE_THRESH", -1)

    # Update output directory
    SOURCE_DIR = Path(args.input)
    TARGET_DIR = Path(args.output)

    if not SOURCE_DIR.is_dir():
        print12(f"{SOURCE_DIR} is not an existing directory")
        sys.exit(1)
    if not TARGET_DIR.is_dir():
        print12(f"{TARGET_DIR} is not an existing directory")
        sys.exit(1)


    # Connect to Canvas =========================================================

    print12("\nConnecting to Canvas…\n") #--------------------------

    # Initialize a new Canvas object
    canvas = Canvas(API_URL, cookies=COOKIES) # <<<<<<<<<<<<<<<<< NOTE: canvasapi does not support cookies by default
    # (currently running on modified canvasapi)
    
    # Test the connection and API key
    try:
        user = canvas.get_current_user()
        print12(f"Successfully authenticated as: {user.name} (ID: {user.id})") #--------------------------
        if user.id != USER_ID:
            print12(f"Warning: Authenticated user ID ({user.id}) does not match configured USER_ID ({USER_ID})")
    except Exception as e:
        CanvasErrorHandler.handle_exception(e, "Canvas authentication")

    # Archive Process =========================================================

    # print12(f"Creating output directory: {DL_LOCATION}\n")
    # DL_LOCATION.mkdir(parents=True, exist_ok=True)

    # start_time = time.time()
    start_time = datetime.now()
    
    # try:
    #     courses_list = canvas.get_courses(
    #         state=["unpublished","available","completed","deleted"],
    #         include = ["syllabus_body","total_scores","term","total_students",
    #                     "favorites","teachers","tabs","course_image","banner_image"]
    #     )
    #     courses = [course for course in courses_list]
    # except Exception as e:
    #         CanvasErrorHandler.handle_exception(
    #             e, 'retrieve and unpacking paginated list of courses'
    #         )
    #         print12("Error requesting courses from Canvas. Aborting...")
    #         sys.exit(1)


    select = set(COURSE_SELECTION)
    skip = set(COURSES_TO_SKIP)



    # ---------------------------------------------------

    # for courses in courses_list:

    # path to new output
    # path to old output

    """
    for each course folder
        files.json -> dict
        for each file
            # fix id stuff if not an int
            make a File object (get requester from Canvas object)
            get file name
            if file name exists in old directory somewhere
                if filesize matches?
                    move it to Path(file.file_path)
                    mark download true
            else if file below threshold
                
                download to Path(file.file_path)
                mark download true
            else leave alone (maybe log the files that weren't downloaded / above thresh)

    """