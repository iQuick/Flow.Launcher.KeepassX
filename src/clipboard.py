import time
import pyperclip

def copy(data):
    pyperclip.copy(data)


def clear(delay=3):
    time.sleep(delay)
    pyperclip.copy("")


def remove(data, delay=3):
    pass
