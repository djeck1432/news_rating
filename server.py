import main
from aiohttp import web
import asyncio


async def handle(request):
    data = request.query
    dirty_urls = data['urls'].split(',')
    clean_urls = [url for url in dirty_urls if url != '']
    if len(clean_urls) >= 10:
        error_response = {"error": "too many urls in request, should be 10 or less"}
        return web.json_response(error_response,status=400)

    article_queue = asyncio.Queue()
    await main.get_analysis_process(article_queue,*clean_urls,)
    response = await article_queue.get()
    return web.json_response(response)


app = web.Application()
app.add_routes([web.get('/', handle)])


if __name__=='__main__':
    web.run_app(app)
