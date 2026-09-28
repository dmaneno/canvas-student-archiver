import os
import re
from pathlib import Path
from canvasapi.course import Course
from canvasapi.module import Module, ModuleItem
from canvasapi.discussion_topic import DiscussionTopic
from canvasapi.assignment import Assignment
from canvasapi.file import File
from canvasapi.page import Page

import jsonpickle
from bs4 import BeautifulSoup

from util import parse_size

def _clean_obj(obj: object):
    # python pass-by-object-reference, but return anyway so it can be placed within
    # append statement
    if hasattr(obj, "_requester"):
        delattr(obj, "_requester")
    return obj

def _write_obj_json(obj: object, path: Path):
    json = jsonpickle.encode(obj,unpicklable=False, indent=4)
    with open(path,"w") as out_file:
        out_file.write(json)

def _write_html(html:str, path: Path):
    with open(path,"w") as out_file:
        out_file.write(html)

class CourseDownloader:
    course: Course
    course_dir: Path
    files_dir: Path
    # in bytes. -1 = no thresh, 0 = don't download anything, anything higher is regular thresh
    file_size_thresh: int  

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
    module_items: dict
    # videos
    # media_gallery

    def __init__(self, course: Course, course_dir: Path, file_size_thresh: str|int = -1):
        self.course = course
        self.course_dir = course_dir
        self.files_dir: Path = course_dir / "files"
        self.files_dir.mkdir(parents=True, exist_ok=True)

        # default is no threshold (-1)
        self.file_size_thresh = parse_size(file_size_thresh)
        # submissions, attachments, imgs


    # main method that calls everything else
    def download_resources(self):
        # syllabus + home page
        self.course.syllabus_body_mod = self.process_html(self.course.syllabus_body)
        if self.course.default_view == "wiki":
            self.download_page("home")
        # files
        # only has effect if "files" tab was enabled for course
        self.download_files()
        # download pages (?)
        # only has effect if the "pages" tab was enabled
        self.download_pages()
        # assignments
        self.download_assignments()
        # download announcements, discussion topics
        self.download_announcements()
        self.download_discussion_topics()
        # download modules
        self.download_modules()
        # TODO: clean course obj and save resources to jsons?
        self.save_as_jsons()




    # --------- "batch download" methods ----------------------------------------


    # Does nothing (i.e "files" variable is empty) when File tab of Course is disabled
    def download_files(self):
        files = self.course.get_files(include = ["user", "usage_rights"])
        for file in files:
            self.download_file(file.id, file)


    # Does nothing (i.e "pages" variable is empty) when Pages tab of Course is disabled
    def download_pages(self):
        pages = self.course.get_pages()
        for page in pages:
            self.download_page(page.url, page)


    def download_assignments(self):
        assignments = self.course.get_assignments(include=["submission","score_statistics","ab_guid"])
        for assignment in assignments:
            self.download_assignment(assignment.id, assignment)


    def download_announcements(self):
        announcements = self.course.get_discussion_topics(include = ["sections_user_count","sections","all_dates"], only_announcements=True)
        for announcement in announcements:
            self.download_discussion_topic(announcement.id, announcement, is_announcement=True)


    def download_discussion_topics(self):
        topics = self.course.get_discussion_topics(include = ["sections_user_count","sections","all_dates"])
        for topic in topics:
            self.download_discussion_topic(topic.id, topic)


    def download_modules(self):
        modules = self.course.get_modules()
        for module in modules:
            self.download_module(module.id, module)


    # TODO
    def save_as_jsons(self):
        pass




    # --- Atomic resources ----------------------------------------------------------------

    # FOR MOST COURSE RESOURCES:
    # - check if already downloaded/saved to dict
    # - get resource (& save if file)
    # - if resource contains html -> process_html()
    # - if resource contains files -> download_file()
    # - add resource id to dict


    # NOTE: File name should be same / stored in file json for it to be retrieved later
    # by viewer
    def download_file(self, id: int, file: File|None = None, is_submission: bool = False) -> bool:
        # Downloads file if it hasn't already been downloaded
        if id in self.files:
            return False

        if not file:        
            file = self.course.get_file(id, include = ["user", "usage_rights"])

        # TODO: more types? submission, attachment, image. keep in separate folders?
        # so it may make more sense to change this to a string "file type"
        # embedded images are likely to be downloaded in a different way though.

        file.is_submission = is_submission #NOTE: new attribute
        if is_submission:
            # multiple submissions to same assignment likely have same filename -
            # append ID to end of stem
            file.og_filename = file.filename #NOTE: new attribute
            og = Path(file.og_filename)
            file.filename = f"{og.stem}_{id}{og.suffix}"

        folder_path = self.get_full_folder_path(file.folder_id)
        parent_dir = self.files_dir / folder_path if folder_path else self.files_dir
        parent_dir.mkdir(parents=True, exist_ok=True)
        file_path: Path = parent_dir / file.filename

        # size in bytes
        if self.file_size_thresh >= 0 and file.size > self.file_size_thresh:
            print(f"File size is above set threshold; marked as not downloaded")
            file.downloaded = False
        else:
            if not file_path.is_file():
                file.download(file_path)
                print(f"Downloaded: {file.filename}")
            else:
                print(f"File Already Exists: {file.filename}")
            file.downloaded = True #NOTE: new attribute

        # Add file info to dict
        file.file_path = file_path #NOTE: new attribute
        self.files[id] = _clean_obj(file)
        return True


    def get_full_folder_path(self, folder_id: int|None) -> Path|None:
        # catches null folder id
        if not folder_id:
            return None
        try:
            folder = self.course.get_folder(folder_id)
        except:
            # folder is likely inaccessible to student (unauthorized) - default to None
            return None
        return Path(folder.full_name)


    def download_page(self, page_url: str, page: Page|None = None) -> bool:
        if page_url in self.pages:
            return False
        # Add to dict with temp value - address case of two resources referring to each
        # other in html content
        self.pages[page_url] = None

        if not page:
            page = self.course.get_page(page_url)

        page.html_mod = self.process_html(page.body) #NOTE: new attribute

        self.pages[page_url] = _clean_obj[page]
        return True


    def download_assignment(self, id: int, assignment: Assignment|None = None) -> bool:
        if id in self.assignments:
            return False
        # Add to dict with temp value - address case of two resources referring to each
        # other in html content
        self.assignments[id] = None

        if not assignment:    
            assignment = self.course.get_assignment(id, include=["submission","score_statistics","ab_guid"])

        #NOTE: new attribute
        assignment.html_mod = self.process_html(assignment.description)
        #NOTE: new attribute
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
            comment_obj.html_mod = self.process_html(comment_obj.comment) #NOTE: new attribute

        _clean_obj(assignment.submission_full.attachments)
        _clean_obj(assignment.submission_full)
        self.assignments[id] = _clean_obj[assignment]
        return True


    def download_discussion_topic(self, id: int, topic: DiscussionTopic|None = None, is_announcement: bool = False) -> bool:
        if id in self.discussion_topics:
            return False
        self.discussion_topics[id] = None
        if not topic:
            topic = self.course.get_discussion_topic(id, include = ["sections_user_count","sections", "all_dates"])

        # NOTE: AFAIK, there's no consistent way to know from module item if a topic is an announcement or not
        # (the closest thing is "subscription_hold"). Rely on optional param
        topic.is_announcement = is_announcement #NOTE: new attribute
        topic.html_mod = self.process_html(topic.message) #NOTE: new attribute
        topic.full_topic = self.download_full_discussion_topic(topic) #NOTE: new attribute

        self.discussion_topics[id] = _clean_obj(topic)
        return True


    def download_full_discussion_topic(self, topic: DiscussionTopic) -> dict:
        """
        Retrieves, processes, and returns full view of topic (entries, replies, etc)
        to be stored to topic object.

        This method currently utilizes cached course.get_full_discussion_topic()
        (the other option being DiscussionTopic.get_entries() -> loop with
        DiscussionEntry.get_replies() ).
        """
        # NOTE: This just returns the JSON (in dict form) as is from the response.
        # This means full_topic "attributes" are accessed by *dict keys*, not
        # object attribute dot notation.
        full_topic: dict = self.course.get_full_discussion_topic(topic.id)

        for entry in full_topic["view"]:
            entry["message_mod"] = self.process_html(entry["message"]) #NOTE: new attribute
            for reply in entry["replies"]:
                reply["message_mod"] = self.process_html(reply["message"]) #NOTE: new attribute

        # TODO: download any file attachments
        # -> NOTE: some of these are not associated with the course itself.
        #    either just in "files" broadly, or in user's files. can also be 
        #    located in attachment(s) attribute or inline in the entry message

        # Since full_topic is just a dict, no need to call _clean_obj()
        return full_topic


    def download_module(self, id: int, module: Module|None = None) -> bool:
        if id in self.modules:
            return False
        self.modules[id] = None
        if not module:
            module = self.course.get_module(id)

        module_items = module.get_module_items(include=["content_details"])
        module.items = []
        for item in module_items:
            self.download_module_item(item.id, id, item)
            module.items.append(item.id) # to make items easier to retrieve from module later

        self.modules[id] = _clean_obj(module)
        return True


    def download_module_item(self, id: int, module_id: int, item: ModuleItem|None = None) -> bool:
        """
        Checks what resource type the module item is, downloads the respective resource, and stores
        module item metadata in self.module_items.
        """
        if id in self.module_items:
            return False
        self.module_items[id] = None
        if not item:
            # unlike other resources, getting mod item requires both mod item id and mod id
            item = self.course.get_module(module_id).get_module_item(id, include=["content_details"])

        match item.type:
            case "File":
                self.download_file(item.content_id)
            case "Page":
                self.download_page(item.page_url)
            case "Assignment":
                self.download_assignment(item.content_id)
            case "Discussion":
                self.download_discussion_topic(item.content_id)
            case "SubHeader":
                pass
            # NOTE: consider implementing in future
            case "Quiz":
                # uses content_id
                pass
            case "ExternalUrl":
                # uses external_url
                pass
            case "ExternalTool":
                # uses content_id & external_url
                pass
            case _:
                pass

        self.module_items[id] = _clean_obj(item)
        return True




    # ------ KEY HELPER METHOD


    #TODO
    def process_html(self, html_content: str|None) -> str:
        # NoneType values
        if not html_content:
            return ""

        # find relevant links in html_content, download resource if necessary and modify link to use local.
        # beautifulsoup / regex / string searches
        # links to find:
        # - canvas resource links
        # - embedded images / links
        # - kaltura / video links
        # - external links - if leads to a file, maybe try to download? not sure yet

        output_html = html_content

        soup = BeautifulSoup(html_content, 'lxml')
        links = soup.find_all('a')

        # canvas resource links
        domain = self.course._requester.original_url
        for link in links:
            if domain in link['href']:
                endpoint = link['data-api-endpoint']
                returntype = link['data-api-returntype']

                # NOTE: need to account for both course files and non-course files
                # (see comment in discussion methods)
                # f"courses/{self.course.id}/..." from old repo may not be necessary

                # https://developerdocs.instructure.com/services/canvas/basics/file.endpoint_attributes
                match returntype:
                    case "File":
                        content_id = int(endpoint.split("/files/")[-1])
                        self.download_file(content_id)
                    case "Page":
                        page_url = endpoint.split("/pages/")[-1]
                        self.download_page(page_url)
                    case "Assignment":
                        content_id = int(endpoint.split("/assignments/")[-1])
                        self.download_assignment(content_id)
                    case "Discussion":
                        content_id = int(endpoint.split('/discussion_topics/')[-1])
                        self.download_discussion_topic(content_id)
                    case "Module":
                        content_id = int(endpoint.split('/modules/')[-1])
                        self.download_module(content_id)
                    case "Folder":
                        pass
                    case "Quiz":
                        # uses content_id
                        pass
                    case "SessionlessLaunchUrl":
                        pass
                    # case "SubHeader":
                    #     pass
                    # case "ExternalUrl":
                    #     # uses external_url
                    #     pass
                    # case "ExternalTool":
                    #     # uses content_id & external_url
                    #     pass
                    case _:
                        pass

                # TODO: modifying and returning the html using the soup structure doesn't preserve
                # the original formatting of the input html.
                # Perhaps use soup just for finding necessary information, and then
                # modify and return using basic string / RE searching on a copy of the original html string

                # turn href to local url. maybe save the original in a new attribute "original_href"
                # should be like /courses/:courseid/:resource_type/:id_or_url
                # some original hrefs have additional parameters like "download?wrap=1"
                # link['og_href'] = link['href']
                # domain as stored in _requester.original_url has no trailing '/'
                # so splitting this way keeps the '/' in front of 'courses'
                # (see Canvas.__init__ in canvas.py)
                # link['href'] = link['href'].split(domain)[-1]

                og_href = link['href']
                local_href = link['href'].split(domain)[-1]
                old_attributes = f'"{og_href}"'
                new_attributes = f'"{local_href}" og_href="{og_href}"'

                output_html = output_html.replace(old_attributes, new_attributes)

        # ------ TODO: other types of links and embedded content ------

        # embedded images / links
        imgs = soup.find_all('img')

        # kaltura / video links

        # youtube links - store in case user wants to download bulk with yt-dlp?

        # external links

        # modify and return html from beautifulsoup (NOTE: need to test: do changes 
        # in objects derived from original soup affect the original soup?)
        #  -> yes, but format is not preserved
        # return soup.prettify()
        return output_html