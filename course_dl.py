import os
import re
from canvasapi.course import Course
from canvasapi.module import ModuleItem

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
    modules: list # just list or dict for ids as well?
    # videos
    # media_gallery

    def __init__(self, course: Course, course_dir: str):
        self.course = course
        self.course_dir = course_dir
        files_dir = os.path.join(course_dir, "files")
        # submissions, attachments, imgs

        # will create necessary course_dir parent directory
        os.makedirs(files_dir, exist_ok=True)

    def download_resources():
        # main method
        # home page / syllabus
        # download pages (?)
        # download assignments
        # download modules
        # download announcements, discussion topics
        # clean course obj?
        pass

    def save_as_jsons():
        pass

    # FOR MOST COURSE RESOURCES:
    # - check if already downloaded/saved to dict
    # - get resource (& save if file)
    # - if resource contains html -> process_html()
    # - if resource contains files -> download_file()
    # - add resource id to dict

    # NOTE: File name should be same / stored in file json for it to be retrieved later
    # by viewer
    def download_file(self, id: int, is_submission: bool = False) -> bool:
        # Downloads file if it hasn't already been downloaded
        if id in self.files:
            return False
        
        file = self.course.get_file(id)
        file.is_submission = is_submission

        file_name = file.filename
        # file_name = util.makeValidFilename(file.filename)
        filepath = os.path.join(self.course_dir, "files", file_name)
        if not os.path.exists(filepath):
            file.download(filepath)
            print(f"Downloaded: {file_name}")
        else:
            print(f"File already exists: {file_name}")

        # Add file info to dict
        self.files[id] = _clean_obj(file)
        return True

    #TODO
    def process_html(self, html_content: str | None) -> str:
        # NoneType values
        if not html_content:
            return ""

        # find relevant links in html_content, download resource if necessary and modify link to use local.
        # beautifulsoup / regex / string searches
        return ""

    def download_page(self, page_url: str) -> bool:
        if page_url in self.pages:
            return False

        # TODO: in the case that process_html() ends up calling download_page() on the same page,
        # (like if two pages refer to each other in their html content), you need to add the page
        # to self.pages dict before calling process_html(), or have a separate "working pages" set
        # where the page is temporarily stored for checking purposes
        
        page = self.course.get_page(page_url)
        page.html_mod = self.process_html(page.body)

        self.pages[page_url] = _clean_obj[page]
        return True

    def download_assignment(self, id) -> bool:
        if id in self.assignments:
            return False
        
        assignment = self.course.get_assignment(id, include=["submission","score_statistics","ab_guid"])
        assignment.html_mod = self.process_html(assignment.description)
        assignment.submission_full = assignment.get_submission(assignment.submission.user_id, include=["submission_history","submission_comments","submission_html_comments",
                                                                  "rubric_assessment","assignment","visibility","course","user","group",
                                                                  "read_status","student_entered_score"])

        # grab file attachments
        # this downloads for all submissions in sub history
        # you may need to attach id to name since they're likely submitted with the same filename.
        # perhaps you can also have this as a togglable option, some users may not care for old submissions
        # TODO
        for submission in assignment.submission_full.submission_history:
            for attachment in submission.attachments:
                self.download_file(attachment.id, is_submission=True)

        #NOTE: submission_full also have "submission_html_comments" which contain html content in "comment" attribute
        for comment_obj in assignment.submission_full.submission_html_comments:
            comment_obj.html_mod = self.process_html(comment_obj.comment)

        _clean_obj(assignment.submission_full.attachments)
        _clean_obj(assignment.submission_full)
        self.assignments[id] = _clean_obj[assignment]
        return True

    def download_module_item(self, item: ModuleItem):
        match item.type:
            case "File":
                self.download_file(item.content_id)
            case "Page":
                self.download_page(item.page_url)
            case "Assignment":
                self.download_assignment(item.content_id)
            # TODO ...
            case "Discussion":
                # uses content_id
                pass
            case "Quiz":
                # uses content_id
                pass
            case "SubHeader":
                pass
            case "ExternalUrl":
                # uses external_url
                pass
            case "ExternalTool":
                # uses content_id & external_url
                pass
            case _:
                pass

        #modify item if necessary (i.e. relative url to the resource)
        # (^ prob not necessary, can be pretty easily recreated from existing details)
        return item


    def download_modules(self):
        modules = self.course.get_modules()
        if not modules:
            print("No modules exist for this course")
            return

        modules_list = []
        for module in modules:
            # retrieve items in module before deleting requester.
            module_items = module.get_module_items(include=["content_details"])
            module.items = []
            for item in module_items:
                # for each item, you should check what type it is and call the respective method
                # to check if exists and if not, retrieve it and store in the respective dictionary
                # for the course.
                self.download_module_item(item)
                module.items.append(_clean_obj(item))
            modules_list.append(_clean_obj(module))
            
        self.modules = modules_list
        