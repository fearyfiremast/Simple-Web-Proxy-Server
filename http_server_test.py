import unittest
import sys

def main():
    print("hello")

# entry point
if __name__ == "__main__":
    # default case - runs all
    if len(sys.argv) > 1:
        main()

    # implement specifc test args here
    else:
        main()