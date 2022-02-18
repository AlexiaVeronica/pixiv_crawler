import os
import re
import time

from PixivAPI import login_pixiv
from fake_useragent import UserAgent
import setting
import requests
from PixivApp import *
from rich import print
import threading

config = setting.set_config()


def headers():
    return {
        'User-Agent': UserAgent(verify_ssl=False).random,
        'Referer': 'https://www.pixiv.net/',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="98", "Microsoft Edge";v="98"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'cookie': config.data("headers", "Cookie")
    }


def get(url, params=None, max_retry=config.data("headers", "retry")):
    for retry in range(int(max_retry)):
        result = requests.get(url=url, headers=headers(), params=params)
        if result.status_code == 200:
            return result
        print("插图下载失败，重新第{}次请求：".format(retry))


def remove_str(content: str):
    file_name = re.sub('[/:*?"<>|]', '-', content)  # 去掉非法字符
    res_compile = re.compile(u'[\U00010000-\U0010ffff\\uD800-\\uDBFF\\uDC00-\\uDFFF]')
    return res_compile.sub("", file_name)


def rec_id(book_id):
    book_id = book_id if 'http' not in book_id else re.findall(r'/([0-9]+)/?', book_id)[0]
    return int(book_id) if book_id.isdigit() else f'输入信息 {book_id} 不是数字或链接！'


def input_(prompt, default=None):
    while True:
        ret = input(prompt)
        if ret != '':
            return ret
        elif default is not None:
            return default


def mkdir(file_path: str):
    if not os.path.exists(file_path):
        os.mkdir(file_path)


class Download:
    @staticmethod
    def save_image(image_id: int):
        response = PixivApp.illustration_information(image_id)
        if response.get("message") is None:
            image_url = response.image_urls['large']
            image_name = remove_str(response.title)
            file_path = config.data("user", "save_file")
            if not os.path.exists(os.path.join(file_path, f'{image_name}.png')):
                with open(os.path.join(file_path, f'{image_name}.png'), 'wb+') as file:
                    file.write(get(image_url).content)
                    print('成功下载图片：{}'.format(image_name))
            else:
                print(f"{image_name} 已经下载过了")
        else:
            print(response.get("message"))

    @staticmethod
    def threading_download(image_id_list: list):
        lock_tasks_list = threading.Lock()
        threads_pool = []

        # 生成下载队列.

        def downloader():
            """多线程下载函数"""
            nonlocal lock_tasks_list

            while image_id_list:
                lock_tasks_list.acquire()
                image_id = image_id_list.pop()
                lock_tasks_list.release()

                Download.save_image(image_id)

        for _ in range(5):
            th = threading.Thread(target=downloader)
            threads_pool.append(th)
            th.start()

        # wait downloader
        for th in threads_pool:
            th.join()


class PixivApp:
    @staticmethod
    def pixiv_app_api(max_retry=config.data("headers", "retry")):
        """构造API接口类"""
        for index, retry in enumerate(range(int(max_retry))):
            app_pixiv = AppPixivAPI()
            access_token = config.data("user", "access_token")
            refresh_token = config.data("user", "refresh_token")
            app_pixiv.set_auth(access_token=access_token, refresh_token=refresh_token)
            if app_pixiv.illust_recommended().error is not None:
                login_pixiv.refresh(refresh_token)
                print("令牌失效，尝试刷新令牌:retry {}".format(index))
            return app_pixiv

    @staticmethod
    def start_information():
        """收藏插画 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivApp.pixiv_app_api().illust_recommended()
        if response.error is None:
            return response.illusts
        return response.error

    @staticmethod
    def recommend_information():
        """推荐插画 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivApp.pixiv_app_api().illust_recommended()
        if response.error is None:
            return response.illusts
        return response.error

    @staticmethod
    def about_recommend(works_id: int):
        """插画相关推荐 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivApp.pixiv_app_api().illust_related(works_id)
        next_qs = PixivApp.pixiv_app_api().parse_qs(response.next_url)
        response2 = PixivApp.pixiv_app_api().illust_related(**next_qs)
        if response2.error is None:
            return response2.illusts
        return response2.error

    @staticmethod
    def follow_information():
        """关注用户信息 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivApp.pixiv_app_api().illust_follow()
        if response.error is None:
            return response.illusts
        return response.error

    @staticmethod
    def author_information(author_id: str):
        """作者作品集 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivApp.pixiv_app_api().user_illusts(author_id)
        if response.error is None:
            return [data.id for data in response.illusts]
        return response.error

    @staticmethod
    def search_information(png_name: str, search_target: str):
        """搜搜插画 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivApp.pixiv_app_api().search_illust(
            word=png_name, search_target=search_target
        )
        if response.error is None:
            return response.illusts
        return response.error

    @staticmethod
    def illustration_information(works_id: int):
        """插画信息 <class 'PixivApp.utils.JsonDict'>"""
        response = PixivApp.pixiv_app_api().illust_detail(works_id)
        if response.error is None:
            return response.illust
        return response.error
