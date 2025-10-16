# -*- coding: utf-8 -*-

import os, re
import sys
import requests
import hashlib
import json
import base64

import pykeepass

from urllib.parse import urlparse
from bs4 import BeautifulSoup
import urllib3

# 屏蔽 InsecureRequestWarning 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}

def extract_redirect_url_from_meta(html_content):
      soup = BeautifulSoup(html_content, 'html.parser')
      meta_tag = soup.find('meta', attrs={'http-equiv': 'refresh'})
      if meta_tag:
         content = meta_tag.get('content', '')
         match = re.search(r'URL=\'(.*?)\'', content) # 使用正则表达式获取 URL
         if match:
             return match.group(1)
      return None

def download_favicon(url, name, save_dir="", apis=[], proxy={}):
    def is_base64_image(st):
        return re.match(r'^data:image/(png|jpeg|jpg|gif|webp|x-icon);base64', st)
    
    def pt_link(response):
        soup = BeautifulSoup(response.text, 'html.parser')
        favicon_link = None
        link_tag = soup.find('link', rel='icon')
        if link_tag:
            favicon_link = link_tag.get('href')
        if not favicon_link:
            link_tag = soup.find('link', rel='shortcut icon')
            if link_tag:
                favicon_link = link_tag.get('href')
        if not favicon_link:
            link_tag = soup.find('link', rel='SHORTCUT ICON')
            if link_tag:
                favicon_link = link_tag.get('href')
        if not favicon_link:
            if base_url.endswith("/"):
                favicon_link = base_url + "favicon.ico"
            else:
                favicon_link = base_url + "/favicon.ico"
        if favicon_link:
            if is_base64_image(favicon_link):
                file_path = os.path.join(save_dir, name)
                data = base64.b64decode(favicon_link)
                with open(file_path, 'wb') as f:
                    f.write(data)
                return file_path
            elif favicon_link.startswith("http"):
                return download_file(favicon_link, name, save_dir)
            elif favicon_link.startswith("//"):
                return download_file("https:" + favicon_link, name, save_dir)
            else:
                if favicon_link.startswith("/"):
                    return download_file(f"{url}{favicon_link}", name, save_dir)
                return download_file(f"{url}/{favicon_link}", name, save_dir)
    
    def download_file(url, name, save_dir):
        try:
            print(f"Start download favicon : {url}")
            try:
                print("download url 1 : " + url)
                favicon_response = requests.get(url, verify=False, timeout=(30, 30), headers=HEADERS, proxies=proxy)
            except Exception as e:
                print("download url 2 : " + url)
                favicon_response = requests.get(url, verify=False, timeout=(30, 30), headers=HEADERS)
            favicon_response.raise_for_status()
            
            if url.endswith("svg"):
                name = name.replace(".ico", ".svg")
            elif url.endswith("jpg"):
                name = name.replace(".ico", ".jpg")
            elif url.endswith("jepg"):
                name = name.replace(".ico", ".jepg")
            elif url.endswith("png"):
                name = name.replace(".ico", ".png")
            elif url.endswith("webp"):
                name = name.replace(".ico", ".webp")

            # 保持
            print('=======================================')
            print("content-type : " + favicon_response.headers['Content-Type'])
            print("download name : "  + url + " / " + name)
            file_path = os.path.join(save_dir, name)
            content = favicon_response.content

            print(f'len : {len(content)}')
            if len(content) <= 512:
                return None
            
            try:
                pt_link(favicon_response)
            except:
                pass

            if isinstance(content, str) and is_base64_image(content):
                print("is base64 image")
                data = base64.b64decode(content)
                with open(file_path, 'wb') as f:
                    f.write(data)
                return file_path
            else:
                print("not base64 image")
                with open(file_path, 'wb') as f:
                    f.write(content)

            print(f"Succssful download favicon: {file_path}")
            return file_path
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"Error download timeout or connection : {url}")
            print(e)
            return None
        except Exception as e:
            print(f"Error download: {url} , {e}")
            return None

    def download_favicon_by_method1(url, name, save_dir):
        print("Try download method 1 : ")
        favicon_link = f"{base_url}/favicon.ico"
        return download_file(favicon_link, name, save_dir)

    def download_favicon_by_method2(url, name, save_dir):
        print("Try download method 2 : " + url)
        try:
            response = requests.get(url, verify=False, timeout=5)
            response.raise_for_status()
            redirect_url = extract_redirect_url_from_meta(response.text)
            parsed_url1 = urlparse(url)
            parsed_url2 = urlparse(response.url)

            if parsed_url1.netloc != parsed_url2.netloc:
                url = response.url

            if redirect_url:
                url = f"{response.url}/{redirect_url}"
                print("use redirect url download : " + url)
                response = requests.get(url, verify=False, timeout=5)
                response.raise_for_status()

            pt_link(response)

        except Exception as e:
            print("Error download method 2")
            print(e)
        return None

    def download_favicon_by_method3(domain, name, save_dir):
        print("Try download method 3 : ")
        for api in apis:
            get_favicon_url = api.replace(r"{domain}", domain)
            print("Try download method url : " + get_favicon_url)
            file = download_file(get_favicon_url, name, save_dir)
            if file is not None:
                return file

    # 开始下载
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    parsed_url = urlparse(url)
    domain = parsed_url.netloc if parsed_url.netloc != '' else parsed_url.path
    
    if domain != '':
        scheme = parsed_url.scheme
        
        # 方法 1
        if scheme == 'http' or scheme == 'https':
            base_url = f"{scheme}://{domain}"
            file = download_favicon_by_method2(base_url, name, save_dir)
            if file is not None:
                return file
        else:
            # https
            base_url = f"https://{domain}"
            file = download_favicon_by_method2(base_url, name, save_dir)
            if file is not None:
                return file
            
            # http
            base_url = f"http://{domain}"
            file = download_favicon_by_method2(base_url, name, save_dir)
            if file is not None:
                return file
    
        # 方法 3
        file = download_favicon_by_method3(domain, name, save_dir)
        if file is not None:
            return file
        
        
    return None

def download_form_database(db, save_dir):
    with pykeepass.PyKeePass(db['path'], db['password']) as kdb:
        for entry in kdb.entries:
            url = entry.url if entry.url else ""
            if url != '':
                name = hashlib.md5(url.encode('utf-8')).hexdigest() + ".ico"
                if not os.path.exists(f"{save_dir}/{name}"):
                    download_favicon(url, name, save_dir, config['favicon_apis'], config['proxy'])
                else:
                    print(f"Already existing : {name}")
                print("---")
                print("")

def download_icons(config, save_dir):
    try:
        for db in config['databases']:
            download_form_database(db, save_dir)
    except Exception as e:
        pass


if __name__ == "__main__":
    print("---- ready ----")
    config_file = sys.argv[1]
    save_dir = sys.argv[2]
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf8") as f:
            config = json.loads(f.read())
            download_icons(config, save_dir)
    print("---- complete ----")
    