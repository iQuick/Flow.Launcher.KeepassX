import os
import sys
import subprocess


def edittext(file_path):
    if sys.platform.startswith('win'):
        # Windows
        subprocess.run(['start', file_path], shell=True)
    elif sys.platform.startswith('darwin'):
        # macOS
        subprocess.run(['open', file_path])
    else:
        # Linux
        subprocess.run(['xdg-open', file_path])


if __name__ == '__main__':
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        edittext(sys.argv[1])
    