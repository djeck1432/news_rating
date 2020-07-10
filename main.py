import aiohttp
import asyncio

import logging
import time
from urllib.parse import urlparse
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
TEXT_ARTICLES = [
    'https://inosmi.ru/politic/20200704/247701497.html',
    'https://lenta.ru/articles/2020/07/04/zahvat/',
    'https://inosmi.ru/social/20200704/247680141',
    'https://inosmi.ru/social/20200704/247697320.html',
    'https://inosmi.ru/military/20200704/247668031.html'
    ]

articles_data = []
morph = pymorphy2.MorphAnalyzer()
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
    parse_result = urlparse(response_url)
    website_name = parse_result.netloc
    # result = re.findall(r'//\w+.\w+', response_url)
    # converted_host = result[0].replace('//','')
    # website_name = converted_host
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


async def  process_article(url,processed_max_time=3):
    article_info = {
        'status': None,
        'url': url,
        'words_count': None,
        'score': None,
    }
    async with aiohttp.ClientSession() as session:
        with managed_time_processs() as timer_process:
            try:
                async with timeout(processed_max_time) as cm:
                    html = await fetch(session, url)
                    sanitized_html = sanitize(html)
                    article_words = await text_tools.split_by_words(morph, sanitized_html)
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


def test_process_article():
    asyncio.run(process_article('https://inosmi.ru/social/20200708/247723129.html'))
    assert  'OK' == articles_data[0]['status']

    asyncio.run(process_article('https://lenta.ru/articles/2020/07/04/zahvat/'))
    assert 'PARSING_ERROR' == articles_data[1]['status']

    asyncio.run(process_article('https://inosmi.ru/social/20200708/247723129.html', processed_max_time=1))
    assert 'TIMEOUT' == articles_data[2]['status']


async def get_analysis_process(*args):
    logging.basicConfig(level=logging.INFO)
    text_articles = args

    async with create_task_group() as process:
        for article_url in TEXT_ARTICLES:
            await process.spawn(process_article, article_url)
    for article in articles_data:
        print(article['status'])

if __name__=='__main__':
    run(get_analysis_process)
