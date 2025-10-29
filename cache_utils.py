"""Module that handles server cache behaviour"""

import threading
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# Project imports
from header_utils import (
    get_date_header,
    get_last_modified_header,
    compute_etag,
    acquire_resource,
    is_future_date,
)


DEFAULT_TTL_SECONDS = 60  # default freshness lifetime for cached records


class Cache:
    """
    Class that stores and allows the retrieval of recently received requests. These requests are
    stored as Records.
    """

    _max_capacity = 2  # cache capacity
    _records = []  # Stores cached resources
    _lock = threading.Lock()

    def __init__(self):
        return
    
    def _change_base_TTL(self, val):
        """ Testing method to change the TTL from client"""
        global DEFAULT_TTL_SECONDS
        DEFAULT_TTL_SECONDS = val

    def _is_expired(self, record):
        """
        method that takes as input a record and checks to see if it has expired.

        Args:
            record (Record): the record that may or may not have expired

        Returns:
            (bool): True if it has expired, false otherwise
        """
        if type(record) is not Record:
            # print("_is_expired: Passed in value is not record. Exiting")
            return True

        expiry = record.get_expiry()
        # Parse str representation of date to datetime obj and check if it's in the past
        # Expired when expiry is NOT in the future
        return not is_future_date(parsedate_to_datetime(expiry))

    def _remove_records(self, array):
        """
        Removes records in the passed array from _records list.

        Precondition:
            function is called while only one thread controls access to the _records
            list.

        Args:
            array (list): contains a list of items that are also in the _records list.
                          must be iterable.
        """
        if len(array) < 1:
            return

        for item in array:
            try:
                self._records.remove(item)
                
            except(ValueError):
                continue

        return

    def find_record(self, key):
        """
        Searches cache data structure for a record with matching key as attribute.

        Args:
            key dict: contains the request header fields

        Returns:
            A record if there was a match. If not then returns None
        """

        to_return = None
        expired_records = []

        with self._lock:
            # Early exit
            if len(self._records) == 0:
                return None

            for record in self._records:
                # print(f"Checking record: {record}")  # Debug print

                # If the record in cache is expired, it will be marked for removal somehow
                if self._is_expired(record):
                    expired_records.append(record)
                    # print("Record expired, marking for removal")  # Debug print
                    continue  # prevents the case of a record being expired and matching the key

                # passes in dict
                if record.is_match(key):
                    to_return = record
                    self._records.remove(record)
                
                    self._records = [to_return] + self._records
                    break  # We found the record that we wanted so we leave early.

            self._remove_records(expired_records)

        # returns data in a form that calling function can understand
        return to_return

    def print_cache(self):
        """
        Prints the current cache contents to the console.
        """
        with self._lock:
            print("Cache contents:")
            for record in self._records:
                print(record)
        return

    def insert_response(self, record):
        """
        Inserts an record object into the cache for later retrieval.
        If the cache is full removes all expired records or oldest record.

        Args:
            record (Record): the record to be inserted
        """
        if type(record) is not Record:
            print("insert_response: Passed in value is not record. Exiting")
            return

        if self._max_capacity <= 0:
            return

        with self._lock:
            if len(self._records) >= self._max_capacity:
                expired_records = []

                # Expunge expired records
                for item in self._records:
                    if self._is_expired(item):
                        expired_records.append(item)

                # True if an expired record was found
                if len(expired_records) > 0:
                    self._remove_records(expired_records)

                # No records to expire. Pop oldest
                else:
                    self._records.pop()

            # Element insertion and formats the response into a record
            self._records = [record] + self._records
        return

    def clear_cache(self):
        """
        Clears all records from the cache.
        """
        with self._lock:
            self._records = []
        return
    
    def evict_expired(self):
        """
        Evicts expired records from cache. For use in testing
        """
        with self._lock:
            expired_records = []
            for record in self._records:
                if self._is_expired(record):
                    expired_records.append(record)

            
            # True if an expired record was found
            if len(expired_records) > 0:
                self._remove_records(expired_records)
       
        return


