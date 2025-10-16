import sys
import time
import pyperclip

def clear_clipboard(delay=3):
    print(f'clear clipboard on time : {delay}')
    time.sleep(delay)
    pyperclip.copy("")

if __name__ == '__main__':
    try:
        clear_clipboard(int(sys.argv[1]))
    except:
        clear_clipboard()

