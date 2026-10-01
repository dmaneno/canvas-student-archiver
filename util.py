import re
import unicodedata
import string
import jsonpickle
from pathlib import Path

# based on - https://stackoverflow.com/a/60708339
units = {"B": 1, "KB": 2**10, "MB": 2**20, "GB": 2**30, "TB": 2**40}

#TODO: more robust input validation / exception handling
def parse_size(size: str|int) -> int:
    """
    Converts human-readable file size string into bytes (int).

    Unit conversions are based on binary system, not decimal. Even though
    most OS's use the decimal label, it usually is binary under the hood.
    """
    # assumes an int value or digit string is already in bytes
    if isinstance(size,int):
        return size
    if size.isdigit():
        return int(size)

    size = size.upper()
    if not re.match(r' ', size):
        size = re.sub(r'([KMGT]?B)', r' \1', size)
    number, unit = [string.strip() for string in size.split()]

    b_size = None
    try:
        b_size = int(float(number)*units[unit])
    except:
        raise ValueError(f"Invalid file size string")
    return b_size

# based on code from https://github.com/davekats/canvas-student-data-export/blob/master/export.py
def valid_fname(input_str: str|None) -> str|None:
    if not input_str:
        return None

    # Normalize Unicode and whitespace
    input_str = unicodedata.normalize('NFKC', input_str)
    input_str = input_str.replace("\u00A0", " ") # NBSP to space
    input_str = re.sub(r"\s+", " ", input_str)

    # Remove invalid characters
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    input_str = input_str.replace("+"," ") # Canvas default for spaces
    input_str = input_str.replace(":","-")
    input_str = input_str.replace("/","-")
    input_str = "".join(c for c in input_str if c in valid_chars)

    # Remove leading and trailing whitespace
    input_str = input_str.lstrip().rstrip()

    # Remove trailing periods
    input_str = input_str.rstrip(".")

    return input_str

# based on code from https://github.com/davekats/canvas-student-data-export/blob/master/export.py
def valid_folder(input_str: str|None) -> str|None:
    # Normalize Unicode and whitespace
    input_str = unicodedata.normalize('NFKC', input_str)
    input_str = input_str.replace("\u00A0", " ") # NBSP to space
    input_str = re.sub(r"\s+", " ", input_str)

    # Remove invalid characters
    valid_chars = "-_.()/ %s%s" % (string.ascii_letters, string.digits)
    input_str = input_str.replace("+"," ") # Canvas default for spaces
    input_str = input_str.replace(":","-")
    input_str = "".join(c for c in input_str if c in valid_chars)

    # Remove leading and trailing whitespace, separators
    input_str = input_str.lstrip().rstrip().strip("/").strip("\\")

    # Remove trailing periods
    input_str = input_str.rstrip(".")

    # Replace path separators with OS default
    input_str=input_str.replace("/",os.sep)

    return input_str

# based on code from https://github.com/davekats/canvas-student-data-export/blob/master/export.py
# Max PATH length is 260 characters on Windows. 70 is just an estimate for a reasonable max folder name to prevent the chance of reaching the limit
# Applies to modules, assignments, announcements, and discussions
# If a folder exceeds this limit, a "-" will be added to the end to indicate it was shortened ("..." not valid)
MAX_FNAME_SIZE = 70
def short_fname(string: str|None) -> str:
    """
    Shortens filename, if necessary.
    """
    if not string:
        return string
    shorten_by = len(string) - MAX_FNAME_SIZE
    if shorten_by <= 0:
        return string
    # Shorten string by specified value + 1 for "-" to indicate incomplete file name (trailing periods not allowed)
    string = string[:len(string)-(shorten_by + 1)]
    string = string.rstrip().rstrip(".").rstrip("-")
    string += "-"
    return string

def clean_obj(obj: object):
    # python pass-by-object-reference, but return anyway so it can be placed within
    # append statement
    if hasattr(obj, "_requester"):
        delattr(obj, "_requester")
    return obj

def write_obj_json(obj: object, path: Path):
    json = jsonpickle.encode(obj,unpicklable=False, indent=4)
    with open(path,"w") as out_file:
        out_file.write(json)