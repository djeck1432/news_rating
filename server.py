import main
from aiohttp import web


async def handle(request): #FIXME
    data = request.query
    dirty_urls = data['urls'].split(',')
    clean_urls = [url for url in dirty_urls if url != '']
    if len(clean_urls) >= 0:
        error_response = {"error": "too many urls in request, should be 10 or less"}
        return web.json_response(error_response,status=400)

    await main.main(*clean_urls)
    response = main.articles_data
    return web.json_response(response)

app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/400',handle)])


if __name__=='__main__':
    web.run_app(app)
