import base64
import concurrent.futures
import uuid
from abc import ABC, abstractmethod

import pykeepass
from .logcat import logger


class KeepassBase(ABC):
    """KeePass操作的基础类"""

    def find(self, db, query):
        """统一的查找接口"""
        db_path = db["path"]
        db_password = db["password"]
        if db_path and db_password:
            return self._search_keepass(db_path, db_password, query)
        return []

    def delete(self, entry):
        path, password = self._decrypt_db_connect(entry['dbc'])
        with pykeepass.PyKeePass(path, password) as kdb:
            try:
                kp_entry = kdb.find_entries(uuid=uuid.UUID(entry['uuid']), first=True)
                logger.info(f"Delete match result : {kp_entry}")
                if kp_entry:
                    recycle_name = "回收站" if kdb.root_group.name else "Recycle Bin"
                    recycle_group = kdb.find_groups(name=recycle_name, group=kdb.root_group, first=True)
                    if not recycle_group and recycle_name == "Recycle Bin":
                        recycle_group = kdb.find_groups(name="Recycle", group=kdb.root_group, first=True)
                    if not recycle_group:
                        recycle_group = kdb.add_group(kdb.root_group, recycle_name)
                    # kp_entry.delete()
                    kdb.move_entry(kp_entry, recycle_group)
                    kdb.save()
                    logger.info(f"Delete successful!")
                else:
                    logger.warn(f"Not found entry in keepass: {entry['title']}")
            except Exception as e:
                logger.error(f"Error delete entry from keepass : {e}")

    def all(self, db):
        """统一的获取全部条目接口"""
        try:
            return self._get_all_entries(db)
        except Exception as e:
            logger.error(f"Error getting all keepass entries: {e}")
            return []

    def _encrypt_db_connect(self, path, password):
        data = f"{path}#|#{password}"
        encrypted = base64.b64encode(data.encode('utf-8')).decode('utf-8')
        return encrypted

    def _decrypt_db_connect(self, dbc):
        decoded = base64.b64decode(dbc.encode('utf-8')).decode('utf-8')
        path, password = decoded.split('#|#', 1)  # 只分割第一个 |
        return path, password

    def _extract_entry_data(self, dbc, entry):
        try:
            return {
                "dbc": dbc,
                "uuid": str(entry.uuid),
                "title": entry.title or "",
                "username": entry.username or "",
                "password": entry.password or "",
                "url": entry.url or "",
                "remark": entry.attachments or "",
                "tags": entry.tags or [],
            }
        except Exception as e:
            logger.error(f"Error extract entry data : {entry} , {e}")
            return None

    def _extract_entry_with_score(self, dbc, entry, score):
        data = self._extract_entry_data(dbc, entry)
        if data:
            data["score"] = score
        return data

    def _validate_entry(self, entry):
        return entry.group.name not in ['回收站', 'Recycle', 'Recycle Bin']
        # return bool(entry.password)

    def _get_entry_text_fields(self, entry):
        return (
            (entry.title or "").lower(),
            (entry.username or "").lower(),
            (entry.url or "").lower()
        )

    def _quick_filter(self, title, username, url, search_string):
        return search_string in title or search_string in username or search_string in url

    def _calculate_simple_score(self, title, username, url, search_string):
        score = 0

        if search_string == title:
            score += 20
        elif search_string in title:
            score += 12 if title.startswith(search_string) else 8

        # username 评分 (最高18分)
        if search_string == username:
            score += 18
        elif search_string in username:
            score += 10 if username.startswith(search_string) else 6

        # url 评分 (最高12分)
        if search_string == url:
            score += 12
        elif search_string in url:
            score += 8 if url.startswith(search_string) else 4

        return min(score, 50)

    def _calculate_detailed_score(self, title, username, url, search_string):
        total_score = 0

        if search_string in title:
            total_score += self._calculate_field_score(title, search_string, weight=1.5)

        if search_string in username:
            total_score += self._calculate_field_score(username, search_string, weight=2.0)

        if search_string in url:
            total_score += self._calculate_field_score(url, search_string, weight=1.0)

        return min(total_score, 50)

    def _calculate_field_score(self, text, search_string, weight=1.0):
        """计算单个字段的评分"""
        if not text:
            return 0

        # 完全匹配
        if search_string == text:
            return 10 * weight

        # 开头匹配
        if text.startswith(search_string):
            length_ratio = len(search_string) / len(text)
            return 8 * length_ratio * weight

        # 包含匹配 - 计算出现频率
        count = 0
        start = 0
        while True:
            pos = text.find(search_string, start)
            if pos == -1:
                break
            count += 1
            start = pos + 1

        if count > 0:
            frequency_score = min(count * 1.5, 6)
            length_ratio = len(search_string) / len(text)
            ratio_score = length_ratio * 4
            return (frequency_score + ratio_score) * weight

        return 0

    @abstractmethod
    def _search_keepass(self, database_path, password, search_string):
        """搜索KeePass数据库的抽象方法"""
        pass

    @abstractmethod
    def _get_all_entries(self, db):
        """获取所有条目的抽象方法"""
        pass


