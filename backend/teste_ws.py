import asyncio, json, websockets

async def main():
    async with websockets.connect('ws://127.0.0.1:8000/ws/stream') as ws:
        while True:
            a = json.loads(await ws.recv())['analysis']
            if a['status'] == 'analisando':
                print(f"analisando... {a['progresso']}%")
            else:
                print(f"{a['resultado'].upper():14} | rosa={a['pct_rosa']}% | tulipa={a['pct_tulipa']}% | amostras={a['amostras']}")

asyncio.run(main())
