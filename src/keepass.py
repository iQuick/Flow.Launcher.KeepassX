import pykeepass
from .logcat import logger


class Keepass:

    def find(self, db, query):
        db_path = db["path"]
        db_password = db["password"]
        if db_path and db_password:
            return self._search_keepass(db_path, db_password, query)
        return []

    def all(self, db):
        data = []
        with pykeepass.PyKeePass(db["path"], db["password"]) as kdb:
            for entry in kdb.entries:
                title = entry.title if entry.title else ""
                username = entry.username if entry.username else ""
                url = entry.url if entry.url else ""
                attachments = entry.attachments if entry.attachments else ""
                tags = entry.tags if entry.tags else []
                data.append(
                    {
                        "title": title,
                        "username": username,
                        "password": entry.password,
                        "url": url,
                        "remark": attachments,
                        "tags": tags,
                    }
                )
        return data

    def _search_keepass(self, database_path, password, search_string):
        try:
            logger.info(f"search keepass : {database_path} - {search_string}")
            with pykeepass.PyKeePass(database_path, password) as kdb:
                matched_entries = []
                for entry in kdb.entries:
                    if entry.password is None or entry.password == "":
                        continue

                    title = entry.title if entry.title else ""
                    username = entry.username if entry.username else ""
                    url = entry.url if entry.url else ""
                    attachments = entry.attachments if entry.attachments else ""
                    tags = entry.tags if entry.tags else []

                    # 计算匹配率
                    title_match = self._calculate_match_rate(title, search_string) * 2
                    username_match = (
                        self._calculate_match_rate(username, search_string) * 3
                    )
                    url_match = self._calculate_match_rate(url, search_string)
                    total_match = title_match + username_match + url_match  # 平均匹配率

                    if total_match > 0:
                        matched_entries.append(
                            {
                                "title": title,
                                "username": username,
                                "password": entry.password,
                                "url": url,
                                "remark": attachments,
                                "tags": tags,
                                "match_rate": total_match,
                            }
                        )
                return matched_entries
        except Exception as e:
            logger.error(f"Error search keepass : {e}")
            return []

    def _calculate_match_rate(self, text, search_string):
        if not text:  # 防止 text 为 None 或者空字符串
            return 0
        search_string = search_string.lower()
        text = text.lower()
        match_count = 0
        for i in range(len(text) - len(search_string) + 1):
            if text[i : i + len(search_string)] == search_string:
                match_count += 1
        return match_count / max(len(text), 1)
