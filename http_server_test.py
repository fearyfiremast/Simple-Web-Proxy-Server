import unittest
import sys

# Declarations
SOCKET = None
REPORT_STATUS = False # if value is true write report
PORT = 8080

class TestPart1(unittest.TestCase):
    def setUp(self):
        return super().setUp()
    
    def tearDown(self):
        return super().tearDown()
    
    def test_GET_method(self):
        print("test run")
        return

def refreshReport():
    if REPORT_STATUS == False:
        return # redundant for now
    return

# project states that we need screenshots of output.
def appendReport():
    if REPORT_STATUS == False:
        return # redundant for now
    return

# entry point
# specific tests can be ran from the command line: https://docs.python.org/3/library/unittest.html
# If report or port number is wanted it is not recommended to use the interface from above link
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1].isdigit() and 0 < int(sys.argv[1]) < 65536:
            PORT = int(sys.argv[1])
    
    unittest.main()
