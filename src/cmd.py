import json
import os
import subprocess
import sys

from . import logger


def run_cmd_background(cmds):
    logger.info(f"run cmd on background : {json.dumps(cmds)}")
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        subprocess.Popen(
            cmds,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:  # Unix/Linux
        subprocess.Popen(
            cmds,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def run_cmd_foreground(cmd):
    if sys.platform == "win32":
        subprocess.Popen(f'start cmd /c "{cmd}"', shell=True)
    elif sys.platform == "linux":
        try:
            subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{cmd}; exec bash'])
        except FileNotFoundError:
            subprocess.run(cmd, shell=True)  # fallback
    elif sys.platform == "darwin":  # macOS
        try:
            subprocess.Popen(['open', '-a', 'Terminal', '--args', '-e', f'sh -c \'{cmd}; exec sh\''])
        except FileNotFoundError:
            subprocess.run(cmd, shell=True)
