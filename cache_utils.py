"""Module that handles server cache behaviour"""
import threading

class Cache:
    '''
    Class that stores and allows the retrieval of recently received requests
    '''
    _max_capacity = 1 # cache capacity
    _records = [] # Stores cached resources
    _lock = threading.Lock()

    def __init__(self):
        return
    
    def is_cached():
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