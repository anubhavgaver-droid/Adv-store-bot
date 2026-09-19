import urllib.parse
from aiohttp import web

routes = web.RouteTableDef()

# 1. रूट हैंडलर (HTML Web Player सर्व करेगा)
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.FileResponse('web/index.html')

# 2. ऑडियो स्ट्रीमिंग + रेंज हैंडलर
@routes.get("/stream/{file_id}")
async def stream_handler(request):
    file_id = request.match_info.get('file_id')
    bot = request.app['bot']

    try:
        msg = await bot.get_messages(bot.db_channel.id, int(file_id))
        media = msg.audio or msg.document or msg.video
        if not media:
            return web.Response(status=404, text="File Not Found")

        file_size = getattr(media, 'file_size', 0)
        file_name = getattr(media, 'file_name', 'Audio File')

        # डेटा चैनल में लॉग भेजना
        try:
            log_text = (
                f"🎧 **Watch Online Stream Triggered!**\n\n"
                f"📁 **File Name:** `{file_name}`\n"
                f"🆔 **Message ID:** `{file_id}`\n"
                f"⚡ **Status:** Direct Byte-Range Streaming Active."
            )
            await bot.send_message(chat_id=bot.db_channel.id, text=log_text)
        except Exception:
            pass

        # HTTP Range Requests का सपोर्ट
        range_header = request.headers.get('Range')
        
        if range_header and file_size > 0:
            bytes_range = range_header.replace('bytes=', '').split('-')
            start = int(bytes_range[0]) if bytes_range[0] else 0
            end = int(bytes_range[1]) if len(bytes_range) > 1 and bytes_range[1] else file_size - 1

            if start >= file_size or end >= file_size:
                return web.Response(status=416, headers={'Content-Range': f'bytes */{file_size}'})

            content_length = (end - start) + 1
            headers = {
                'Content-Type': 'audio/mpeg',
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Content-Length': str(content_length),
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'no-cache',
                'Content-Disposition': 'inline'
            }

            response = web.StreamResponse(status=206, headers=headers)
            await response.prepare(request)

            offset = 0
            async for chunk in bot.stream_media(media):
                chunk_len = len(chunk)
                if offset + chunk_len > start:
                    chunk_start = max(0, start - offset)
                    chunk_end = min(chunk_len, end - offset + 1)
                    await response.write(chunk[chunk_start:chunk_end])
                offset += chunk_len
                if offset > end:
                    break
            return response

        else:
            headers = {
                'Content-Type': 'audio/mpeg',
                'Accept-Ranges': 'bytes',
                'Content-Length': str(file_size) if file_size else '0',
                'Content-Disposition': 'inline'
            }
            response = web.StreamResponse(status=200, headers=headers)
            await response.prepare(request)

            async for chunk in bot.stream_media(media):
                await response.write(chunk)

            return response

    except Exception as e:
        return web.Response(status=500, text=f"Streaming Error: {str(e)}")
