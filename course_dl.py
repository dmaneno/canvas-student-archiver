import os
import re
from canvasapi.course import Course

import jsonpickle

def _clean_obj(obj: object):
    # python pass-by-object-reference, but return anyway so it can be placed within
    # append statement
    if hasattr(obj, "_requester"):
        delattr(obj, "_requester")
    return obj

def _write_obj_json(obj: object, path: str):
    json = jsonpickle.encode(obj,unpicklable=False, indent=4)
    with open(path,"w") as out_file:
        out_file.write(json)

def _write_html(html:str, path:str):
    with open(path,"w") as out_file:
        out_file.write(html)

class CourseDownloader:
    course: Course
    course_dir: str

    # Store each dict into a separate json in course's folder
    course_dict: dict  #<- hm, maybe this one should be in the top level for the output folder.
    #( most of below are int(id) to response.json() which could be list or dict)
    pages: dict
    files: dict
    assignments: dict
    # submissions: dict
    discussion_topics: dict
    announcements: dict
    modules: dict
    # videos
    # media_gallery

    def __init__(self, course: Course, course_dir: str):
        self.course = course
        self.course_dir = course_dir
        files_dir = os.path.join(course_dir, "files")
        # submissions, attachments, imgs

        # will create necessary course_dir parent directory
        os.makedirs(files_dir, exist_ok=True)

    def download_file(self, content_id: int) -> bool:
        # Downloads file if it hasn't already been downloaded
        if content_id in self.files:
            return False
        file = self.course.get_file(content_id)
        file_name = file.filename
        # file_name = util.makeValidFilename(file.filename)
        filepath = os.path.join(self.course_dir, "files", file_name)
        if not os.path.exists(filepath):
            file.download(filepath)
            print(f"Downloaded: {file_name}")
        else:
            print(f"File already exists: {file_name}")

        # Add file info to dict
        self.files[content_id] = _clean_obj(file)
        return True

    

    