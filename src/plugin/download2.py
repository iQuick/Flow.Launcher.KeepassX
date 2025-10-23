# -*- coding: utf-8 -*-

import os
import random
import re
import sys
import json
import hashlib
import base64
import logging
from typing import Optional, Dict, List
from urllib.parse import urlparse, urljoin
from pathlib import Path

import requests
import pykeepass
from bs4 import BeautifulSoup
import urllib3
from construct import Array

# 屏蔽 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

HDS = [
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36  (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.105 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.98 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.198 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.6045.105 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/118.0.5993.88 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/117.0.5938.62 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/116.0.5845.97 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/115.0.5790.98 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/114.0.5735.198 Safari/537.36'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.105 Safari/537.36 Edg/119.0.6045.105'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36 Edg/118.0.5993.88'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.62 Safari/537.36 Edg/117.0.5938.62'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.97 Safari/537.36 Edg/116.0.5845.97'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.98 Safari/537.36 Edg/115.0.5790.98'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.198 Safari/537.36 Edg/114.0.5735.198'}
]

class FaviconDownloader:
    """Favicon下载器类"""

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }

    BASE64_IMAGE_PATTERN = re.compile(r'^data:image/(png|jpeg|jpg|gif|webp|x-icon);base64')
    META_REFRESH_PATTERN = re.compile(r'URL=[\'"]?(.*?)[\'"]?', re.IGNORECASE)

    ICON_SELECTORS = [
        {'rel': 'icon'},
        {'rel': 'shortcut icon'},
        {'rel': 'apple-touch-icon'},
        {'rel': 'apple-touch-icon-precomposed'},
        {'rel': 'mask-icon'},
        {'rel': 'fluid-icon'}
    ]

    # 常见的favicon默认路径（按优先级排序）
    DEFAULT_FAVICON_PATHS = [
        '/favicon',
        # assets
        '/assets/favicon',
        '/assets/img/favicon',
        '/assets/images/favicon',
        # static
        '/static/favicon',
        '/static/img/favicon',
        '/static/images/favicon',
        # image | resource
        '/img/favicon',
        '/images/favicon',
        '/public/favicon',
        '/resources/favicon',
        '/wp-content/uploads/favicon',
        '/sites/default/files/favicon',
        '/apple-touch-icon',
        '/apple-touch-icon-precomposed'
    ]

    SUPPORTED_EXTENSIONS = {'.svg', '.jpg', '.jpeg', '.png', '.webp', '.ico', '.gif'}
    MIN_FILE_SIZE = 128 * 3  # 最小文件大小（字节）

    def __init__(self, proxy: Optional[Dict] = None, apis: List[str] = None):
        self.proxy = proxy or {}
        self.apis = apis or []
        if proxy:
            for key, value in self.proxy.items():
                if "IP:PROXY" == value:
                    del self.proxy[key]
        self.has_proxy = bool(self.proxy)
        self.stats = DownloadStats()
        self.session_no_proxy = None
        self.session_with_proxy = None

        # 创建两个session：一个带代理，一个不带代理
        logger.info("创建不带代理的 session")
        self.session_no_proxy = self._create_session()
        self.sessions = [self.session_no_proxy]
        if self.has_proxy:
            logger.info("创建带代理的 session")
            self.session_with_proxy = self._create_session(self.proxy)
            self.sessions.append(self.session_with_proxy)


    def _create_session(self, proxy = None) -> requests.Session:
        """创建requests会话"""
        session = requests.Session()
        session.headers.update(self.HEADERS)
        session.verify = False
        if proxy:
            session.proxies.update(proxy)

        return session

    def _format_url(self, url):
        """格式化URL"""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        elif url.startswith("//"):
            return f"http:{url}"
        else:
            return f"http://{url}"

    def _make_request(self, session: requests.Session, url: str, headers=HEADERS, timeout=10, retry=2) -> Optional[requests.Response]:
        """使用指定session发起请求"""
        try:
            logger.info(f"| 尝试请求({3 - retry}): {url}")
            response = session.get(url, timeout=timeout, headers=headers)
            response.raise_for_status()
            logger.info(f"| 请求成功")
            return response
        except Exception as e:
            if retry > 0:
                self._make_request(session, url, random.choice(HDS), timeout, retry - 1)
            else:
                logger.info(f"| 请求失败 {e}")
                logger.info(f"| ---------")

        return None

    def _check_connect(self, session: requests.Session, url: str, timeout=10) -> bool:
        """检查连接是否可用"""
        try:
            if len(session.proxies.keys()) > 0:
                logger.info(f"| 尝试代理连接: {url}")
            else:
                logger.info(f"| 尝试直接连接: {url}")
            session.get(url, timeout=timeout)
            return True
        except:
            return False

    def _extract_redirect_url(self, html_content: str) -> Optional[str]:
        """从HTML meta标签中提取重定向URL"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            meta_tag = soup.find('meta', attrs={'http-equiv': re.compile(r'refresh', re.I)})
            if meta_tag:
                content = meta_tag.get('content', '')
                match = self.META_REFRESH_PATTERN.search(content)
                if match:
                    return match.group(1)
        except Exception:
            logger.debug(f"| 提取重定向URL失败")
        return None

    def _find_favicon_by_page(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """从HTML中查找所有可能的favicon图片链接"""
        favicon_candidates = []

        # 1. 标准的link标签
        for selector in self.ICON_SELECTORS:
            link_tags = soup.find_all('link', attrs=selector)
            for link_tag in link_tags:
                href = link_tag.get('href')
                if href:
                    favicon_candidates.append({
                        'url': href,
                        'type': 'link_tag',
                        'rel': link_tag.get('rel', [''])[0],
                        'sizes': link_tag.get('sizes', ''),
                        'priority': 1
                    })

        # 2. meta标签中的图片
        meta_tags = soup.find_all('meta')
        for meta_tag in meta_tags:
            property_val = meta_tag.get('property', '').lower()
            name_val = meta_tag.get('name', '').lower()
            content = meta_tag.get('content', '')

            if property_val == 'og:image' and content:
                favicon_candidates.append({
                    'url': content,
                    'type': 'og_image',
                    'rel': 'og:image',
                    'sizes': '',
                    'priority': 3
                })
            elif name_val == 'twitter:image' and content:
                favicon_candidates.append({
                    'url': content,
                    'type': 'twitter_image',
                    'rel': 'twitter:image',
                    'sizes': '',
                    'priority': 4
                })
            elif any(keyword in name_val for keyword in ['icon', 'logo', 'image']) and content:
                favicon_candidates.append({
                    'url': content,
                    'type': 'meta_image',
                    'rel': name_val,
                    'sizes': '',
                    'priority': 5
                })

        # 3. 查找可能是logo的img标签
        img_tags = soup.find_all('img')
        for img_tag in img_tags:
            src = img_tag.get('src', '')
            alt = img_tag.get('alt', '').lower()
            class_list = ' '.join(img_tag.get('class', [])).lower()
            id_attr = img_tag.get('id', '').lower()

            keywords = ['favicon', 'icon', 'logo', 'brand']
            if src and any(keyword in src.lower() for keyword in keywords):
                favicon_candidates.append({
                    'url': src,
                    'type': 'img_src',
                    'rel': 'img-src',
                    'sizes': '',
                    'priority': 6
                })
            elif any(keyword in alt for keyword in keywords):
                favicon_candidates.append({
                    'url': src,
                    'type': 'img_alt',
                    'rel': 'img-alt',
                    'sizes': '',
                    'priority': 7
                })
            elif any(keyword in class_list for keyword in keywords):
                favicon_candidates.append({
                    'url': src,
                    'type': 'img_class',
                    'rel': 'img-class',
                    'sizes': '',
                    'priority': 8
                })
            elif any(keyword in id_attr for keyword in keywords):
                favicon_candidates.append({
                    'url': src,
                    'type': 'img_id',
                    'rel': 'img-id',
                    'sizes': '',
                    'priority': 9
                })

        # 按优先级排序并去重
        seen_urls = set()
        unique_candidates = []

        for candidate in sorted(favicon_candidates, key=lambda x: x['priority']):
            url = candidate['url']
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_candidates.append(candidate)

        logger.debug(f"找到 {len(unique_candidates)} 个favicon候选图片")
        return unique_candidates

    def _normalize_url(self, url: str, base_url: str) -> str:
        """标准化URL"""
        if self._is_base64_image(url):
            return url
        elif url.startswith('http'):
            return url
        elif url.startswith('//'):
            return f"https:{url}"
        else:
            return urljoin(base_url, url)

    def _get_file_extension(self, url: str, content_type: str = '') -> str:
        """根据URL和Content-Type确定文件扩展名"""
        parsed = urlparse(url)
        path_ext = Path(parsed.path).suffix.lower()
        if path_ext in self.SUPPORTED_EXTENSIONS:
            return path_ext

        if content_type:
            if 'svg' in content_type:
                return '.svg'
            elif 'png' in content_type:
                return '.png'
            elif 'jpeg' in content_type or 'jpg' in content_type:
                return '.jpg'
            elif 'webp' in content_type:
                return '.webp'
            elif 'gif' in content_type:
                return '.gif'

        return '.ico'

    def _save_base64_image(self, base64_data: str, file_path: Path) -> bool:
        """保存base64图片"""
        try:
            _, data = base64_data.split(',', 1)
            decoded_data = base64.b64decode(data)

            if len(decoded_data) < self.MIN_FILE_SIZE:
                logger.warning(f"| Base64图片太小，跳过: {len(decoded_data)} bytes")
                return False

            with open(file_path, 'wb') as f:
                f.write(decoded_data)
            logger.info(f"| 成功保存base64图片: {file_path}")
            return True
        except Exception:
            logger.error(f"| 保存base64图片失败")
            return False

    def _is_base64_image(self, content: str) -> bool:
        """检查是否为base64图片"""
        return bool(self.BASE64_IMAGE_PATTERN.match(content))

    def _is_image_content(self, content: bytes, content_type: str) -> bool:
        """检查内容是否为图片"""
        image_types = ['image/', 'application/octet-stream']
        if any(img_type in content_type.lower() for img_type in image_types):
            return True

        if len(content) < 4:
            return False

        magic_numbers = {
            b'\x89PNG': 'PNG',
            b'\xFF\xD8\xFF': 'JPEG',
            b'GIF8': 'GIF',
            b'RIFF': 'WEBP',
            b'\x00\x00\x01\x00': 'ICO',
            b'\x00\x00\x02\x00': 'CUR',
            b'<svg': 'SVG'
        }

        for magic, format_type in magic_numbers.items():
            if content.startswith(magic):
                logger.info(f"| 检测到图片格式: {format_type}")
                return True

        try:
            text_content = content.decode('utf-8', errors='ignore')[:1000]
            if '<svg' in text_content.lower():
                logger.info("| 检测到SVG格式")
                return True
        except:
            pass

        return False

    def _download_file(self, session: requests.Session, url: str, save_path: Path) -> bool:
        """下载文件"""
        try:
            logger.info(f"| 开始下载 favicon: {url}")

            response = self._make_request(session, url)
            if not response:
                return False

            content = response.content
            content_type = response.headers.get('Content-Type', '').lower()

            if len(content) < self.MIN_FILE_SIZE:
                logger.info(f"| 文件太小，跳过: {len(content)} bytes")
                return False

            if 'text/html' in content_type or not self._is_image_content(content, content_type):
                logger.info(f"| 响应是HTML页面，尝试从中提取favicon链接")

                try:
                    html_content = content.decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(html_content, 'html.parser')
                    favicon_candidates = self._find_favicon_by_page(soup, response.url)

                    if favicon_candidates:
                        for candidate in favicon_candidates[:3]:  # 只尝试前3个
                            favicon_url = self._normalize_url(candidate['url'], response.url)

                            if self._is_base64_image(favicon_url):
                                return self._save_base64_image(favicon_url, save_path)

                            if favicon_url != url:
                                logger.info(f"| 从HTML中找到favicon链接: {favicon_url}")
                                return self._download_file(session, favicon_url, save_path)

                    logger.info(f"| HTML页面中未找到favicon链接")
                    return False

                except Exception:
                    logger.info(f"| 处理HTML内容失败")
                    return False

            logger.info(f"| 检测到图片内容: {content_type}")

            ext = self._get_file_extension(url, content_type)
            final_path = save_path.with_suffix(ext)

            with open(final_path, 'wb') as f:
                f.write(content)

            logger.info(f"| 成功下载favicon: {final_path}")
            return True

        except Exception:
            logger.info(f"| 保存文件失败 {url}")
            return False

    def download_favicon(self, url: str, save_path: Path) -> bool:
        """下载favicon的主入口"""
        logger.info(f"┌{"─" * 60}")
        logger.info(f"| 开始抓取站点 favicon : {url}")
        logger.info(f"├{"─" * 60}")
        download_result = self._download_favicon_inner(url, save_path)
        if download_result:
            logger.info(f"| 下载成功: {url}")
        else:
            self.stats.add_failure(url, "所有方法失败")
            logger.info(f"| 下载失败: {url}")
        logger.info(f"└{"─" * 60}\n")
        return download_result

    def _download_favicon_inner(self, url: str, save_path: Path) -> bool:
        """下载favicon的内部实现"""
        if not url:
            return False

        save_path.parent.mkdir(parents=True, exist_ok=True)

        # 检查是否存在任何扩展名的文件
        existing_files = list(save_path.parent.glob(f"{save_path.stem}.*"))
        if existing_files:
            logger.info(f"| 文件已存在，跳过: {existing_files[0]}")
            self.stats.add_skip()
            return True

        # 解析URL
        url = self._format_url(url)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or parsed_url.path
        if not domain:
            logger.info(f"| 无效URL: {url}")
            self.stats.add_failure(url, "无效URL")
            return False

        # 检测可用的 session 和协议
        session = None
        final_url = None
        logger.info(f"| 尝试连接站点")

        for scheme in ["http", "https"]:
            for test_session in self.sessions:
                if test_session is None:
                    continue
                new_url = f"{scheme}://{domain}{parsed_url.path}"
                if self._check_connect(test_session, new_url):
                    session = test_session
                    final_url = new_url
                    break
            if session:
                break

        if not session or not final_url:
            logger.info(f"| 连接站点失败")
            self.stats.add_failure(url, "连接失败")
            return False

        # 方法1: 尝试默认路径
        logger.info(f"├─────── 方法1 : 尝试默认favicon路径 ───────")
        if self._try_favicon_from_paths(session, final_url, save_path):
            self.stats.add_success('direct_favicon')
            return True

        # 方法2: 从网站页面获取
        logger.info(f"├─────── 方法2 : 从网站页面解析 ───────")
        if self._try_favicon_from_page_content(session, final_url, save_path):
            return True

        # 方法3: 使用第三方API
        logger.info(f"├─────── 方法3 : 使用第三方API ({len(self.apis)}) ───────")
        if len(self.apis) > 0:
            if self.session_with_proxy:
                session = self.session_with_proxy
            if self._try_favicon_from_apis(session, domain, save_path):
                return True

        return False

    def _try_favicon_from_paths(self, session: requests.Session, base_url: str, save_path: Path) -> bool:
        """尝试常见的默认favicon路径"""
        logger.info(f"| 尝试默认favicon路径: {base_url}")
        for path in self.DEFAULT_FAVICON_PATHS:
            for ext in self.SUPPORTED_EXTENSIONS:
                favicon_url = urljoin(base_url, f"{path}{ext}")
                logger.info(f"| 尝试默认路径: {favicon_url}")

                if self._download_file(session, favicon_url, save_path):
                    logger.info(f"| 默认路径成功: {favicon_url}")
                    return True

        logger.info("| 所有默认路径都失败了")
        return False

    def _try_favicon_from_page_content(self, session: requests.Session, url: str, save_path: Path) -> bool:
        """从页面内容解析并下载favicon"""
        try:
            logger.info(f"| 从页面获取favicon: {url}")

            response = self._make_request(session, url)
            if not response:
                self.stats.add_failure(url, "页面请求失败")
                return False

            # 处理重定向
            final_url = response.url
            redirect_url = self._extract_redirect_url(response.text)
            if redirect_url:
                final_url = urljoin(final_url, redirect_url)
                logger.info(f"| 发现重定向: {final_url}")
                response = self._make_request(session, final_url)
                if not response:
                    self.stats.add_failure(url, "重定向页面请求失败")
                    return False

            # 解析HTML查找所有可能的favicon图片
            soup = BeautifulSoup(response.text, 'html.parser')
            favicon_candidates = self._find_favicon_by_page(soup, final_url)

            if favicon_candidates:
                for candidate in favicon_candidates:
                    favicon_url = candidate['url']
                    candidate_type = candidate['type']

                    logger.debug(f"| 尝试候选图片 [{candidate_type}]: {favicon_url}")

                    if self._is_base64_image(favicon_url):
                        success = self._save_base64_image(favicon_url, save_path)
                        if success:
                            self.stats.add_success('base64_image')
                            return True
                        continue

                    normalized_url = self._normalize_url(favicon_url, final_url)
                    success = self._download_file(session, normalized_url, save_path)
                    if success:
                        self.stats.add_success('from_html_page')
                        logger.info(f"| 成功下载 [{candidate_type}]: {normalized_url}")
                        return True
                    else:
                        logger.info(f"| 候选图片下载失败 [{candidate_type}]: {normalized_url}")

            logger.info("| 所有候选图片都失败，尝试默认favicon路径")
            success = self._try_favicon_from_paths(session, final_url, save_path)
            if success:
                self.stats.add_success('default_paths')
                return True

            self.stats.add_failure(url, "页面解析和默认路径都失败")
            return False

        except Exception as e:
            logger.error(f"从页面获取favicon失败 {url}: {e}")
            self.stats.add_failure(url, f"页面解析异常: {str(e)}")
            return False

    def _try_favicon_from_apis(self, session: requests.Session, domain: str, save_path: Path) -> bool:
        """使用第三方API下载favicon"""
        for api in self.apis:
            try:
                api_url = api.replace('{domain}', domain)
                logger.info(f"| 尝试API: {api_url}")

                success = self._download_file(session, api_url, save_path)
                if success:
                    self.stats.add_success('from_api')
                    return True
            except Exception:
                logger.info(f"| API下载失败 {api_url}")
                continue

        self.stats.add_failure(f"domain:{domain}", "所有API方法失败")
        return False


class DownloadStats:
    """下载统计信息类"""

    def __init__(self):
        self.total_count = 0
        self.success_count = 0
        self.skip_count = 0
        self.failed_urls = []
        self.failed_reasons = {}

        self.success_methods = {
            'direct_favicon': 0,
            'from_html_page': 0,
            'default_paths': 0,
            'from_api': 0,
            'base64_image': 0
        }

    def add_success(self, method: str = 'unknown'):
        """记录成功"""
        self.success_count += 1
        if method in self.success_methods:
            self.success_methods[method] += 1

    def add_skip(self):
        """记录跳过"""
        self.skip_count += 1

    def add_failure(self, url: str, reason: str):
        """记录失败"""
        self.failed_urls.append(url)
        if reason in self.failed_reasons:
            self.failed_reasons[reason] += 1
        else:
            self.failed_reasons[reason] = 1

    def add_total(self):
        """增加总数"""
        self.total_count += 1

    @property
    def failure_count(self) -> int:
        """失败数量"""
        return len(self.failed_urls)

    @property
    def success_rate(self) -> float:
        """成功率"""
        attempted = self.total_count - self.skip_count
        if attempted == 0:
            return 0.0
        return (self.success_count / attempted) * 100

    @property
    def overall_completion_rate(self) -> float:
        """总完成率"""
        if self.total_count == 0:
            return 0.0
        return ((self.success_count + self.skip_count) / self.total_count) * 100

    def get_summary(self) -> str:
        """获取统计摘要"""
        summary = []
        summary.append("=" * 60)
        summary.append("📊 下载统计报告")
        summary.append("=" * 60)
        summary.append(f"📈 总处理数量: {self.total_count}")
        summary.append(f"✅ 成功下载: {self.success_count}")
        summary.append(f"⏭️ 跳过(已存在): {self.skip_count}")
        summary.append(f"❌ 下载失败: {self.failure_count}")
        summary.append(f"📊 成功率: {self.success_rate:.1f}% (不含跳过)")
        summary.append(f"📊 总完成率: {self.overall_completion_rate:.1f}% (含跳过)")

        if self.success_count > 0:
            summary.append("\n🎯 成功方式分布:")
            for method, count in self.success_methods.items():
                if count > 0:
                    percentage = (count / self.success_count) * 100
                    method_name = {
                        'direct_favicon': '直接/favicon.ico',
                        'from_html_page': 'HTML页面解析',
                        'default_paths': '默认路径尝试',
                        'from_api': '第三方API',
                        'base64_image': 'Base64图片'
                    }.get(method, method)
                    summary.append(f"  • {method_name}: {count} ({percentage:.1f}%)")

        if self.failed_reasons:
            summary.append("\n💥 失败原因分布:")
            for reason, count in sorted(self.failed_reasons.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.failure_count) * 100
                summary.append(f"  • {reason}: {count} ({percentage:.1f}%)")

        if self.failed_urls:
            summary.append(f"\n❌ 失败的URL列表 (前{min(10, len(self.failed_urls))}个):")
            for i, url in enumerate(self.failed_urls[:10], 1):
                summary.append(f"  {i:2d}. {url}")
            if len(self.failed_urls) > 10:
                summary.append(f"     ... 还有 {len(self.failed_urls) - 10} 个失败的URL")

        summary.append("=" * 60)
        return "\n".join(summary)

    def save_failed_urls(self, file_path: Path):
        """保存失败的URL到文件"""
        if not self.failed_urls:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# 下载失败的URL列表\n")
                f.write(f"# 总失败数量: {len(self.failed_urls)}\n\n")
                for url in self.failed_urls:
                    f.write(f"{url}\n")

            logger.info(f"失败URL列表已保存到: {file_path}")
        except Exception as e:
            logger.error(f"保存失败URL列表时出错: {e}")


class KeePassProcessor:
    """KeePass数据库处理器"""

    def __init__(self, downloader: FaviconDownloader):
        self.downloader = downloader

    def process_database(self, db_config: Dict, save_dir: Path) -> int:
        """处理单个数据库"""
        db_path = db_config['path']
        password = db_config['password']

        if not os.path.exists(db_path):
            logger.error(f"数据库文件不存在: {db_path}")
            return 0

        success_count = 0

        try:
            with pykeepass.PyKeePass(db_path, password=password) as kdb:
                logger.info(f"处理数据库: {db_path}\n")
                for entry in kdb.entries:
                    url = entry.url
                    if not url:
                        continue

                    self.downloader.stats.add_total()

                    filename = hashlib.md5(url.encode('utf-8')).hexdigest() + '.ico'
                    save_path = save_dir / filename

                    if self.downloader.download_favicon(url, save_path):
                        success_count += 1

        except Exception as e:
            logger.error(f"处理数据库失败 {db_path}: {e}")

        return success_count

    def process_all_databases(self, config: Dict, save_dir: Path) -> int:
        """处理所有数据库"""
        total_success = 0
        for db_config in config.get('databases', []):
            success_count = self.process_database(db_config, save_dir)
            total_success += success_count
            logger.info(f"数据库处理完成，成功下载: {success_count} 个图标")

        return total_success


def main():
    """主函数"""
    if len(sys.argv) != 3:
        print("用法: python script.py <配置文件> <保存目录>")
        sys.exit(1)

    config_file = sys.argv[1]
    save_dir = Path(sys.argv[2])
    logger.info("开始读取配置")

    if not os.path.exists(config_file):
        logger.error(f"配置文件不存在: {config_file}")
        sys.exit(1)

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"config : {config}")
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        sys.exit(1)

    # 创建下载器和处理器
    proxy = config.get('proxy', {})
    logger.info(f"proxy : {proxy}")
    apis = config.get('favicon_apis', {})
    logger.info(f"apis : {apis}")
    downloader = FaviconDownloader(proxy=proxy, apis=apis)
    processor = KeePassProcessor(downloader)

    logger.info("开始处理...")
    total_success = processor.process_all_databases(config, save_dir)

    print(downloader.stats.get_summary())

    failed_urls_file = save_dir / 'failed_urls.txt'
    downloader.stats.save_failed_urls(failed_urls_file)

    logger.info(f"处理完成！总共成功下载: {total_success} 个图标")


if __name__ == "__main__":
    main()