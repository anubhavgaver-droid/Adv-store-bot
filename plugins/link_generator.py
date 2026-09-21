#(©)Codexbotz

import asyncio
import base64
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid
from bot import Bot
from helper_func import encode, admin

async def get_chat_and_msg_id(client: Client, message: Message):
    """
    Forwarded message ya Telegram link se Chat ID aur Message ID extract karta hai.
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
                chat_id = int(f"-100{chat_ref.replace('c/', '')}")
            elif chat_ref.isdigit():
                chat_id = int(f"-100{chat_ref}")
            else:
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


# ==============================================================================
# 1. /batch Command Handler (DIRECT LINK - NO COPYING)
# ==============================================================================
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

        # Check: Bot channel mein Admin hai ya nahi
        if not await is_bot_admin(client, f_chat_id):
            await first_message.reply(
                "⚠️ **Warning:** Main is channel mein **Admin** nahi hoon!\n\n"
                "Kripya pehle mujhe us channel mein Admin banayein.",
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

        if f_chat_id != s_chat_id:
            await second_message.reply("❌ **Error:** Both messages must be from the same channel!", quote=True)
            continue

        if not await is_bot_admin(client, s_chat_id):
            await second_message.reply(
                "⚠️ **Warning:** Main is channel mein **Admin** nahi hoon!\n\n"
                "Kripya pehle mujhe us channel mein Admin banayein.",
                quote=True
            )
            continue

        break

    # 🚀 NO COPYING NEEDED: Direct Channel IDs se Range String Encode karna
    # Absolute value target channel ID aur first/last message ID ke saath
    string = f"get-{f_msg_id * abs(f_chat_id)}-{s_msg_id * abs(f_chat_id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    
    total_files = (s_msg_id - f_msg_id) + 1
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    
    await second_message.reply_text(
        f"<b>Here is your batch link</b>\n\n"
        f"📦 <b>Total Files:</b> {total_files}\n"
        f"🔗 <b>Link:</b> {link}", 
        quote=True, 
        reply_markup=reply_markup
    )


# ==============================================================================
# 2. /genlink Command Handler (DIRECT LINK - NO COPYING)
# ==============================================================================
@Bot.on_message(filters.private & admin & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    while True:
        try:
            channel_message = await client.ask(
                text="Send A Message For To Get Your Shareable Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | filters.text | filters.media),
                timeout=60
            )
        except Exception:
            return

        if channel_message.text and channel_message.text.startswith("/"):
            await channel_message.reply("Process Cancelled!")
            return

        chat_id, msg_id = await get_chat_and_msg_id(client, channel_message)
        
        if chat_id and msg_id:
            if not await is_bot_admin(client, chat_id):
                await channel_message.reply(
                    "⚠️ **Warning:** Main is channel mein **Admin** nahi hoon!\n\n"
                    "Kripya pehle mujhe us channel mein Admin banayein.",
                    quote=True
                )
                continue
            
            # Channel ID aur Message ID directly use karenge
            final_chat_id = chat_id
            final_msg_id = msg_id
            break
        else:
            # Agar PM mein direct bheja gaya hai tabhi DB Channel me save karenge
            try:
                post_msg = await channel_message.copy(chat_id=client.db_channel.id, disable_notification=True)
                final_chat_id = client.db_channel.id
                final_msg_id = post_msg.id
                break
            except Exception as e:
                await channel_message.reply(f"❌ Error saving message: {e}", quote=True)
                continue

    base64_string = await encode(f"get-{final_msg_id * abs(final_chat_id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await channel_message.reply_text(f"<b>Here is your link</b>\n\n{link}", quote=True, reply_markup=reply_markup)
