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
    is_future_date
    )

class Cache:
    '''
    Class that stores and allows the retrieval of recently received requests. These requests are
    stored as Records.
    '''
    _max_capacity = 1 # cache capacity
    _records = [] # Stores cached resources
    _lock = threading.Lock()

    def __init__(self):
        return
    
    def _is_expired(self, record):
        """
        TODO
        method that takes as input a record and checks to see if it has expired.
        
        Args:
            record (Record): the record that may or may not have expired

        Returns:
            (bool): True if it has expired, false otherwise
        """
        if type(record) is not Record:
            print("_is_expired: Passed in value is not record. Exiting")
            return
        
        expiry = record.get_expiry()

        # parses str representation of date to datetime obj and passes obj for comparision
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
            self._records.remove(item)

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

                # If the record in cache is expired, it will be marked for removal somehow
                if self._is_expired(record):
                    expired_records.append(record)
                    continue # prevents the case of a record being expired and matching the key
                
                # passes in dict
                if record.is_match(key[1]):
                    to_return = record
                    to_return.update_expiry_date()
                    self._records.remove(record)
                    # Propends record to front to emulate temporal locality
                    self._records = [to_return] + self._records
                    break # We found the record that we wanted so we leave early. 
                    
            self._remove_records(expired_records)
 
        # returns data in a form that calling function can understand
        return to_return
    
    
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

        with self._lock:
            if len(self._records) > self._max_capacity:
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

    def __init__(self, url : str):
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
        self._etag = compute_etag(self._etag, self._vary)
        self.update_expiry_date()

        return

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
    

    def update_expiry_date(self, offset:float=0):
        """ 
        updates the planned expiry of a record by a minimum of 2 minutes.

        Args:
        offset (float): default value is 0. increases the number of seconds until the
                        planned expiry date.

        """
        offset = max(offset, 0) # Clamps offset

        expirydate = datetime.now()
        expirydate = expirydate + timedelta(seconds=(2+offset))
        self._expires = get_date_header(expirydate)


    def is_match(self, dictionary) -> bool:
        """
        Checks if the record has the resource by values in the key
        """
        req_eTag = dictionary["If-None-Match"]
        req_mod_date = dictionary["If-Modified-Since"]

        if req_eTag is not None and req_mod_date is not None:
            return (req_eTag == self._etag) and (req_mod_date == self._last_modified )
            
        elif req_eTag is not None:
           return req_eTag == self._etag
        
        elif req_mod_date is not None:
            return req_mod_date == self._last_modified

        # No valid identifiers
        return False
