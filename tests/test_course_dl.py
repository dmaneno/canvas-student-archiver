import pytest
import re
from pathlib import Path
from course_dl import CourseDownloader
from canvasapi.course import Course
from canvasapi.requester import Requester
from canvasapi.exceptions import ResourceDoesNotExist, Unauthorized, Forbidden, InvalidAccessToken, CanvasException

# NOTE: view output with pytest -rP (passed), pytest -rX (failed), 
# or pytest -rA (all) after running tests

def test_course_downloader_init_requester():
    course = Course(Requester(base_url="canvas.mock.edu", cookies={}), attributes={})
    downloader = CourseDownloader(course, Path("./test_course"))
    assert course._requester == downloader._requester

@pytest.fixture
def course_downloader(mocker):
    mock_requester = mocker.Mock(spec=Requester)
    mock_requester.original_url = "canvas.mock.edu"
    course = Course(mock_requester, attributes={})
    # course = Course(Requester(base_url="canvas.mock.edu", cookies={}), attributes={})
    # TODO: this does create a real directory that should probably be removed after.
    # 1 - use yield and perform cleanup after
    # 2 - perhaps name the directory with a timestamp to ensure name doesn't
    # collide with an existing directory that happens to have the same name
    return CourseDownloader(course, Path("./test_course"))

def test_download_page_nonexistent(mocker, course_downloader):
    # setup
    mock_api = mocker.patch("course_dl.Course.get_page")
    # mock_api = mocker.patch.object("course_downloader", "")
    mock_api.side_effect = ResourceDoesNotExist("Not Found")

    # run
    flag = course_downloader.download_page("nonexistent-page")

    # assertions
    mock_api.assert_called_once_with("nonexistent-page")
    assert flag == False


@pytest.fixture
def html_content_all_types():
    html = """<div>
    <div>
        <h2>
            <span>Mock Course</span><span>All Course Resource Types</span>
        </h2>
    </div>

    <div>
        <h3>
            Links
        </h3>
        <p>File "24680": <a title="file_24680.pdf"
            href="https://canvas.mock.edu/courses/12345/files/24680/download?wrap=1" 
            data-api-endpoint="https://canvas.mock.edu/api/v1/courses/12345/files/24680" 
            data-api-returntype="File">
            file_24680.pdf
        </a></p>

        <p>Page "week-1": <a title="Week 1 Overview"
            href="https://canvas.mock.edu/courses/12345/pages/week-1" 
            data-api-endpoint="https://canvas.mock.edu/api/v1/courses/12345/pages/week-1" 
            data-api-returntype="Page">
            Week 1 Overview
        </a></p>

        <p>Assignment "77177": <a title="Week 1 Homework"
            href="https://canvas.mock.edu/courses/12345/assignments/77177" 
            data-api-endpoint="https://canvas.mock.edu/api/v1/courses/12345/assignments/77177" 
            data-api-returntype="Assignment">
            Week 1 Homework
        </a></p>

        <p>Discussion Topic "22222": <a title="Week 1 Q&amp;A"
            href="https://canvas.mock.edu/courses/12345/discussion_topics/22222" 
            data-api-endpoint="https://canvas.mock.edu/api/v1/courses/12345/discussion_topics/22222" 
            data-api-returntype="Discussion">
            Week 1 Q&amp;A
        </a></p>

        <p>Module "716": <a title="Week 1 Module"
            href="https://canvas.mock.edu/courses/12345/modules/716" 
            data-api-endpoint="https://canvas.mock.edu/api/v1/courses/12345/modules/716" 
            data-api-returntype="Module">
            Week 1 Module
        </a></p>

        <!-- TODO: Folder, Quiz, SessionlessLaunchUrl -->
        
    </div>
</div>
"""
    return html

# test for parsing canvas links from html
# test for properly getting appropriate resource based on api return type
def test_process_html_canvas_links(mocker, course_downloader, html_content_all_types):
    # Mock atomic resource download methods
    # file, page, assignment, discussion, module
    mock_file_dl = mocker.patch("course_dl.CourseDownloader.download_file_by_url")
    mock_page_dl = mocker.patch("course_dl.CourseDownloader.download_page")
    mock_assignment_dl = mocker.patch("course_dl.CourseDownloader.download_assignment")
    mock_topic_dl = mocker.patch("course_dl.CourseDownloader.download_discussion_topic")
    mock_module_dl = mocker.patch("course_dl.CourseDownloader.download_module")

    # Run on html content
    output = course_downloader.process_html(html_content_all_types)

    # Assertions
    # - all things were called
    # mock_file_dl.assert_called_once_with(24680) # NOTE: process_html now calls download_file_by_url()
    mock_file_dl.assert_called_once_with("https://canvas.mock.edu/api/v1/courses/12345/files/24680")
    mock_page_dl.assert_called_once_with("week-1")
    mock_assignment_dl.assert_called_once_with(77177)
    mock_topic_dl.assert_called_once_with(22222)
    mock_module_dl.assert_called_once_with(716)

    # - html returned is as expected
    # - - no hrefs should still have original domain, i.e. all hrefs should be replaced with local hrefs

    # NOTE: this one doesn't work because string search still matches with 'og_href="http://canvas.mock...'
    # could consider changing og_href to a different attribute name but not sure what else to call it yet
    # assert 'href="https://canvas.mock.edu/courses' not in output

    assert len(re.findall('href="/courses/', output)) == 5
    assert len(re.findall('og_href="https://canvas.mock.edu/courses/', output)) == 5
    # not the most thorough check tbh, but could do a separate parametrized test to check specific
    # resource types hrefs are properly being modified
    
    # NOTE: the specific formatting of the output (i.e. order of attributes) is not checked
    # in this test, though it is preferred to preserve the original formatting if possible.
    print(output)




# test for non-canvas links



