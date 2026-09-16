import pytest
from course_dl import CourseDownloader
from canvasapi.course import Course

@pytest.fixture
def course_downloader(mocker):
    mock_course = mocker.Mock(spec=Course)
    mock_course._requester.original_url = "canvas.mock.edu"
    return CourseDownloader(mock_course, "./test_course")

@pytest.fixture
def html_content_with_all_resource_types():
    html = """

"""
    # TODO
    return html

# test for parsing canvas links from html
# test for properly getting appropriate resource based on api return type
def test_process_html_canvas_links(course_downloader):
    # TODO
    pass



# test for non-canvas links