class Record:
    """
    Internal representation of requests
    """

    _etag = None
    _last_modified = None
    _vary = None
    _expires = None
    _content_type = None
    _content = None
    # Request identity used to match cache entries
    _method = None
    _url = None
    _version = None
    _req_headers = None  # subset of request headers that affect representation (e.g., Accept-Encoding)

    def __init__(
        self,
        url: str,
        method: str = "GET",
        version: str = "HTTP/1.1",
        req_headers: dict | None = None,
    ):
        """
        Constructor for the Record class

        Args:
            url (str): the absolute path of the file we want to acquire

        Returns:
            a fully formed record object
        """
        retrieved = acquire_resource(url)

        # Setting up fields
        self._content = retrieved[0]
        self._content_type = retrieved[1]
        self._last_modified = get_last_modified_header(url)
        self._vary = "Accept-Encoding"
        self._etag = compute_etag(self._content, self._vary)
        self.update_expiry_date()
        # identity
        self._method = (method or "GET").upper()
        self._url = url
        self._version = (version or "HTTP/1.1").upper()
        # Keep only headers that influence representation (currently Accept-Encoding)
        if isinstance(req_headers, dict):
            ae = None
            for k, v in req_headers.items():
                if isinstance(k, str) and k.lower() == "accept-encoding":
                    ae = v
                    break
            self._req_headers = {"Accept-Encoding": ae} if ae is not None else {}
        else:
            self._req_headers = {}

        return

    def __str__(self):
        return f"""
            method: {self._method}\n
            url: {self._url}\n
            version: {self._version}\n
            etag: {self._etag}\n
            last_modified: {self._last_modified}\n
            vary: {self._vary}\n
            expires: {self._expires}\n
            content_type: {self._content_type}\n
            content: {self._content}\n
            """

    def get_expiry(self) -> str:
        """
        Returns the expiry of the record in date format.

        Returns:
            string expression of expiry date.
            ex: 'Mon, Apr 17 ...'
        """
        return self._expires

    def get_etag(self):
        """
        Gets the etag

        Returns:
            (int)
        """
        return self._etag

    def get_last_modified(self):
        """
        Gets the date of most recent modification

        Returns:
            (str)
        """
        return self._last_modified

    def get_vary(self):
        """
        Gets the vary

        Returns:
            (str)
        """
        return self._vary

    def get_content_type(self):
        """
        Gets the content type

        Returns:
            (str)
        """
        return self._content_type

    def get_content(self):
        """
        Gets the content

        Returns:
            (str)
        """
        return self._content

    def update_expiry_date(self, offset: float = 0):
        """
        Updates the planned expiry of a record by a default TTL.

        Args:
            offset (float): additional seconds to extend the planned expiry date.

        """
        offset = max(offset, 0)  # Clamps offset
        expirydate = datetime.now()
        # Use a sensible default TTL; offset can extend it
        expirydate = expirydate + timedelta(seconds=(DEFAULT_TTL_SECONDS + offset))
        self._expires = get_date_header(expirydate)

    @staticmethod
    def _extract_request_line(key: dict):
        """Extract (method, url, version) from key.

        Supports either:
        - {"request_line": "GET /abs/path HTTP/1.1"}
        - {"method": "GET", "url": "/abs/path", "version": "HTTP/1.1"}
        Returns (method, url, version) with method/version uppercased; values may be None.
        """
        if not isinstance(key, dict):
            return None, None, None
        method = url = version = None
        rl = key.get("request_line")
        if isinstance(rl, str):
            parts = rl.strip().split()
            if len(parts) >= 3:
                method, url, version = parts[0], parts[1], parts[2]
        else:
            method = key.get("method")
            url = key.get("url")
            version = key.get("version")
        method = method.upper() if isinstance(method, str) else None
        version = version.upper() if isinstance(version, str) else None
        return method, url, version

    def is_match(self, key) -> bool:
        """True if request identity (method,url,version) and Vary headers match.

        Validators (If-None-Match / If-Modified-Since) are not used for identity. Use them
        after a cache hit to decide 200 vs 304.
        """
        method, url, version = self._extract_request_line(
            key if isinstance(key, dict) else {}
        )

        # print(f"Is Match: searching for {method} {url} {version}")  # Debug print
        # Require request line match if provided
        if method is not None and method != self._method:
            return False
        if url is not None and url != self._url:
            return False
        if version is not None and version != self._version:
            return False

        # Compare Accept-Encoding if present in record
        key_headers = {}
        if isinstance(key, dict):
            hdrs = key.get("headers") if "headers" in key else key
            if isinstance(hdrs, dict):
                key_headers = {
                    k.lower(): v for k, v in hdrs.items() if isinstance(k, str)
                }

        rec_ae = (
            self._req_headers.get("Accept-Encoding")
            if isinstance(self._req_headers, dict)
            else None
        )
        if rec_ae is not None:
            req_ae = key_headers.get("accept-encoding")
            if req_ae != rec_ae:
                return False

        return True

    def is_newer_than(self, header_str: str):
        if header_str is None or header_str == "N/A":
            return False

        # Has operator overloading for inequality
        return parsedate_to_datetime(self._last_modified) > parsedate_to_datetime(
            header_str
        )
