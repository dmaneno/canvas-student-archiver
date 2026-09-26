import re

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