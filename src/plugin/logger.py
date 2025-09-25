import os
import sys
import subprocess



if __name__ == '__main__':
    if len(sys.argv) > 2:
        with open(sys.argv[1], "a") as f:
            f.write(sys.argv[2])
    