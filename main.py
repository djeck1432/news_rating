import aiohttp
import asyncio


async def fetch(session, url):
    async with session.get(url,ssl=False) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    async with aiohttp.ClientSession() as session:
        html = await fetch(session, 'https://inosmi.ru/politic/20200702/247694385.html')
        print(html)


asyncio.run(main())
