import urllib.parse
from aiohttp import web

routes = web.RouteTableDef()

# 1. रूट हैंडलर (HTML Web Player सर्व करेगा)
@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.FileResponse('web/index.html')

# 2. ऑडियो स्ट्रीमिंग + चैनल डेटा लॉगर रूट
@routes.get("/stream/{file_id}")
async def stream_handler(request):
    file_id = request.match_info.get('file_id')
    bot = request.app['bot']  # Bot Instance from bot.py
    
    try:
        # DB Channel से exact Message फेच करें
        msg = await bot.get_messages(bot.db_channel.id, int(file_id))
        
        media = msg.audio or msg.document or msg.video
        if not media:
            return web.Response(status=404, text="File Not Found")

        # -------------------------------------------------------------
        # 📢 डेटा चैनल (CHANNEL_ID) पर स्ट्रीम की जानकारी भेजना
        # -------------------------------------------------------------
        try:
            file_name = getattr(media, 'file_name', 'Audio File')
            log_text = (
                f"🎧 **Watch Online Stream Triggered!**\n\n"
                f"📁 **File Name:** `{file_name}`\n"
                f"🆔 **Message ID:** `{file_id}`\n"
                f"🌐 **Player URL:** {bot.config.URL if hasattr(bot, 'config') else 'Live Stream'}\n"
                f"⚡ **Status:** File redirected & streaming successfully."
            )
            await bot.send_message(chat_id=bot.db_channel.id, text=log_text)
        except Exception as log_err:
            print(f"Channel Log Error: {log_err}")
        # -------------------------------------------------------------

        # ऑडियो स्ट्रीम रिस्पॉन्स तैयार करें
        response = web.StreamResponse(
            status=200,
            reason='OK',
            headers={
                'Content-Type': 'audio/mpeg',
                'Content-Disposition': 'inline'
            }
        )
        await response.prepare(request)
        
        # टेलीग्राम सर्वर से फाइल को स्ट्रीम (chunk by chunk) करें
        async for chunk in bot.stream_media(media):
            await response.write(chunk)
            
        return response

    except Exception as e:
        return web.Response(status=500, text=f"Error streaming file: {str(e)}")
