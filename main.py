import sys
import argparse
from pathlib import Path

from canvasapi import Canvas
import yaml
import jsonpickle

from course_dl import CourseDownloader
from error_handler import  CanvasErrorHandler

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

    parser = argparse.ArgumentParser(description="Archives plain html content and associated files from Canvas courses.")
    parser.add_argument("-c", "--config", default="credentials.yaml", help="Path to YAML credentials file (default: credentials.yaml)")
    parser.add_argument("-o", "--output", default="./output", help="Directory to store exported data (default: ./output)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output for debugging.")
    # parser.add_argument("--version", action="version", version="Canvas Student Data Export Tool 1.0")

    args = parser.parse_args()

    # Load credentials from YAML
    creds = _load_credentials(args.config)
    
    # Validate credentials
    required = ["API_URL", "API_KEY", "USER_ID"]
    missing = [k for k in required if not creds.get(k)]

    if missing:
        print(f"Error: {args.config} is missing required field(s): {', '.join(missing)}.")
        print("Please create the YAML file with the following structure:\n"
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
    DL_LOCATION = Path(args.output)

    # Connect to Canvas =========================================================

    print("\nConnecting to Canvas…\n") #--------------------------

    # Initialize a new Canvas object
    canvas = Canvas(API_URL, cookies=COOKIES) # <<<<<<<<<<<<<<<<< NOTE: canvasapi does not support cookies by default
    # (currently running on modified canvasapi)
    
    # Test the connection and API key
    try:
        user = canvas.get_current_user()
        print(f"Successfully authenticated as: {user.name} (ID: {user.id})") #--------------------------
        if user.id != USER_ID:
            print(f"Warning: Authenticated user ID ({user.id}) does not match configured USER_ID ({USER_ID})")
    except Exception as e:
        error_type, message = CanvasErrorHandler.handle_canvas_exception(
            e, "Canvas authentication"
        )
        if CanvasErrorHandler.is_fatal_error(error_type):
            print(f"FATAL: {message}")
            sys.exit(1)
        else:
            CanvasErrorHandler.log_error(error_type, message, verbose=args.verbose)

    # Archive Process =========================================================
 
    print(f"Creating output directory: {DL_LOCATION}\n")
    # os.makedirs(DL_LOCATION, exist_ok=True)
    DL_LOCATION.mkdir(parents=True, exist_ok=True)
    
 
    courses_list = [
        canvas.get_courses(enrollment_state = "active", include=["syllabus_body", "term"]),
        canvas.get_courses(enrollment_state = "completed", include=["syllabus_body", "term"])
    ]

    select = set(COURSE_SELECTION)
    skip = set(COURSES_TO_SKIP)

    for courses in courses_list:
        for course in courses:
            if course.id in skip or not hasattr(course, "name") or not hasattr(course, "term"):
                continue
            if len(select) > 0 and course.id not in select:
                continue

            # print(course.term)

            # course_dir = os.path.join(DL_LOCATION, course.term["name"], course.course_code)
            course_dir: Path = DL_LOCATION / course.term["name"] / course.course_code

            course_downloader = CourseDownloader(course, course_dir, FILE_SIZE_THRESH)
            print(f"---Downloading resources for {course.course_code}---")
            course_downloader.download_resources()
