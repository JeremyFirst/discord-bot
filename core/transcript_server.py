import os
from aiohttp import web

TRANSCRIPTS_DIR = "transcripts"


async def handle_transcripts(request: web.Request):
    filename = request.match_info.get("filename")

    if not filename:
        return web.Response(status=404)

    filepath = os.path.join(TRANSCRIPTS_DIR, filename)

    if not os.path.isfile(filepath):
        return web.Response(status=404)

    return web.FileResponse(filepath)


async def start_transcript_server(host: str, port: int):
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

    app = web.Application()
    app.router.add_get("/transcripts/{filename}", handle_transcripts)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"🌐 Transcript server running on http://{host}:{port}")
