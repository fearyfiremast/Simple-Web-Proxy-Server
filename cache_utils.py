"""Module that handles server cache behaviour"""
import threading
from message_utils import get_date_header, convert_datetime_to_posix

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
    
    def _validate_expiry(self, ):
        #  may cause de
        with self._lock:
            if len(self._records) == 0:
                return
            
        return
    
    def is_cached(self):
        return
    
    def find_record(self):
        with self._lock:
            return
        
        return
    
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


    def is_resource(self, request) -> bool:
        """Checks if the record has the resource by URL"""
        return self._url == request