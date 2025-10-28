"""Module that handles server cache behaviour"""
import threading
from datetime import datetime

# Project imports
from header_utils import (
    is_not_modified_since, 
    get_date_header,
    get_last_modified_header,
    compute_etag,
    acquire_resource
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
            
        return
    
    def _remove_records(self, array):
        """
        TODO: Removes records from _records list
        """
        return
    
    def _record_to_response(self, record):
        """
        TODO: Converts the cache representation of data to socket representation
        """
        if record is None:
            return
        
        return 
    def find_record(self, key):
        """
        Searches cache data structure for a record with matching key as attribute.

        Args:
            key dict: contains the request header fields

        Returns:

        """

        to_return = None
        expired_records = []

        with self._lock:
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
        return self._record_to_response(to_return)
    
    def insert_response(self, response):
        
        # Formats the response into a record
        to_insert = Record(response)

        with self._lock:
            if len(self._records) > self._max_capacity:
                expired_records = []

                # Expunge expired records
                for record in self._records:
                    if self._is_expired(record):
                        expired_records.append(record)
                
                # True if an expired record was found
                if len(expired_records) > 0:
                    self._remove_records(expired_records)

                # No records to expire. Pop oldest
                else:
                    self._records.pop()

            # Element insertion
            self._records = [to_insert] + self._records
        return
    
class Record:
    _etag = None
    _last_modified = None
    _vary = None
    _expires = None
    _content_type = None
    _content = None

    def __init__(self, url):
        retrieved = acquire_resource(url)
        
        self._content = retrieved[0]
        self._content_type = retrieved[1]
        self._last_modified = get_last_modified_header(url)
        #self._etag = compute_etag()
        return


    def update_expiry_date(self):
        return

    def is_match(self, dictionary) -> bool:
        """Checks if the record has the resource by values in the key"""
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