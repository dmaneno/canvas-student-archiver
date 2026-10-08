import sys
import argparse
from pathlib import Path

from canvasapi import Canvas
import yaml
import jsonpickle

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

OVERWRITE_CONFIG = {}
LOAD_FROM_JSON = True

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
    parser.add_argument("-o", "--output", default="./output", help="Directory to store exported data (default: ./output)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output for debugging.")
    # parser.add_argument("--version", action="version", version="")

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

    OVERWRITE_CONFIG = creds.get("OVERWRITE_CONFIG", {})
    course_overwrite_config = OVERWRITE_CONFIG.get("course_level",{})
    # to check if necessary to step into download_resources() at all for already-archived courses
    course_overwrite_flag = True if True in course_overwrite_config.values() else False


    LOAD_FROM_JSON = creds.get("LOAD_FROM_JSON", True)

    # Update output directory
    DL_LOCATION = Path(args.output)


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
 
    print12(f"Creating output directory: {DL_LOCATION}\n")
    DL_LOCATION.mkdir(parents=True, exist_ok=True)
    
    try:
        courses_list = canvas.get_courses(
            state=["unpublished","available","completed","deleted"],
            include = ["syllabus_body","total_scores","term","total_students",
                        "favorites","teachers","tabs","course_image","banner_image"]
        )
        courses = [course for course in courses_list]
    except Exception as e:
            CanvasErrorHandler.handle_exception(
                e, 'retrieve and unpacking paginated list of courses'
            )
            print12("Error requesting courses from Canvas. Aborting...")
            sys.exit(1)


    select = set(COURSE_SELECTION)
    skip = set(COURSES_TO_SKIP)

    term_dict = {}
    course_count = 0
    skipped = []
    download_update_count = 0
    unchanged_count = 0

    print12(f'** Fetched {len(courses)} courses. Beginning downloads... **')

    # TODO: progress bar? threading?
    for course in courses:
        course_count += 1
        print12(f"--- COURSE COUNT: {course_count} ---")

        # -- Skips --
        if not hasattr(course, "id"): # Unlikely but just in case
            print12("No id found for course. Skipping...")
            skipped.append(None)
            continue
        # NOTE: perhaps in future, write some UI to select / deselect available courses
        # instead of doing it in config
        if course.id in skip or (select and course.id not in select):
            print12(f'Id {course.id} in "skip", or not in "select". Skipping...')
            skipped.append(course.id)
            continue

        # -- Build Path --
        # TODO: option to skip unavailable courses
        name = None
        code = None
        term_folder = "Unavailable_Courses"
        if hasattr(course, "name"):
            name = course.name
            code = course.course_code if hasattr(course, "course_code") else None
            term_folder = course.term["name"] if hasattr(course, "term") else "Courses_Without_Term"

        course_folder = short_fname(valid_fname(code)) if code else short_fname(valid_fname(name))
        course_folder = course_folder if course_folder else str(course.id)        
        course_path: Path = DL_LOCATION / short_fname(valid_fname(term_folder)) / course_folder

        print12(f'Course: [{course.id}] [{code}]: {name}')

        #  -- Download Course --
        # NOTE: runs on assumption that if the directory exists, then the jsons for course also exist...
        # i.e. if for some reason the directory exists but nothing is in there, and overwrite_configs are false,
        # then the program won't download the resources even though the course hasn't been archived yet
        if not course_path.is_dir() or course_overwrite_flag: # or overwrite is true
            course_downloader = CourseDownloader(course, course_path, FILE_SIZE_THRESH,
                                                 course_overwrite_config, LOAD_FROM_JSON)
            print12(f"Downloading resources to {str(course_path)}...")
            course_downloader.download_resources()
            download_update_count += 1
        else:
            print12(f'** {str(course_path)} already exists and overwrite is disabled **')
            unchanged_count += 1

        # -- Add course to term / course dictionary --
        if term_folder not in term_dict:
            term_dict[term_folder] = {
                "count":        0,
                "course_list":  [],
            }
        term_dict[term_folder]["count"] += 1
        term_dict[term_folder]["course_list"].append({
            "id":   course.id,
            "code": code,
            "name": name,
        })

    print12(f'** Finished downloading courses **')
    print12(f'Courses newly archived or updated: {download_update_count}')
    print12(f'Courses already archived and unchanged: {unchanged_count}')
    print12(f'Skipped {len(skipped)} courses: {skipped}')
    print12("----------------------------------------------------------------\n"
            f'Total courses currently archived: {len(courses) - len(skipped)}\n')

    # Write top-level JSON of term / course list
    json_path: Path = DL_LOCATION / "courses_by_terms.json"
    if not json_path.is_file() or OVERWRITE_CONFIG.get("courses_by_terms", False):
        print12(f'** writing term_dict to json in {str(json_path)} **')
        write_obj_json(term_dict, json_path)
    else:
        print12(f'** {str(json_path)} already exists and overwrite is disabled **')
                