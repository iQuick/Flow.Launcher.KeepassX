# -*- coding: utf-8 -*-
import json
import sys, os

parent_folder_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(parent_folder_path)
sys.path.append(os.path.join(parent_folder_path, "lib"))
sys.path.append(os.path.join(parent_folder_path, "plugin"))

from flowlauncher import FlowLauncher, FlowLauncherAPI


from src import (
    keepass,
    logger,
    config,
    get_config_file,
    get_app_icon,
    get_asset_icon,
    edit_file,
    download_icons,
    copy_to_clipboard,
    get_keepass_icon,
    get_keepass_title,
    get_keepass_subtitle,
)


class KeepassLauncher(FlowLauncher):

    def query(self, query):
        if self._check_none(query):
            return list(
                filter(lambda x: x["Title"].startswith(query), self._get_tip_none())
            )

        # 读取配置文件
        logger.info(f"query : {query}")
        if not self._check_database(config):
            return self._get_tip_database()

        # 读取数据
        data = []
        for db in config["databases"]:
            try:
                data.extend(self._find_keepass_db(db, query))
            except Exception as e:
                logger.error(f"Error query find in database : {e}")
        return data

    def context_menu(self, data):
        if data:
            type = data[0]
            logger.info(f"context menu type : {type}")
            if type == "keepass":
                return self._get_menu_keepass(data[1])
        return []

    def _find_keepass_db(self, db, query):
        data = []
        result = keepass.find(db, query)
        logger.info(f"match result : {db['path']} - {len(result)}")
        for info in result:
            item = {
                "Title": get_keepass_title(info),
                "SubTitle": get_keepass_subtitle(info),
                "IcoPath": get_keepass_icon(info),
                "ContextData": ["keepass", info],
                "JsonRPCAction": {
                    "method": "action_copy_query_result",
                    "parameters": [info["password"]],
                },
                "score": info["score"]
            }
            data.append(item)
        return data

    def action_delete_entry(self, entry):
        try:
            entry["delete"]()
        except:
            logger.error("Error delete entry!")

    def action_edit_file(self, file):
        logger.info(f"action edit file : {file}")
        return edit_file(file)

    def action_download_icons(self):
        download_icons()

    def action_copy_query_result(self, url):
        copy_to_clipboard(url)

    def _check_none(self, query):
        return query == None or query == "" or query.startswith("@")

    def _check_database(self, config):
        return config and config["databases"] and len(config["databases"]) > 0

    def _get_tip_none(self):
        return [
            {
                "Title": "@config",
                "SubTitle": "修改配置 - Modify config",
                "IcoPath": get_app_icon(),
                "JsonRPCAction": {
                    "method": "action_edit_file",
                    "parameters": [get_config_file()],
                },
            },
            {
                "Title": "@download-icons",
                "SubTitle": "下载图标 - Download icons",
                "IcoPath": get_app_icon(),
                "JsonRPCAction": {
                    "method": "action_download_icons",
                    "parameters": [],
                },
            },
        ]

    def _get_tip_database(self):
        return [
            {
                "Title": "未配置数据库，请前往配置",
                "SubTitle": "No database configured, go to configure!",
                "IcoPath": get_app_icon(),
                "JsonRPCAction": {
                    "method": "action_edit_file",
                    "parameters": [get_config_file()],
                }
            }
        ]

    def _get_menu_keepass(info):
        return [
            {
                "Title": "复制密码",
                "SubTitle": "******",
                "IcoPath": info["username"],
                "JsonRPCAction": {
                    "method": "action_copy_query_result",
                    "parameters": [info["password"]],
                }
            },
            {
                "Title": "复制用户名",
                "SubTitle": info["name"],
                "IcoPath": get_asset_icon("copy"),
                "JsonRPCAction": {
                    "method": "action_copy_query_result",
                    "parameters": [info["name"]],
                }
            },
            {
                "Title": "复制标题",
                "SubTitle": info["title"],
                "IcoPath": get_asset_icon("copy"),
                "JsonRPCAction": {
                    "method": "action_copy_query_result",
                    "parameters": [info["title"]],
                }
            },
            {
                "Title": "复制地址",
                "SubTitle": info["url"],
                "IcoPath": get_asset_icon("copy"),
                "JsonRPCAction": {
                    "method": "action_copy_query_result",
                    "parameters": [info["url"]],
                }
            },
            {
                "Title": "删除",
                "SubTitle": "Delete entry",
                "IcoPath": get_asset_icon("delete"),
                "JsonRPCAction": {
                    "method": "action_delete_entry",
                    "parameters": [info],
                }
            },
        ]


if __name__ == "__main__":
    KeepassLauncher()
