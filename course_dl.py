import os
import re
from canvasapi.course import Course
from canvasapi.module import ModuleItem
from canvasapi.discussion_topic import DiscussionTopic

import jsonpickle
from bs4 import BeautifulSoup

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
    # in bytes. -1 = no thresh, 0 = don't download anything, anything higher is regular thresh
    # TODO: give option to enter and convert string value like 500mb, 2gb, etc. 
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
    modules: list # just list or dict for ids as well?
    # videos
    # media_gallery

    def __init__(self, course: Course, course_dir: str, file_size_thresh: int = -1):
        self.course = course
        self.course_dir = course_dir
        files_dir = os.path.join(course_dir, "files")
        self.file_size_thresh = file_size_thresh # default is no threshold
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
        
        file = self.course.get_file(id, include = ["user", "usage_rights"])
        # TODO: more types? submission, attachment, image. keep in separate folders?
        # so it may make more sense to change this to a string "file type"
        # embedded images are likely to be downloaded in a different way though.
        file.is_submission = is_submission

        file_name = file.filename
        # NOTE: from old repo. check if necessary to keep
        # file_name = util.makeValidFilename(file.filename)
        filepath = os.path.join(self.course_dir, "files", file_name)

        # size in bytes
        if self.file_size_thresh > -1 and file.size > self.file_size_thresh:
            print(f"File size is above set threshold; marked as not downloaded")
            file.downloaded = False
        else:
            if not os.path.exists(filepath):
                file.download(filepath)
                print(f"Downloaded: {file_name}")
            else:
                print(f"File already exists: {file_name}")
            file.downloaded = True

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
        # links to find:
        # - canvas resource links
        # - embedded images / links
        # - kaltura / video links
        # - external links - if leads to a file, maybe try to download? not sure yet

        soup = BeautifulSoup(html_content, 'lxml')
        links = soup.find_all('a')

        # canvas resource links
        for link in links:
            if self.course._requester.original_url in link['href']:
                endpoint = link['data-api-endpoint']
                returntype = link['data-api-returntype']

                # NOTE: need to account for both course files and non-course files
                # (see comment in discussion methods)
                # f"courses/{self.course.id}/..." from old repo may not be necessary

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

                # turn href to local url. maybe save the original in a new attribute "original_href"


        # embedded images / links
        imgs = soup.find_all('img')

        # kaltura / video links

        # youtube links - store in case user wants to download bulk with yt-dlp?

        # external links

        # modify and return html from beautifulsoup (NOTE: need to test: do changes 
        # in objects derived from original soup affect the original soup?)

        return ""

    def download_page(self, page_url: str) -> bool:
        if page_url in self.pages:
            return False
        # Add to dict with temp value - address case of two resources referring to each
        # other in html content
        self.pages[page_url] = None
        
        page = self.course.get_page(page_url)
        page.html_mod = self.process_html(page.body)

        self.pages[page_url] = _clean_obj[page]
        return True

    def download_assignment(self, id) -> bool:
        if id in self.assignments:
            return False
        # Add to dict with temp value - address case of two resources referring to each
        # other in html content
        self.assignments[id] = None
        
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

    # downloads cached view and stores to Topic object. including announcements.
    # - this method currently utilizes cached course.get_full_discussion_topic(), but
    # - could also use DiscussionTopic.get_entries() -> DiscussionEntry.get_replies()
    def download_full_discussion_topic(self, topic: DiscussionTopic) -> bool:
        # this just returns the JSON (in dict form) as is from the response, so
        # no need to call _clean_obj() later
        full_topic = self.course.get_full_discussion_topic(topic.id)
        # TODO: html / text components to check: entry messages, replies
        # -> NOTE: main message is actually in the topic itself, not here.
        # TODO: download any file attachments
        # -> NOTE: some of these are not associated with the course itself.
        #    either just in "files" broadly, or in user's files. can also be 
        #    located in attachment(s) attribute or inline in the entry message
        topic.full_topic = full_topic
        return True

    # NOTE: currently I'm not expecting to have to request discussion topic objects individually
    # i.e. with course.get_discussion_topic(id) so for now there's no method for that in this class
    # This would become necessary if somehow a discussion topic link is found elsewhere (i.e. in modules)
    # while not being retrievable through download_discussion_topics() somehow.

    # this should be run if encountered in module item. modules should be retrieved after
    # download_discussion_topics() and download_announcements() are already run, so we can
    # minimize the requests done one-by-one. Not sure if there's actually any performance advantage
    # of downloading all at once, but it seems more convenient.
    def download_discussion_topic(self, id: int) -> bool:
        if id in self.discussion_topics:
            return False
        topic = self.course.get_discussion_topic(id)
        # NOTE: AFAIK, there's no way to know from module item if a topic is an announcement or not
        topic.is_announcement = False
        self.download_full_discussion_topic(topic)
        self.discussion_topics[id] = _clean_obj(topic)

    def download_discussion_topics(self):
        topics = self.course.get_discussion_topics(include = ["sections_user_count","sections"])
        for topic in topics:
            self.discussion_topics[topic.id] = None
            topic.is_announcement = False
            self.download_full_discussion_topic(topic)
            self.discussion_topics[topic.id] = _clean_obj(topic)

    def download_announcements(self):
        announcements = self.course.get_discussion_topics(include = ["sections_user_count","sections"], only_announcements=True)
        for announcement in announcements:
            self.discussion_topics[announcement.id] = None
            announcement.is_announcement = True
            self.download_full_discussion_topic(announcement)
            self.discussion_topics[announcement.id] = _clean_obj(announcement)
        

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
                self.download_discussion_topic(item.content_id)
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
        