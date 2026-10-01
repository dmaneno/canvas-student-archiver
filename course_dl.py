import sys
import os
import re
from pathlib import Path
from canvasapi.course import Course
from canvasapi.module import Module, ModuleItem
from canvasapi.discussion_topic import DiscussionTopic
from canvasapi.assignment import Assignment
from canvasapi.file import File
from canvasapi.page import Page
from canvasapi.util import combine_kwargs

from error_handler import CanvasErrorHandler

import jsonpickle
from bs4 import BeautifulSoup

from util import parse_size, valid_fname

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
    def __init__(self, course: Course, course_dir: Path, file_size_thresh: str|int = -1):
        self.course = course
        self._requester = course._requester

        self.course_dir: Path = course_dir
        self.files_dir: Path = course_dir / "files"
        self.files_dir.mkdir(parents=True, exist_ok=True)

        self.files = dict()
        self.pages = dict()
        self.assignments = dict()
        self.discussion_topics = dict()
        self.modules = dict()
        self.module_items = dict()

        # in bytes. -1 = no thresh, 0 = don't download anything, anything higher is regular thresh
        # default is no threshold (-1)
        self.file_size_thresh: int = parse_size(file_size_thresh)
        


    # main method that calls everything else
    def download_resources(self):
        # files
        # only has effect if "files" tab was enabled for course
        print("files...")
        self.download_files()
        # download pages (?)
        # only has effect if the "pages" tab was enabled
        print("pages...")
        self.download_pages()
        # assignments
        print("assignments...")
        self.download_assignments()
        # download announcements, discussion topics
        print("announcements...")
        self.download_announcements()
        print("discussions...")
        self.download_discussion_topics()
        # download modules
        print("modules...")
        self.download_modules()
        # syllabus + home page
        if hasattr(self.course, "syllabus_body"):
            self.course.syllabus_body_mod = self.process_html(self.course.syllabus_body)
        if self.course.default_view == "wiki":
            self.download_page("home")
        # clean course obj and save resources to jsons
        _clean_obj(self.course)
        print("saving jsons...")
        self.save_as_jsons()




    # --------- "batch download" methods ----------------------------------------


    # Does nothing (i.e "files" variable is empty) when File tab of Course is disabled
    def download_files(self):
        count = 0
        try:
            files = self.course.get_files(include = ["user", "usage_rights"])
        except Exception as e:
            # not storing exception message
            CanvasErrorHandler.handle_exception(
                e, f'self.course.get_files(include = ["user", "usage_rights"])'
            )
        else:
            try:
                for file in files:
                    self.download_file(file.id, file)
                    count += 1
            except Exception as e:
                CanvasErrorHandler.handle_exception(
                    e, f'iterating on PaginatedList[File]'
                )
        print(f"{count} files from course.get_files()")


    # Does nothing (i.e "pages" variable is empty) when Pages tab of Course is disabled
    def download_pages(self):
        count = 0
        try:
            pages = self.course.get_pages()
        except Exception as e:
            # not storing exception message
            CanvasErrorHandler.handle_exception(
                e, f'self.course.get_pages()'
            )
        else:
            try:
                for page in pages:
                    self.download_page(page.url, page)
                    count += 1
            except Exception as e:
                CanvasErrorHandler.handle_exception(
                    e, f'iterating on PaginatedList[Page]'
                )
        print(f"{count} pages from course.get_pages()")


    def download_assignments(self):
        count = 0
        try:
           assignments = self.course.get_assignments(
               include=["submission","score_statistics","ab_guid"])
        except Exception as e:
            # not storing exception message
            CanvasErrorHandler.handle_exception(
                e, f'self.course.get_assignments(include=["submission","score_statistics","ab_guid"])'
            )
        else:
            try:
                for assignment in assignments:
                    self.download_assignment(assignment.id, assignment)
                    count += 1
            except Exception as e:
                CanvasErrorHandler.handle_exception(
                    e, f'iterating on PaginatedList[Assignment]'
                )
        print(f"{count} assignments from course.get_assignments()")


    def download_announcements(self):
        count = 0
        try:
            announcements = self.course.get_discussion_topics(
                include = ["sections_user_count","sections","all_dates"], only_announcements=True)
        except Exception as e:
        # not storing exception message
            CanvasErrorHandler.handle_exception(
                e, f'self.course.get_discussion_topics('
                'include = ["sections_user_count","sections","all_dates"], only_announcements=True)'
            )
        else:
            try:
                for announcement in announcements:
                    self.download_discussion_topic(announcement.id, announcement, is_announcement=True)
                    count += 1
            except Exception as e:
                CanvasErrorHandler.handle_exception(
                    e, f'iterating on PaginatedList[DiscussionTopic] (announcements)'
                )
        print(f"{count} announcements from course.get_discussion_topics()")



    def download_discussion_topics(self):
        count = 0
        try:
            topics = self.course.get_discussion_topics(
                include = ["sections_user_count","sections","all_dates"])
        except Exception as e:
            # not storing exception message
            CanvasErrorHandler.handle_exception(
                e, f'self.course.get_discussion_topics('
                'include = ["sections_user_count","sections","all_dates"])'
            )
        else:
            try:
                for topic in topics:
                    self.download_discussion_topic(topic.id, topic)
                    count += 1
            except Exception as e:
                CanvasErrorHandler.handle_exception(
                    e, f'iterating on PaginatedList[DiscussionTopic]'
                )
        print(f"{count} topics from course.get_discussion_topics()")


    def download_modules(self):
        count = 0
        try:
            modules = self.course.get_modules()
        except Exception as e:
            # not storing exception message
            CanvasErrorHandler.handle_exception(
                e, f'self.course.get_modules()'
            )
        else:
            try:
                for module in modules:
                    self.download_module(module.id, module)
                    count += 1
            except Exception as e:
                CanvasErrorHandler.handle_exception(
                    e, f'iterating on PaginatedList[Module]'
                )
        print(f"{count} modules from course.get_modules()")


    def save_as_jsons(self):
        """
        Stores resource dicts / objects into separate jsons in course's folder
        """
        objs = [
            self.course,
            self.files,
            self.pages,
            self.assignments,
            self.discussion_topics,
            self.modules,
            self.module_items,
            ]
        names = [
            "course",
            "files",
            "pages",
            "assignments",
            "discussion_topics",
            "modules",
            "module_items"
        ]
        for obj, name in zip(objs, names):
            filepath = self.course_dir / f"{name}.json"
            _write_obj_json(obj, filepath)




    # --- Atomic resources ----------------------------------------------------------------

    # FOR MOST COURSE RESOURCES:
    # - check if already downloaded/saved to dict
    # - get resource (& save if file)
    # - if resource contains html -> process_html()
    # - if resource contains files -> download_file()
    # - add resource id to dict


    # NOTE: File name should be same / stored in file json for it to be retrieved later
    # by viewer
    def download_file(self, id: int, file: File|None = None, source_name: str|None = None,
                      topic_name: str|None = None, assignment_name: str|None = None) -> bool:
        # Downloads file if it hasn't already been downloaded
        if id in self.files:
            return False

        if not file:
            try:
                file = self.course.get_file(id, include = ["user", "usage_rights"])
            except Exception as e:
                self.files[id] = CanvasErrorHandler.handle_exception(
                    e, f'self.course.get_file({id}, include = ["user", "usage_rights"])'
                )
                return False
        
        parent_dir = self.files_dir

        file.tag = "course" #NOTE: new attribute
        if assignment_name:
            file.tag = "submission"
            parent_dir = parent_dir / "submissions" / assignment_name
            # multiple submissions to same assignment likely have same filename -
            # append ID to end of stem
            file.og_filename = file.filename #NOTE: new attribute
            og = Path(file.og_filename)
            file.filename = f"{og.stem}_{id}{og.suffix}"
        elif topic_name:
            file.tag = "topic_attachment"
            parent_dir = parent_dir / "topic_attachments" / topic_name
        elif source_name:
            file.tag = "other_source"
            parent_dir = parent_dir / "other_sources" / source_name

        folder_path = self.get_full_folder_path(file.folder_id)
        if folder_path:
            parent_dir = parent_dir / folder_path
            
        parent_dir.mkdir(parents=True, exist_ok=True)
        file_path: Path = parent_dir / file.filename

        # size in bytes
        if self.file_size_thresh >= 0 and file.size > self.file_size_thresh:
            print(f"File size is above set threshold; marked as not downloaded")
            file.downloaded = False
        else:
            if not file_path.is_file():
                try:
                    file.download(file_path)
                except Exception as e:
                    file.exception = CanvasErrorHandler.handle_exception(
                        e, f'file.download({file_path})'
                    )
                    file.downloaded = False
                else:
                    print(f"Downloaded: {file.filename}")
                    file.downloaded = True
            else:
                print(f"File Already Exists: {file.filename}")
                file.downloaded = True #NOTE: new attribute

        # Add file info to dict
        file.file_path = str(file_path) #NOTE: new attribute
        self.files[id] = _clean_obj(file)
        return True


    def download_file_by_url(self, url: str, id: int|None = None) -> bool:
        """
        Downloads Canvas files and attachments by url. This includes files that are not directly
        from course files, but are relevant to the course.
        """
        # I'm choosing to deviate from the underlying structure of Canvas's resources since Users
        # are probably a separate DB table from courses, but for the purposes of archiving COURSES
        # I don't really want to bother requesting / storing more information from other users than
        # is necessary.
        # Thus, I'll opt to just request the relevant files directly and store under the Course anyway,
        # instead of doing something like canvas.get_user().get_file().

        # This does make things complicated for accessing via local urls in the viewer... like /files/id
        # needs to direct to the file that's associated with this course?
        # Maybe the resulting dicts are combined on the Canvas level call.
        if not id:
            id = url.split("/files/")[-1].split('/')[0]
        if id in self.files:
            return False

        source = None
        # source_id = None

        if "/courses/" in url:
            self.download_file(id)
        elif "/groups/" in url:
            source = "groups"
            # source_id = url.split("/groups/")[-1].split('/')[0]
        elif "/users/" in url:
            source = "users"
            # source_id = url.split("/users/")[-1].split('/')[0]
        else:
            source = "canvas"
            # source_id = None

        # endpoint apparently works without specifying source
        # endpoint = f'{source}/{source_id}/files/{id}' if source != "canvas" else f'files/{id}'
        endpoint = f'files/{id}'
        try:
            file = self.get_file_from_endpoint(endpoint, include = ["user", "usage_rights"])
        except Exception as e:
            self.files[id] = CanvasErrorHandler.handle_exception(
                e, f'self.get_file_from_endpoint({endpoint}, include = ["user", "usage_rights"])'
            )
            return False
        
        return self.download_file(file.id, file, source_name=valid_fname(source))


    def get_file_from_endpoint(self, endpoint, **kwargs) -> File:
        response = self._requester.request(
            "GET", endpoint, _kwargs=combine_kwargs(**kwargs)
        )
        return File(self._requester, response.json())


    
    def download_attachment(self, attachment_json: dict, topic_name: str|None = None,
                            assignment_name: str|None = None):
        """
        Downloads an attachment file.
        """
        # NOTE: although attachments seem to match attributes of Files in manual tests,
        # the canvas docs show that FileAttachment objects have only 4 of the attributes:
        # content-type, url, filename, display_name.
        # maybe just parse the id from url just in case it isn't there.
        # If you really care about getting the complete file metadata for attachment, just re-call get_file
        if "id" not in attachment_json:
            attachment_json["id"] = attachment_json["url"].split("/files/")[-1].split('/')[0]
        file = File(self._requester, attachment_json)
        topic_name = valid_fname(topic_name)
        assignment_name = valid_fname(assignment_name)
        self.download_file(file.id, file, topic_name=topic_name, assignment_name=assignment_name)
    

    def get_full_folder_path(self, folder_id: int|None) -> Path|None:
        # catches null folder id
        if not folder_id:
            return None
        try:
            folder = self.course.get_folder(folder_id)
        except Exception as e:
            CanvasErrorHandler.handle_exception(e, f"self.course.get_folder({folder_id})")
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
            try:
                page = self.course.get_page(page_url)
            except Exception as e:
                self.pages[page_url] = CanvasErrorHandler.handle_exception(
                    e, f"self.course.get_page({page_url})"
                )
                return False

        page.html_mod = self.process_html(page.body) #NOTE: new attribute

        self.pages[page_url] = _clean_obj(page)
        return True


    def download_assignment(self, id: int, assignment: Assignment|None = None) -> bool:
        if id in self.assignments:
            return False
        # Add to dict with temp value - address case of two resources referring to each
        # other in html content
        self.assignments[id] = None

        if not assignment:
            try:
                assignment = self.course.get_assignment(id, include=["submission","score_statistics","ab_guid"])
            except Exception as e:
                self.assignments[id] = CanvasErrorHandler.handle_exception(
                    e, f'self.course.get_assignment({id}, include=["submission","score_statistics","ab_guid"])'
                )
                return False

        #NOTE: new attribute
        assignment.html_mod = self.process_html(assignment.description)

        if hasattr(assignment, "submission"):
            try:
                assignment.submission_full = assignment.get_submission(
                    assignment.submission["user_id"], include=["submission_history","submission_comments","submission_html_comments",
                    "rubric_assessment","assignment","visibility","course","user","group",
                    "read_status","student_entered_score"]
                )
            except Exception as e:
                assignment.submission_full = CanvasErrorHandler.handle_exception(
                    e, f'assignment.get_submission({assignment.submission["user_id"]}, ' 
                    'include=["submission_history","submission_comments","submission_html_comments",'
                    '"rubric_assessment","assignment","visibility","course","user","group",'
                    '"read_status","student_entered_score"])'
                )
            else:
                # NOTE: perhaps you can also have this as a toggleable option, some users may not care for old submissions
                for submission in assignment.submission_full.submission_history:
                    # submission_full is a Submission object, but the submissions in history are probably still dicts
                    for attachment in submission.get("attachments",[]):
                        # attachments are not guaranteed to be from course
                        self.download_attachment(attachment, assignment_name=assignment.name)

                #NOTE: submission_full also have "submission_html_comments" which contain html content in "comment" attribute
                for comment_obj in assignment.submission_full.submission_html_comments:
                    comment_obj.html_mod = self.process_html(comment_obj.comment) #NOTE: new attribute

                _clean_obj(assignment.submission_full.attachments)
                _clean_obj(assignment.submission_full)
        self.assignments[id] = _clean_obj(assignment)
        return True


    def download_discussion_topic(self, id: int, topic: DiscussionTopic|None = None, is_announcement: bool = False) -> bool:
        if id in self.discussion_topics:
            return False
        self.discussion_topics[id] = None
        if not topic:
            try:
                topic = self.course.get_discussion_topic(id, include = ["sections_user_count","sections", "all_dates"])
            except Exception as e:
                self.discussion_topics[id] = CanvasErrorHandler.handle_exception(
                    e, f'self.course.get_discussion_topic({id}, '
                    'include = ["sections_user_count","sections", "all_dates"])'
                )
                return False
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
        try:
            full_topic: dict = self.course.get_full_discussion_topic(topic.id)
        except Exception as e:
            return CanvasErrorHandler.handle_exception(
                e, f'self.course.get_full_discussion_topic({topic.id})'
            )

        for entry in full_topic.get("view",[]):
            entry["message_mod"] = self.process_html(entry.get("message",""))
            for reply in entry.get("replies",[]):
                reply["message_mod"] = self.process_html(reply.get("message","")) #NOTE: new attribute
            if "attachment" in entry:
                self.download_attachment(entry["attachment"],topic_name=topic.title)
                # -> NOTE: some of these are not associated with the course itself.
                #    either just in "files" broadly, or in user's files.
            # NOTE: according to docs, "attachments" (with 's') is deprecated and redundant,
            # but still gets returned in cached view. I'll just remove it
            if "attachments" in entry:
                entry.pop("attachments")
        
        # Since full_topic is just a dict, no need to call _clean_obj()
        return full_topic


    def download_module(self, id: int, module: Module|None = None) -> bool:
        if id in self.modules:
            return False
        self.modules[id] = None
        if not module:
            try:
                module = self.course.get_module(id)
            except Exception as e:
                self.modules[id] = CanvasErrorHandler.handle_exception(
                    e, f'self.course.get_module({id})'
                )
                return False

        try:
            module_items = module.get_module_items(include=["content_details"])
        except Exception as e:
            module.items = CanvasErrorHandler.handle_exception(
                e, f'module.get_module_items(include=["content_details"])'
            )
        else:
            module.items = []
            try:
                for item in module_items:
                    self.download_module_item(item.id, id, item)
                    module.items.append(item.id) # to make items easier to retrieve from module later
            except Exception as e:
                module.items = CanvasErrorHandler.handle_exception(
                    e, f'iterating on PaginatedList[ModuleItem]'
                )

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
            try:
                # unlike other resources, getting mod item requires both mod item id and mod id
                item = self.course.get_module(module_id).get_module_item(id, include=["content_details"])
            except Exception as e:
                self.module_items[id] = CanvasErrorHandler.handle_exception(
                    e, f'self.course.get_module({module_id}).get_module_item({id}, '
                    'include=["content_details"])'
                )
                return False

        match item.type:
            case "File":
                self.download_file(item.content_id) #NOTE - likely from course, but maybe verify to be sure
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


    def process_html(self, html_content: str|None) -> str:
        # NoneType values
        if not html_content:
            return ""
        print("entering process_html *")

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
        domain = self._requester.original_url
        for link in links:
            if domain in link['href']:
                endpoint = link['data-api-endpoint']
                returntype = link['data-api-returntype']

                # NOTE: need to account for both course files and non-course files
                # (see comment in discussion methods)
                # f"courses/{self.course.id}/..." from old repo may not be necessary

                # https://developerdocs.instructure.com/services/canvas/basics/file.endpoint_attributes
                # NOTE: each returntype can also show up in a list like "[Module]" or "[File]".
                # currently not accounted for... most of these instances are to link to pages like
                # the modules or topics page, which will eventually be taken care of in download_modules(),
                # download_discussion_topics(), etc.
                match returntype:
                    case "File":
                        print("found file")
                        # content_id = int(endpoint.split("/files/")[-1])
                        self.download_file_by_url(endpoint)
                        # self.download_file(content_id) 
                    case "Page":
                        print("found page")
                        page_url = endpoint.split("/pages/")[-1]
                        self.download_page(page_url)
                    case "Assignment":
                        print("found assignment")
                        content_id = int(endpoint.split("/assignments/")[-1])
                        self.download_assignment(content_id)
                    case "Discussion":
                        print("found discussion")
                        content_id = int(endpoint.split('/discussion_topics/')[-1])
                        self.download_discussion_topic(content_id)
                    case "Module":
                        print("found module")
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

                # NOTE: modifying and returning the html using the soup structure doesn't preserve
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
        print("exiting process_html *")
        return output_html