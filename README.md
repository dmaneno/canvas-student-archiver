# Canvas Student Archiver

This is a Python script enabling students to make a local archive of their Canvas course content -- such as pages, assignments, submissions, and modules -- using the Python wrapper of the official Canvas LMS API, `canvasapi`.

> **This project is still a work in progress** - while the core archiver is mostly functional, there are still plans for improvement in code organization, documentation, features, and extensions. See *Project Progress* for more details.

This archiver uses an HTML-crawling strategy to find additional Canvas resources only accessible to students by direct links in HTML content of pages, assignment descriptions, or other Canvas resource types. (See *More Info* > *Canvas API Quirks* for a more detailed explanation.)

It saves these resources into a hierarchy of organized folders by academic term and course name, with JSON files for each course's resource type and the original course files themselves.

Currently, the archiver will save the following resources it can find from each course:
- files
    - includes submission files and discussion attachments
- pages
- assignments
    - submissions
- discussion topics / announcements
    - includes full discussion thread
- modules
- module items
- the course itself
    - includes metadata, syllabus page html if available 

The data for each individual resource is stored in its JSON form matching the Canvas API documentation (with some additional fields to aid in file management and future html viewing extensions - see *Project Progress*)

> **Note:** Quizzes, while considered Assignment types with Submissions, also have a slightly separate API that I haven't looked into yet. While the archiver does retrieve the "Assignment" and "Submission" related metadata, it does not archive the specific Quizzes content (i.e. questions and submitted answers). I may look into this in the future.

## Setup

- Install Python 3
- Clone this repository
- Run `pip install -r requirements.txt`
- Copy `credentials_template.yaml`, rename to `credentials.yaml`, and fill in with your own credentials and archive preferences. Instructions are in the comments of the template file.
    - To use the archiver, you must either have a Canvas API Access Token or the browser cookies specific to Canvas. See *More Info > Access for Canvas API* for how to find these. 

- OPTIONAL: If you plan to tinker with the code and run the tests, you may want to install `pytest` and `pytest-mock`

## Usage

### In the project root directory:

Archive user's courses to a new `output` folder in the project directory according to configurations in `credentials.yaml`

`python main.py`

Use cookies instead of API token (must be present in `credentials.yaml`)

`python main.py --cookies`

Specify a folder to archive to

`python main.py -o specific_folder`

Specify a yaml config file

`python main.py -c path_to_config_file`

Use verbose output

`python main.py -v`


## More Info
(possibly move to separate md file in a docs folder or something)

### Access for Canvas API

#### User ID

To find your User ID:
- Log onto Canvas
- Navigate to `https://(BASEURL)/api/v1/users/self`, replacing `(BASEURL)` with the base url of your institution's Canvas page. e.g. `canvas.yourschool.edu`
- In the JSON response, find the id field.
    - it may help to click the `Pretty-print` checkbox if your browser has the option

#### Canvas API Access Token

To create or find your access token:
- Log onto Canvas
- Go to `Account > Settings`
- Under `Approved integrations`, click `+ New Access Token`
    - If the button is grayed out, your Canvas admins likely disabled it for students. See *Canvas Cookies*.

#### Canvas Cookies

If you cannot create an access token (e.g. your Canvas admins disabled it for students), then cookies will be necessary to use the API.

The clearest way to find the relevant Canvas cookies is:
- Log onto Canvas
- Navigate to `https://(BASEURL)/api/v1/users/self`, replacing `(BASEURL)` with the base url of your institution's Canvas page. e.g. `canvas.yourschool.edu`
- Open your browser's Developer Tools. Either
    - `Right click > Inspect`
    - `Ctrl + Shift + I`
- In the main toolbar, navigate to the `Application` tab
- Under `Storage` > `Cookies`, you should see a tab for your institution's base url. Click it and you should see the relevant cookies and their values.

From here, you can click on the name of the cookies you need, and from the panel that opens, copy the full value into the respective field in your `credentials.yaml` file. (Keep `Show URL-decoded` unchecked.)

### Canvas API Quirks

(in progress)

#### Resources only available to student by direct link / request

One of the main reasons I decided to write this script was because one of my favorite classes organized its Canvas course content entirely in the syllabus page's HTML, with the associated course files and pages linked in the HTML. It did not use the modules feature.

The first quirk I learned is that if the Files tab is disabled for a course, a student cannot call `course.get_files()` and retrieve a list of all the files for the course, even though files *do* exist for the course. They can only be requested and downloaded by calling `course.get_file(id)` for a specific file. The same is true for other resource types like Pages - if the Pages tab is disabled, `course.get_pages()` doesn't work.

For courses with a modules page, this is easier to work around, since there are API calls to get all the modules, module items, and subsequently the specific resource ids to request. However, for courses like the one above, the only reference to the existing pages, files, etc. for the course were in the HTML itself - thus, it was necessary to design a mechanism to find HTML fields in each Canvas object type, parse the HTML for relevant Canvas links, call the appropriate methods to request the specific resource, and if necessary, parse *that* object's HTML content, and so on.

## Project Progress

### Complete
- Core link-crawling archiver

### In Progress
- "Cookie Patch"
- Code Clean-up
- Documentation
- File Migrator

### Planned
- Load JSON data into SQLite DB
- Local Archive viewer (simple local server) to view and navigate HTML content of Canvas courses. Separate Repository.
- Threaded downloading
- Kaltura Video / Media Gallery Archiver

## Resources

- [davekats/canvas-student-data-export](https://github.com/davekats/canvas-student-data-export)
    - An older canvas data exporting tool. I got the basics of how to use `canvasapi` here. It didn't retrieve all the data I wanted though (in particular the issue mentioned in *More Info > Canvas Quirks*) and it didn't exactly preserve the data in its original format / schema. The script also had some readability / organization issues and overcomplicated some things in my opinion, so I opted to write a separate script.
    - Some code (in particular Canvas API setup and error handling) in this script is based on davekat's script.
- [Canvas LMS Documentation](https://developerdocs.instructure.com/services/canvas)
- [ucfopen/canvasapi](https://github.com/ucfopen/canvasapi) ([documentation](https://canvasapi.readthedocs.io/en/stable/))