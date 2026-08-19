import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from pyrogram.enums import ChatMemberStatus
from bot import Bot
from helper_func import encode, admin

async def get_chat_and_msg_id(client: Client, message: Message):
    """
    Forwarded message ya Telegram link se Chat ID aur Message ID nikalne ke liye function.
    """
    if message.forward_from_chat:
        return message.forward_from_chat.id, message.forward_from_message_id
    
    elif message.text and "t.me/" in message.text:
        text = message.text.strip()
        try:
            parts = text.split("/")
            msg_id = int(parts[-1].split("?")[0])
            chat_ref = parts[-2]
            
            if chat_ref.startswith("c/"):
                # Private channel link (e.g. https://t.me/c/1234567890/10)
                chat_id = int(f"-100{chat_ref.replace('c/', '')}")
            elif chat_ref.isdigit():
                chat_id = int(f"-100{chat_ref}")
            else:
                # Public channel username (e.g. https://t.me/channel_username/10)
                chat = await client.get_chat(chat_ref)
                chat_id = chat.id
                
            return chat_id, msg_id
        except Exception:
            return None, None
            
    return None, None


async def is_bot_admin(client: Client, chat_id: int) -> bool:
    """
    Check karta hai ki Bot target channel mein Admin hai ya nahi.
    """
    try:
        member = await client.get_chat_member(chat_id, "me")
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False


@Bot.on_message(filters.private & admin & filters.command('batch'))
async def batch(client: Client, message: Message):
    # --- FIRST MESSAGE ---
    while True:
        try:
            first_message = await client.ask(
                text="Forward The Batch First Message From your Batch Channel (With Forward Tag).. or Give Me Batch First Message link from your batch channel",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | filters.text),
                timeout=60
            )
        except Exception:
            return

        if first_message.text and first_message.text.startswith("/"):
            await first_message.reply("Process Cancelled!")
            return

        f_chat_id, f_msg_id = await get_chat_and_msg_id(client, first_message)
        
        if not f_chat_id or not f_msg_id:
            await first_message.reply("❌ Invalid Link or Forwarded Message! Please try again.", quote=True)
            continue

        # ⚠️ Check: Kya Bot Channel mein Admin hai?
        if not await is_bot_admin(client, f_chat_id):
            await first_message.reply(
                "⚠️ **Warning:** Main is channel mein **Admin** nahi hoon!\n\n"
                "Kripya pehle mujhe us channel mein Admin banayein jiske messages aap link karna chahte hain.",
                quote=True
            )
            continue

        break

    # --- LAST MESSAGE ---
    while True:
        try:
            second_message = await client.ask(
                text="Forward The Batch Last Message From your Batch Channel (With Forward Tag).. or Give Me Batch Last Message link from your batch channel",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | filters.text),
                timeout=60
            )
        except Exception:
            return

        if second_message.text and second_message.text.startswith("/"):
            await second_message.reply("Process Cancelled!")
            return

        s_chat_id, s_msg_id = await get_chat_and_msg_id(client, second_message)
        
        if not s_chat_id or not s_msg_id:
            await second_message.reply("❌ Invalid Link or Forwarded Message! Please try again.", quote=True)
            continue

        # Check ki dono messages same channel ke hain ya nahi
        if f_chat_id != s_chat_id:
            await second_message.reply("❌ **Error:** Both messages must be from the same channel!", quote=True)
            continue

        # ⚠️ Check: Kya Bot Channel mein Admin hai?
        if not await is_bot_admin(client, s_chat_id):
            await second_message.reply(
                "⚠️ **Warning:** Main is channel mein **Admin** nahi hoon!\n\n"
                "Kripya pehle mujhe us channel mein Admin banayein.",
                quote=True
            )
            continue

        break

    # Link Generation
    string = f"get-{f_msg_id * abs(f_chat_id)}-{s_msg_id * abs(f_chat_id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(f"<b>Here is your link</b>\n\n{link}", quote=True, reply_markup=reply_markup)
