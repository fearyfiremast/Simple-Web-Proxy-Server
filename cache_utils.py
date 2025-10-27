"""Module that handles server cache behaviour"""
import threading
from message_utils import is_not_modified_since

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
    
    def _response_to_record(self, response):
        """
        TODO: Converts the socket representation of data to cache representation
        """
        if response is None:
            return
        return

    def find_record(self, key):
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
                
                if record.is_match(key):
                    to_return = record
                    to_return.update_expiry_date()
                    self._records.remove(record)
                    # Propends record to front to emulate temporal locality
                    self._records = [to_return, self._records] 
                    break # We found the record that we wanted so we leave early. 
                    
            self._remove_records(expired_records)
 
        # returns data in a form that calling function can understand
        return self._record_to_response(to_return)
    
    def insert_record(self):
        with self._lock:
            return
        
        return
    

class Record:
    _etag = None
    _date = None
    _expires = None
    _content = None

    def __init__(self, url, modifaction_date, data):
        self._url = url
        self._modification_date = modifaction_date
        self._data = data

    def update_expiry_date(self):
        return


    def is_match(self, key) -> bool:
        """Checks if the record has the resource by URL"""
        return self._url == key