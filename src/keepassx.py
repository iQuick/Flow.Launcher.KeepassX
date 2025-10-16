import concurrent.futures
from functools import partial
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

    def all(self, db):
        """统一的获取全部条目接口"""
        try:
            return self._get_all_entries(db)
        except Exception as e:
            logger.error(f"Error getting all keepass entries: {e}")
            return []

    def _extract_entry_data(self, entry):
        """提取条目数据的通用方法"""
        return {
            # "id": entry.id,
            "title": entry.title or "",
            "username": entry.username or "",
            "password": entry.password or "",
            "url": entry.url or "",
            "remark": entry.attachments or "",
            "tags": entry.tags or [],
        }

    def _extract_entry_with_score(self, entry, score):
        """提取带评分的条目数据"""
        data = self._extract_entry_data(entry)
        data["score"] = score
        return data

    def _validate_entry(self, entry):
        """验证条目是否有效"""
        return bool(entry.password)

    def _get_entry_text_fields(self, entry):
        """获取条目的文本字段（小写）"""
        return (
            (entry.title or "").lower(),
            (entry.username or "").lower(),
            (entry.url or "").lower()
        )

    def _quick_filter(self, title, username, url, search_string):
        """快速过滤：检查搜索字符串是否在任何字段中"""
        return search_string in title or search_string in username or search_string in url

    def _calculate_simple_score(self, title, username, url, search_string):
        """简单的评分计算（用于大型数据库），范围0-50"""
        score = 0
        
        # 完全匹配给更高分数
        if search_string == title:
            score += 20
        elif search_string in title:
            if title.startswith(search_string):
                score += 12  # 开头匹配
            else:
                score += 8   # 包含匹配
        
        if search_string == username:
            score += 18
        elif search_string in username:
            if username.startswith(search_string):
                score += 10
            else:
                score += 6
        
        if search_string == url:
            score += 12
        elif search_string in url:
            if url.startswith(search_string):
                score += 8
            else:
                score += 4
        
        return min(score, 50)  # 确保不超过50

    def _calculate_detailed_score(self, title, username, url, search_string):
        """详细的评分计算（用于小型数据库），范围0-50"""
        total_score = 0
        
        # 计算各字段的详细匹配评分
        if search_string in title:
            title_score = self._calculate_field_score(title, search_string, weight=1.5)
            total_score += title_score
        
        if search_string in username:
            username_score = self._calculate_field_score(username, search_string, weight=2.0)
            total_score += username_score
        
        if search_string in url:
            url_score = self._calculate_field_score(url, search_string, weight=1.0)
            total_score += url_score
        
        return min(int(total_score), 50)  # 确保不超过50

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
            # 基于出现次数和长度比例计算分数
            frequency_score = min(count * 1.5, 6)  # 最多6分
            length_ratio = len(search_string) / len(text)
            ratio_score = length_ratio * 4  # 最多4分
            return (frequency_score + ratio_score) * weight
        
        return 0

    def _sort_results(self, matched_entries):
        """对结果按评分排序"""
        return sorted(matched_entries, key=lambda x: x["score"], reverse=True)

    @abstractmethod
    def _search_keepass(self, database_path, password, search_string):
        """搜索KeePass数据库的抽象方法"""
        pass


class KeepassSmall(KeepassBase):
    """适用于小型数据库（< 1000条记录）的优化版本"""

    def _get_all_entries(self, db):
        """获取所有条目"""
        data = []
        with pykeepass.PyKeePass(db["path"], db["password"]) as kdb:
            for entry in kdb.entries:
                data.append(self._extract_entry_data(entry))
        return data

    def _search_keepass(self, database_path, password, search_string):
        """小型数据库的搜索实现"""
        try:
            logger.info(f"search keepass small: {database_path} - {search_string}")
            with pykeepass.PyKeePass(database_path, password) as kdb:
                matched_entries = []
                search_lower = search_string.lower()
                for entry in kdb.entries:
                    # 验证条目有效性
                    if not self._validate_entry(entry):
                        continue
                    
                    # 获取字段值
                    title, username, url = self._get_entry_text_fields(entry)
                    
                    # 快速过滤
                    if not self._quick_filter(title, username, url, search_lower):
                        continue
                    
                    # 详细评分计算
                    total_score = self._calculate_detailed_score(title, username, url, search_lower)
                    
                    if total_score > 0:
                        matched_entries.append(
                            self._extract_entry_with_score(entry, total_score)
                        )
                
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
            for entry in kdb.entries:
                yield self._extract_entry_data(entry)

    def _search_keepass(self, database_path, password, search_string):
        """大型数据库的并行搜索实现"""
        try:
            logger.info(f"search keepass large: {database_path} - {search_string}")
            with pykeepass.PyKeePass(database_path, password) as kdb:
                entries = list(kdb.entries)
                return self._search_parallel(entries, search_string)
                
        except Exception as e:
            logger.error(f"Error search keepass large: {e}")
            return []

    def _search_parallel(self, entries, search_string):
        """并行搜索实现 - 不分块，直接并行处理"""
        search_lower = search_string.lower()
        matched_entries = []
        
        # 计算每个线程处理的条目数量
        entries_per_worker = len(entries) // self.max_workers
        if entries_per_worker == 0:
            # 如果条目数少于线程数，直接单线程处理
            return self._search_single_thread(entries, search_string)
        
        # 为每个线程分配条目范围
        worker_ranges = []
        for i in range(self.max_workers):
            start_idx = i * entries_per_worker
            if i == self.max_workers - 1:
                # 最后一个线程处理剩余的所有条目
                end_idx = len(entries)
            else:
                end_idx = (i + 1) * entries_per_worker
            worker_ranges.append((start_idx, end_idx))
        
        # 使用线程池并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for start_idx, end_idx in worker_ranges:
                entry_slice = entries[start_idx:end_idx]
                future = executor.submit(self._process_entries, entry_slice, search_lower)
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