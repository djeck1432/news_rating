import aiohttp
import asyncio

import logging
import time
import re
from async_timeout import timeout
import requests
from contextlib import contextmanager
from adapters.inosmi_ru import sanitize
import adapters
from anyio import create_task_group, run
import pymorphy2
import text_tools
from enum import Enum


logger = logging.getLogger('time_log')
articles_data = []
TEXT_ARTICLES = [
    'https://inosmi.ru/politic/20200704/247701497.html',
    'https://lenta.ru/articles/2020/07/04/zahvat/',
    'https://inosmi.ru/social/20200704/247680141',
    'https://inosmi.ru/social/20200704/247697320.html',
    'https://inosmi.ru/military/20200704/247668031.html'
    ]
CHARGED_WORDS_FILE = 'negative_words.txt'


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


@contextmanager
def managed_time_processs():
    start_time = time.monotonic()
    try:
        yield
    finally:
        end_time = time.monotonic()
        result_time = end_time - start_time
        logger.info(f'The result for: {round(result_time,2)}s.')


def get_website_name(url):
    response_url = requests.get(url).url
    result = re.findall(r'//\w+.\w+', response_url)
    converted_host = result[0].replace('//','')
    website_name = converted_host
    if not website_name in adapters.SANITIZERS:
        return website_name


def fetch_charged_words(text_file):
    charged_words = []
    with open(text_file, 'r') as special_words:
        for word in special_words:
            charged_words.append(word.strip('\n'))

    return charged_words


async def fetch(session, url):
    async with session.get(url,ssl=False) as response:
        response.raise_for_status()
        return await response.text()


async def  process_article(url,morph):
    article_info = {
        'status': None,
        'url': url,
        'words_count': None,
        'score': None,
    }
    async with aiohttp.ClientSession() as session:
        with managed_time_processs() as timer_process:
            try:
                async with timeout(5) as cm:
                    html = await fetch(session, url)
                    sanitized_html = sanitize(html)
                    article_words = text_tools.split_by_words(morph, sanitized_html)
                    charged_words = fetch_charged_words(CHARGED_WORDS_FILE)
                    article_info['status'] = ProcessingStatus.OK.value
                    article_info['words_count'] = len(article_words)
                    article_info['score'] = text_tools.calculate_jaundice_rate(article_words, charged_words)

            except adapters.ArticleNotFound:
                article_info['status'] = ProcessingStatus.PARSING_ERROR.value
                article_info['url'] = f'The artciel on {get_website_name(url)}'

            except asyncio.TimeoutError:
                article_info['status'] = ProcessingStatus.TIMEOUT.value

            except aiohttp.ClientResponseError:
                article_info['status'] = ProcessingStatus.FETCH_ERROR.value

        articles_data.append(article_info)






async def main(*args):
    logging.basicConfig(level=logging.INFO)
    text_articles = args
    morph = pymorphy2.MorphAnalyzer()
    async with create_task_group() as process:
        for article_url in text_articles:
            await process.spawn(process_article, article_url, morph)

    for article in articles_data:
        print(f'status: {article["status"]}')
        print(f'score: {article["score"]}')
        print(f'words count: {article["words_count"]}')
        print('\n')


if __name__=='__main__':
    run(main)

