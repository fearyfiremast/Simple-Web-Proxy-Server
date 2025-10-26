import unittest
import subprocess
import sys

# Declarations
REPORT_STATUS = True # if value is true write report
REPORT_NAME = "results.txt"

PORT = 8080
HOST = "127.0.0.1"
DESTINATION = None
RESOURCE = "/test.html"

class TestPart1(unittest.TestCase):
    '''
        This class is responsible for performing unit tests related to part one of the assignments.
        This includes, verifying server response for the HTTP GET method and codes 200, 304, 403,
         404, and 505.\n

        Extends the unittest.TestCase class.
    '''

    def setUp(self):
       global DESTINATION
       DESTINATION = f"http://{HOST}:{PORT}{RESOURCE}"
    
    def tearDown(self):
        return super().tearDown()
    
    def test_GET_method_header_proper(self):
        '''
            unit test that verifies if the header is well formed
        '''
        # cannot use -I or --head commands because curl sends a HEAD
        # method not a GET method
        cmd = [
            "curl",
            "-i",
            f"{DESTINATION}"
        ]
        result = capture_package_values(cmd)
        append_report("SERVER GET 200 OK RESPONSE", result)
        result = result.split("\n")

        # Goes through each header field and checks for expected response
        self.assertEqual(result[0], "HTTP/1.1 200 OK")
        self.assertEqual(result[1], "Content-Type: text/html")
        self.assertEqual(result[2], "Content-Length: 327")
        self.assertEqual(result[3], "Connection: close")

    
    def test_GET_method_body_proper(self):
        '''
            unit test that verifies if the payload was delivered as expected
        '''
        cmd = [
            "curl",
            f"{DESTINATION}"
        ]
        result = capture_package_values(cmd)
        with open("./test.html", mode='r') as test_html:
            data = test_html.read()
            self.assertEqual(data.split("\n"), result.split("\n"))

def refresh_report():
    if REPORT_STATUS == False:
        return # redundant for now

    open("report.txt", "w").close()
    return

# project states that we need screenshots of output.
def append_report(title : str, content : str):
    if REPORT_STATUS == False:
        return # report unwanted

    with open(REPORT_NAME, "a") as data:
        title = "-- TITLE: " + title + "--\n"
        content += "\n"
        data.write(title)
        data.write(content)

    return

def capture_package_values(cmd : list):
    '''
        runs a subprocess and returns its output as text.

        Args:
            cmd (list): A list that contains a command as well as its arguments.

        Returns:
            The output of cmd as a string.
    '''
    toReturn = (subprocess.run(cmd, capture_output=True, text=True)).stdout
    return toReturn

# entry point
# specific tests can be ran from the command line: https://docs.python.org/3/library/unittest.html
# If report or port number is wanted it is not recommended to use the interface from above link

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # may cause errors with unittest sys.argv implementation
        if sys.argv[1].isdigit() and 0 < int(sys.argv[1]) < 65536:
            PORT = int(sys.argv[1])
            del sys.argv[1]

    refresh_report()
    unittest.main()