class KeepassSmall(KeepassBase):
    """适用于小型数据库（< 1000条记录）的优化版本"""

    def _get_all_entries(self, db):
        """获取所有条目"""
        data = []
        with pykeepass.PyKeePass(db["path"], db["password"]) as kdb:
            dbc = self._encrypt_db_connect(db["path"], db["password"])
            for entry in kdb.entries:
                item = self._extract_entry_data(dbc, entry)
                if item:
                    data.append(item)
        return data

    def _search_keepass(self, database_path, password, search_string):
        """小型数据库的搜索实现"""
        try:
            with pykeepass.PyKeePass(database_path, password) as kdb:
                dbc = self._encrypt_db_connect(database_path, password)
                matched_entries = []
                search_lower = search_string.lower()

                for entry in kdb.entries:
                    if not self._validate_entry(entry):
                        continue

                    title, username, url = self._get_entry_text_fields(entry)

                    if not self._quick_filter(title, username, url, search_lower):
                        continue

                    # 详细评分计算
                    total_score = self._calculate_detailed_score(title, username, url, search_lower)

                    if total_score > 0:
                        item = self._extract_entry_with_score(dbc, entry, total_score)
                        if item:
                            matched_entries.append(item)

                return matched_entries

        except Exception as e:
            logger.error(f"Error search keepass small: {e}")
            return []


class KeepassLarge(KeepassBase):
    """适用于大型数据库（> 1000条记录）的优化版本"""

    def __init__(self, max_workers=4):
        self.max_workers = max_workers

    def _get_all_entries(self, db):
        """使用生成器获取所有条目"""
        return list(self._get_all_entries_generator(db))

    def _get_all_entries_generator(self, db):
        """生成器版本，避免一次性加载所有数据到内存"""
        with pykeepass.PyKeePass(db["path"], db["password"]) as kdb:
            dbc = self._encrypt_db_connect(db["path"], db["password"])
            for entry in kdb.entries:
                item = self._extract_entry_data(dbc, entry)
                if item:
                    yield item

    def _search_keepass(self, database_path, password, search_string):
        """大型数据库的并行搜索实现"""
        try:
            logger.info(f"search keepass large: {database_path} - {search_string}")
            dbc = self._encrypt_db_connect(database_path, password)
            with pykeepass.PyKeePass(database_path, password) as kdb:
                entries = list(kdb.entries)
                search_lower = search_string.lower()

                # 如果条目数少于线程数，使用单线程
                if len(entries) <= self.max_workers:
                    return self._process_entries(entries, search_lower)

                # 并行处理
                return self._search_parallel(dbc, entries, search_lower)

        except Exception as e:
            logger.error(f"Error search keepass large: {e}")
            return []

    def _search_parallel(self, dbc, entries, search_string):

        # 计算每个线程处理的条目数量
        entries_per_worker = len(entries) // self.max_workers

        # 为每个线程分配条目范围
        worker_ranges = []
        for i in range(self.max_workers):
            start_idx = i * entries_per_worker
            # 最后一个线程处理剩余的所有条目
            end_idx = len(entries) if i == self.max_workers - 1 else (i + 1) * entries_per_worker
            worker_ranges.append((start_idx, end_idx))

        # 使用线程池并行处理
        matched_entries = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for start_idx, end_idx in worker_ranges:
                entry_slice = entries[start_idx:end_idx]
                future = executor.submit(self._process_entries, dbc, entry_slice, search_string)
                futures.append(future)

            # 收集所有线程的结果
            for future in concurrent.futures.as_completed(futures):
                try:
                    chunk_results = future.result()
                    matched_entries.extend(chunk_results)
                except Exception as e:
                    logger.error(f"Error processing entries: {e}")
                    continue

        return matched_entries

    def _process_entries(self, dbc, entries, search_string):
        matched_entries = []

        for entry in entries:
            if not self._validate_entry(entry):
                continue

            title, username, url = self._get_entry_text_fields(entry)
            if not self._quick_filter(title, username, url, search_string):
                continue

            # 使用简单评分
            score = self._calculate_simple_score(title, username, url, search_string)
            if score > 0:
                item = self._extract_entry_with_score(dbc, entry, score)
                if item:
                    matched_entries.append(item)

        return matched_entries


