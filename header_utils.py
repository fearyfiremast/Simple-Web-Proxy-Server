from email.utils import formatdate, parsedate_to_datetime
from os.path import getmtime
from time import time
from datetime import datetime

CACHE_REQ_FIELDS = ["If-None-Match", "If-Modified-Since", "Vary"]

def get_date_header(date=None):
    """Generate a Date header for HTTP response.
    Args:
        date(datetime): is None by default. Otherwise function will get the posix time of the
        object and return it as a formatted date.
    
    Returns:
        str: The Date header string.
    """
    if date is None:
        date = time()
    else:
        date = date.timestamp()

    return formatdate(timeval=date, localtime=False, usegmt=True)


def is_not_modified_since(filepath, ims_header):
    """Check if the file has been modified since the time specified in the If-Modified-Since header.

    Args:
        filepath (str): The path to the file.
        ims_header (str): The value of the If-Modified-Since header.

    Returns:
        bool: True if the file has been modified since the specified time, False otherwise.
    """
    try:
        ims_time = parsedate_to_datetime(ims_header).timestamp()
        file_mtime = getmtime(filepath)
        return file_mtime <= ims_time
    except (TypeError, ValueError):
        return True  # If parsing fails, assume modified


def get_last_modified_header(filepath):
    """Generate a Last-Modified header for a given file.

    Args:
        filepath (str): The path to the file.

    Returns:
        str: The Last-Modified header string.
    """
    last_modified_time = getmtime(filepath)
    return formatdate(timeval=last_modified_time, localtime=False, usegmt=True)

def convert_datetime_to_posix(datetime):
    """
    Converts a datetime object to a number signifying POSIX time
    Args:
        datetime: datetime object
    
    Returns:
        POSIX time (number)
    """
    return parsedate_to_datetime(datetime).timestamp()

def convert_reqheader_into_dict(to_convert : list):
    to_return = {}
    for header in CACHE_REQ_FIELDS:
        # Default behaviour is to print "N/A" if value
        # is not in dict. None is prefered of NA.
        to_return[header] = None

    for line in to_convert:
        if line == "":
            break

        key, value = line.split(":", 1)
        to_return[key.strip()] = value.strip()

    return to_return