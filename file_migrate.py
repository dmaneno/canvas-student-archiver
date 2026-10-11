import sys
import argparse
from pathlib import Path

from canvasapi import Canvas
from canvasapi.file import File
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


    # select = set(COURSE_SELECTION)
    # skip = set(COURSES_TO_SKIP)



    # ---------------------------------------------------

    requester = user._requester

    # for courses in courses_list:

    # path to new output
    # path to old output
    # NOTE: if you want to use this in threading, prob have to cast to list
    # json_paths = TARGET_DIR.rglob("files.json")
    json_paths = list(TARGET_DIR.rglob("files.json"))
    print12(f"found {len(json_paths)} files.json files")

    # EACH COURSE
    # TODO: selector for courses? - could possibly do like f string for above rglob. get code for course id ahead of time
    for json_path in json_paths:
        # get course dir and check if dir exists in source dir
        target_course_dir = json_path.parent
        search = list(SOURCE_DIR.rglob(target_course_dir.name))
        source_course_dir = None
        if len(search) != 0:
            source_course_dir = search[0]
        # else:
        #     pass #TODO need to download all jsons manually. maybe just a conditional based on truthiness of source_course_dir

        print12(f"json_path: {json_path}")
        print12(f"target_course_dir: {target_course_dir}")
        print12(f"source_course_dir: {source_course_dir}")

        # load from json
        files = {}
        # if json_path.is_file(): # should be...
        json = json_path.read_text()
        files.update(jsonpickle.decode(json))

        # NOTE - if you want to update the json, you're gonna have to update the original dict, NOT the object that you're creating from it.
        # File object will just be to download the file.

        # NOTE - "filepath" from dict entries are a plain string starting from output. so you need to get TARGET_DIR, get its parent,
        # and append the "filepath"

        # EACH FILE
        for id, file_dict in files.items():

            if file_dict["downloaded"] == True:
                print12(f"file {id} at {file_dict["file_path"]} is already downloaded")
                continue

            file = File(requester, file_dict)

            target_file_path = TARGET_DIR.parent / Path(file.file_path) #NOTE assuming that TARGET_DIR is "output" folder, root folder of course downloading...

            # TODO - submission detection? i put id at end, davekats put at front...

            # IF SOURCE DIR FOR COURSE EXISTS
            if source_course_dir:
                # based on how davekats exporter named downloaded files:
                search_pattern = valid_fname(file.display_name)
                if hasattr(file, "tag") and file.tag == "submission":
                    search_pattern = valid_fname(f"{file.id}_{file.og_filename}")

                print12(f"search pattern: {search_pattern}")
                search_file = list(source_course_dir.rglob(search_pattern))
                # if found, compare file size and....
                if len(search_file) != 0:
                    for source_file_path in search_file: 
                    # source_file_path = search_file[0]
                        print12(f"file found at {source_file_path}")

                        source_size = source_file_path.stat().st_size
                        print12(f"source file size: {source_size}")
                        print12(f"expected size: {file.size}")
                        if file.size == source_size:
                            print12(f"size and name matches, moving to {target_file_path}")
                            #move it to target_file_path
                            # mark download = true IN DICT, not object
                            file_dict["downloaded"] = True
                            continue # or early return if function
                        else:
                            print12(f"size does not match.")


            print12(f"file not found in source directory. attempting to download.")
            # ELSE TRY TO DOWNLOAD FROM CANVAS
            if FILE_SIZE_THRESH >= 0 and file.size > FILE_SIZE_THRESH:
                print12(f"{file.filename} - not downloading (over threshold)")
                pass #don't download
            else:
                if not target_file_path.is_file():
                    try:
                        # file.download(target_file_path)
                        pass
                    except Exception as e:
                        pass
                        # file["exception"] = CanvasErrorHandler.handle_exception(
                        #     e, f'file.download({target_file_path})'
                        # )
                        # print message. don't modify dict. well, I guess you can update to exception.
                        # file_dict["downloaded"] = False
                    else:
                        print12(f"Downloaded: {file.filename}")
                        file_dict["downloaded"] = True
                else:
                    print12(f"File Already Exists: {file.filename}")
                    file_dict["downloaded"] = True


        # write back to json path
        # write_obj_json(file_dict, json_path)
        new_json = jsonpickle.encode(files,unpicklable=False, indent=4)
        print12(f"new file dict:\n{new_json}")


    finish_time = datetime.now()
    print12(f'Finished archiving in {finish_time-start_time}')

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