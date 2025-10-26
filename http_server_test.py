import unittest
import subprocess
import sys

# Declarations
REPORT_STATUS = False # if value is true write report
PORT = 8080
HOST = "127.0.0.1"
DESTINATION = None
RESOURCE = "/test.html"

def capture_package_values(cmd : list, delimiter='\r\n') -> subprocess.CompletedProcess:
    toReturn = (subprocess.run(cmd, capture_output=True, text=True)).stdout
    return toReturn.split(delimiter)

class TestPart1(unittest.TestCase):

    def setUp(self):
       global DESTINATION
       DESTINATION = f"http://{HOST}:{PORT}{RESOURCE}"
    
    def tearDown(self):
        return super().tearDown()
    

    
    def test_GET_header_method(self):
        # test does not need bespoke 
        cmd = [
            "curl",
            "--head",
            f"{DESTINATION}"
        ]
        result = capture_package_values(cmd, "\n")
        self.assertEqual(result[0], "HTTP/1.1 200 OK")
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
        # may cause errors with unittest sys.argv implementation
        if sys.argv[1].isdigit() and 0 < int(sys.argv[1]) < 65536:
            PORT = int(sys.argv[1])
            del sys.argv[1]

    unittest.main()
