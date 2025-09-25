# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import json
import shutil
import hashlib

from .clipboard import copy, clear
from .logcat import logger
from .keepass import Keepass
from .keepassx import KeepassSmall, KeepassLarge
from .cmd import run_cmd_background, run_cmd_foreground

__ICONS = "icons"
__CONFIG = "config.json"
__LOGGER = "logger.txt"
__CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
__ROOT_PATH = os.path.dirname(__CURRENT_PATH)


def _get_icon_path(file):
    return os.path.join(__ROOT_PATH, f"{__ICONS}/{file}")


def _icon(icon=""):
    if icon != None and icon != "":
        name = hashlib.md5(icon.encode("utf-8")).hexdigest()
        if os.path.exists(_get_icon_path(f"{name}.ico")):
            return _get_icon_path(f"{name}.ico")
        elif os.path.exists(_get_icon_path(f"{name}.svg")):
            return _get_icon_path(f"{name}.svg")
        elif os.path.exists(_get_icon_path(f"{name}.jpg")):
            return _get_icon_path(f"{name}.jpg")
        elif os.path.exists(_get_icon_path(f"{name}.jepg")):
            return _get_icon_path(f"{name}.jepg")
        elif os.path.exists(_get_icon_path(f"{name}.png")):
            return _get_icon_path(f"{name}.png")
        elif os.path.exists(_get_icon_path(f"{name}.webp")):
            return _get_icon_path(f"{name}.webp")
    return _get_icon_path("../app.ico")


def get_root(file):
    return os.path.join(__ROOT_PATH, file)


def get_config():
    try:
        if not os.path.exists(get_root(__CONFIG)):
            shutil.copyfile(get_root(__CONFIG + ".simple"), get_root(__CONFIG))
        with open(get_root(__CONFIG), "r", encoding="utf8") as f:
            return json.loads(f.read())
    except:
        return None


def get_config_file():
    return get_root(__CONFIG)


def get_app_icon():
    return _get_icon_path("../app.ico")


def get_keepass_icon(info):
    return _icon(info["url"])


def get_keepass_title(info):
    def get_title(title, name):
        if name != "":
            return name
        if title != "":
            return title
        return "Unknown"

    return get_title(info["title"], info["username"])


def get_keepass_subtitle(info):
    def get_subtitle(title, url):
        new_title = ""
        if title != "":
            new_title += title
        if url != "":
            if new_title != "":
                new_title += " - "
            new_title += url
        return new_title

    return get_subtitle(info["title"], info["url"])


def download_icons():
    try:
        args = [
            sys.executable.replace("pythonw", "python"),
            get_root("src/plugin/download.py"),
            get_root(__CONFIG),
            get_root(__ICONS),
        ]
        cmd = " ".join(args)
        run_cmd_foreground(cmd)
    except Exception as e:
        logger.error(f"Error download : {e}")


def copy_to_clipboard(data):
    copy(data)
    auto_clear = False
    if "auto_clear" in config:
        auto_clear = config["auto_clear"]
    if not auto_clear:
        return

    auto_clear_delay = 5
    if "auto_clear_delay" in config:
        auto_clear_delay = config["auto_clear_delay"]

    args = [sys.executable, get_root("src/plugin/cleanup.py"), str(auto_clear_delay)]
    run_cmd_background(args)


def edit_file(file):
    cmds = [sys.executable, get_root("src/plugin/edittext.py"), file]
    run_cmd_background(cmds)

config = get_config()
logger.init(True, get_root(__LOGGER))
multi = config['multi']
keepass = KeepassLarge() if multi else KeepassSmall()
# keepass = Keepass()


__all__ = [
    "logger",
    "keepass",
    "config",
    "get_root",
    "get_app_icon",
    "get_config_file",
    "edit_file",
    "download_icons",
    "get_keepass_icon",
    "get_keepass_title",
    "get_keepass_subtitle",
]
