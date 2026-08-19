import asyncio
import os
import random
import sys
import re
import string 
import string as rohit
import time
import logging
import traceback
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__, enums
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MessageNotModified
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, MessageDeleteForbidden
from bot import Bot
from config import *
from helper_func import *
from database.database import *
from database.db_premium import *
from pytz import timezone

logger = logging.getLogger(__name__)

# ==================== GLOBAL MONKEY PATCH ====================
original_reply = Message.reply
async def patched_reply(self, *args, **kwargs):
    kwargs.setdefault('quote', False)
    return await original_reply(self, *args, **kwargs)
Message.reply = patched_reply

original_reply_text = Message.reply_text
async def patched_reply_text(self, *args, **kwargs):
    kwargs.setdefault('quote', False)
    return await original_reply_text(self, *args, **kwargs)
Message.reply_text = patched_reply_text

original_reply_photo = Message.reply_photo
async def patched_reply_photo(self, *args, **kwargs):
    kwargs.setdefault('quote', False)
    return await original_reply_photo(self, *args, **kwargs)
Message.reply_photo = patched_reply_photo
# ==============================================================

BAN_SUPPORT = f"{BAN_SUPPORT}"
TUT_VID = f"{TUT_VID}"

# Global dict for tracking cancelled deliveries
cancel_tasks = {}

# 🛡️ Safe DB Channel Fetcher
def get_db_channel_id(client: Client):
    if hasattr(client, "db_channel") and client.db_channel:
        return getattr(client.db_channel, "id", client.db_channel)
    return DB_CHANNEL

# 🛡️ Safe MongoDB Collection Access
def get_mb_collection():
    if hasattr(db, "multi_batches"):
        return db.multi_batches
    elif hasattr(db, "db") and hasattr(db.db, "multi_batches"):
        return db.db["multi_batches"]
    elif hasattr(db, "col") and hasattr(db.col, "database"):
        return db.col.database["multi_batches"]
    else:
        return db.db["multi_batches"]

# 🛠️ Channel Link / Forward Msg Parser
async def get_chat_and_msg_id(client: Client, message: Message):
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
        except Exception as e:
            logger.error(f"❌ [LINK PARSE ERROR] {e}")
            return None, None
    return None, None


# ==============================================================================
# 🚀 1. MAIN /start COMMAND HANDLER
# ==============================================================================
@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except Exception:
        await message.react(emoji="⚡️", big=True)
    
    user_id = message.from_user.id
    is_premium = await is_premium_user(user_id)
    
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except Exception:
            pass

    # ✅ Check Force Subscription
    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    # ✅ Check Ban Status
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            "<b>⛔️ You are Bᴀɴɴᴇᴅ from using this bot.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)]])
        )

    FILE_AUTO_DELETE = await db.get_del_timer()
    text = message.text

    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        # 🔐 Token Verification System
        verify_status = await db.get_verify_status(user_id) or {}

        if SHORTLINK_URL or SHORTLINK_API:
            if verify_status.get('is_verified', False) and VERIFY_EXPIRE < (time.time() - verify_status.get('verified_time', 0)):
                await db.update_verify_status(user_id, is_verified=False)
                verify_status['is_verified'] = False 

            if "verify_" in text:
                _, token = text.split("_", 1)
                if verify_status.get('verify_token') != token:
                    return await message.reply("⚠️ Invalid Token. Please /start again.")

                await db.update_verify_status(user_id, is_verified=True, verified_time=time.time())
                current = await db.get_verify_count(user_id)
                await db.set_verify_count(user_id, current + 1)

                file_id = verify_status.get("link", "") or base64_string
                btn = [[InlineKeyboardButton("🚀 Gᴇᴛ Fɪʟᴇ Nᴏᴡ", url=f"https://t.me/{client.username}?start={file_id}")]]
                
                return await message.reply(
                    f"✅ <b>𝗧𝗼𝗸𝗲𝗻 𝘃𝗲𝗿𝗶𝗳𝗶𝗲𝗱!</b>\n\nValid for: {get_exp_time(VERIFY_EXPIRE)}\n\nClick button below 👇",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=True
                )

            if not verify_status.get('is_verified', False) and not is_premium:
                token = ''.join(random.choices(rohit.ascii_letters + rohit.digits, k=10))
                await db.update_verify_status(user_id, verify_token=token, link=base64_string)
                
                link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{client.username}?start=verify_{token}')
                btn = [
                    [InlineKeyboardButton("• 𝚅𝙴𝚁𝙸𝙵𝚈 •", url=link), InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
                    [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="premium", style=enums.ButtonStyle.PRIMARY)]
                ]
                return await message.reply(
                    f"<b>𝗬𝗼𝘂𝗿 𝘁𝗼𝗸𝗲𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. Please refresh your token to continue.</b>\n\n<b>Token Timeout:</b> {get_exp_time(VERIFY_EXPIRE)}",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=True
                )

        # 🎬 A) MULTI-BATCH MASTER LINK PAYLOAD
        if base64_string.startswith("mbatch_"):
            batch_id = base64_string.replace("mbatch_", "").strip().lower()
            mb_col = get_mb_collection()
            batch_data = await mb_col.find_one({"batch_id": batch_id})

            if not batch_data or not batch_data.get("ranges"):
                return await message.reply("❌ <b>Invalid link or no episodes available in this batch!</b>")

            buttons = []
            for index, item in enumerate(batch_data["ranges"]):
                buttons.append([
                    InlineKeyboardButton(
                        text=f"🎬 {item['title']}",
                        callback_data=f"user_mget_{batch_id}_{index}"
                    )
                ])

            markup = InlineKeyboardMarkup(buttons)
            return await message.reply(
                f"<b>🎬 Select Episode Range:</b>\n\nBatch Name: <code>{batch_id}</code>",
                reply_markup=markup
            )

        # 📦 B) SINGLE / STANDARD BATCH FILE PAYLOAD
        string = await decode(base64_string)
        argument = string.split("-")

        ids = []
        db_chan_id = get_db_channel_id(client)

        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(db_chan_id))
                end = int(int(argument[2]) / abs(db_chan_id))
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                return print(f"Error decoding IDs: {e}")
            
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(db_chan_id))]
            except Exception as e:
                return print(f"Error decoding ID: {e}")

        cancel_tasks[user_id] = False

        wait_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁🛠️", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("🌀 𝙲𝙰𝙽𝙲𝙴𝙻 🌀", callback_data=f"cancel_delivery_{user_id}", style=enums.ButtonStyle.DANGER)]
        ])
        temp_msg = await message.reply("<b>🔺 ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>", reply_markup=wait_markup)
        
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            try: await temp_msg.delete()
            except Exception: pass
            return await message.reply_text(f"Something went wrong: {e}")

        codeflix_msgs = []
        for msg in messages:
            await asyncio.sleep(0.05)
            if cancel_tasks.get(user_id, False):
                break
            if msg.service or (not msg.text and not msg.media):
                continue  

            await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)
            caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, 
                                             filename=msg.document.file_name) if bool(CUSTOM_CAPTION) and bool(msg.document)
                       else ("" if not msg.caption else msg.caption.html))

            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                copied_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, 
                                            reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                codeflix_msgs.append(copied_msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                if cancel_tasks.get(user_id, False): break
                copied_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, 
                                            reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                codeflix_msgs.append(copied_msg)
            except Exception as e:
                print(f"Failed to send message: {e}")

            await asyncio.sleep(0.8)

        was_cancelled = cancel_tasks.pop(user_id, False)
        try: await temp_msg.delete()
        except Exception: pass

        if was_cancelled:
            return await message.reply_text("❌ <b>Delivery cancelled successfully!</b>")

        if FILE_AUTO_DELETE > 0 and codeflix_msgs:
            notification_msg = await message.reply(
                f"<b>This file will be deleted in {get_exp_time(FILE_AUTO_DELETE)}. Save or forward it!</b>"
            )

            await asyncio.sleep(FILE_AUTO_DELETE)

            for snt_msg in codeflix_msgs:    
                if snt_msg:
                    try: await snt_msg.delete()  
                    except Exception: pass

            try:
                reload_url = f"https://t.me/{client.username}?start={message.command[1]}" if message.command and len(message.command) > 1 else None
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ!", url=reload_url)]]) if reload_url else None
                await notification_msg.edit(
                    "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇</b>",
                    reply_markup=keyboard
                )
            except Exception: pass
    else:
        try:
            sticker_msg = await message.reply_sticker(sticker=START_STICKER)
            await asyncio.sleep(0.4)
            await sticker_msg.delete()
        except Exception: pass  
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟs •", callback_data='channels', style=enums.ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"), InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data="help")]
        ])
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup
        )


# ==============================================================================
# ⚙️ 2. MULTI-BATCH ADMIN MENU & COMMAND
# ==============================================================================

async def show_admin_batch_menu(client: Client, user_id: int, batch_id: str, message_to_edit=None):
    mb_col = get_mb_collection()
    batch_data = await mb_col.find_one({"batch_id": batch_id})
    ranges = batch_data.get("ranges", []) if batch_data else []

    buttons = []
    for index, item in enumerate(ranges):
        buttons.append([
            InlineKeyboardButton(f"📺 {item['title']}", callback_data="ignore"),
            InlineKeyboardButton("❌ Delete", callback_data=f"del_mrange_{batch_id}_{index}")
        ])

    buttons.append([InlineKeyboardButton("➕ Add New Episode Range (+)", callback_data=f"add_mrange_{batch_id}")])
    buttons.append([InlineKeyboardButton("🔗 Get Master Share Link", callback_data=f"get_mlink_{batch_id}")])

    markup = InlineKeyboardMarkup(buttons)
    text = (
        f"⚙️ <b>Multi-Batch Editor:</b> <code>{batch_id}</code>\n\n"
        f"Total Episode Buttons: <code>{len(ranges)}</code>\n\n"
        f"Naya episode range add karne ke liye <b>➕ Add New Episode Range (+)</b> par click karein."
    )

    if message_to_edit:
        await message_to_edit.edit_text(text, reply_markup=markup)
    else:
        await client.send_message(user_id, text, reply_markup=markup)


@Bot.on_message(filters.command("multi_batch") & filters.private & admin)
async def multi_batch_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ <b>Usage:</b> <code>/multi_batch <batch_name></code>\n\nExample: <code>/multi_batch naruto_series</code>")

    batch_id = message.command[1].strip().lower()
    mb_col = get_mb_collection()
    batch_data = await mb_col.find_one({"batch_id": batch_id})

    if not batch_data:
        await mb_col.insert_one({"batch_id": batch_id, "ranges": []})

    await show_admin_batch_menu(client, message.from_user.id, batch_id)


# ==============================================================================
# 🎬 3. COMBINED CALLBACK QUERY HANDLER (Admin & User Actions)
# ==============================================================================

@Bot.on_callback_query(filters.regex(r"^(add_mrange_|del_mrange_|get_mlink_|user_mget_|ignore)"))
async def multi_batch_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "ignore":
        return await query.answer("यह सिर्फ़ टाइटल बटन है।", show_alert=False)

    try:
        # 🟢 A) USER CLICKS EPISODE RANGE BUTTON (e.g. Ep 1 to 100)
        if data.startswith("user_mget_"):
            raw_data = data.replace("user_mget_", "")
            batch_id, index_str = raw_data.rsplit("_", 1)  # Safe split for underscores in batch_id
            index = int(index_str)

            # Verification Check
            is_premium = await is_premium_user(user_id)
            verify_status = await db.get_verify_status(user_id) or {}

            if SHORTLINK_URL or SHORTLINK_API:
                if verify_status.get('is_verified', False) and VERIFY_EXPIRE < (time.time() - verify_status.get('verified_time', 0)):
                    await db.update_verify_status(user_id, is_verified=False)
                    verify_status['is_verified'] = False

                if not verify_status.get('is_verified', False) and not is_premium:
                    token = ''.join(random.choices(rohit.ascii_letters + rohit.digits, k=10))
                    await db.update_verify_status(user_id, verify_token=token, link=f"mbatch_{batch_id}")
                    link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{client.username}?start=verify_{token}')
                    
                    btn = [
                        [InlineKeyboardButton("• 𝚅𝙴𝚁𝙸𝙵𝚈 •", url=link), InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
                        [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="premium", style=enums.ButtonStyle.PRIMARY)]
                    ]
                    await query.answer("⚠️ Token verification required!", show_alert=True)
                    return await query.message.reply(
                        f"<b>𝗬𝗼𝘂𝗿 𝘁𝗼𝗸𝗲𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. Please refresh your token to continue..</b>\n\n<b>Token Timeout:</b> {get_exp_time(VERIFY_EXPIRE)}",
                        reply_markup=InlineKeyboardMarkup(btn),
                        protect_content=True
                    )

            mb_col = get_mb_collection()
            batch_data = await mb_col.find_one({"batch_id": batch_id})
            if not batch_data or index >= len(batch_data.get("ranges", [])):
                return await query.answer("❌ Episode range unavailable!", show_alert=True)

            target_range = batch_data["ranges"][index]
            await query.answer(f"Sending {target_range['title']}...", show_alert=False)

            start_id = target_range["start_id"]
            end_id = target_range["end_id"]
            db_channel_id = get_db_channel_id(client)

            cancel_tasks[user_id] = False
            wait_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁🛠️", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)],
                [InlineKeyboardButton("🌀 𝙲𝙰𝙽𝙲𝙴𝙻 🌀", callback_data=f"cancel_delivery_{user_id}", style=enums.ButtonStyle.DANGER)]
            ])
            status_msg = await client.send_message(user_id, "<b>🔺 ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>", reply_markup=wait_markup)

            copied_msgs = []
            for m_id in range(start_id, end_id + 1):
                if cancel_tasks.get(user_id, False):
                    break
                try:
                    await client.send_chat_action(chat_id=user_id, action=ChatAction.UPLOAD_DOCUMENT)
                    msg = await client.copy_message(chat_id=user_id, from_chat_id=db_channel_id, message_id=m_id, protect_content=PROTECT_CONTENT)
                    if msg: copied_msgs.append(msg)
                    await asyncio.sleep(0.6)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    if cancel_tasks.get(user_id, False): break
                    msg = await client.copy_message(chat_id=user_id, from_chat_id=db_channel_id, message_id=m_id, protect_content=PROTECT_CONTENT)
                    if msg: copied_msgs.append(msg)
                except Exception as e:
                    logger.error(f"Failed to copy msg {m_id}: {e}")

            was_cancelled = cancel_tasks.pop(user_id, False)
            try: await status_msg.delete()
            except Exception: pass

            if was_cancelled:
                return await client.send_message(user_id, "❌ <b>Delivery cancelled successfully!</b>")

            FILE_AUTO_DELETE = await db.get_del_timer()
            if FILE_AUTO_DELETE > 0 and copied_msgs:
                notification_msg = await client.send_message(user_id, f"<b>This file will be deleted in {get_exp_time(FILE_AUTO_DELETE)}. Please save or forward it!</b>")
                await asyncio.sleep(FILE_AUTO_DELETE)
                for s_msg in copied_msgs:
                    try: await s_msg.delete()
                    except Exception: pass
                try: await notification_msg.edit("<b>Your video/file is successfully deleted!</b>")
                except Exception: pass
            return

        # 🟡 B) ADMIN: ADD NEW RANGE
        elif data.startswith("add_mrange_"):
            await query.answer()
            batch_id = data.replace("add_mrange_", "")

            title_msg = await client.ask(chat_id=user_id, text="📝 **Enter Button Name/Title:**\n\n(e.g. `Ep 1 to 100`)", timeout=60)
            if not title_msg or not title_msg.text:
                return await query.message.reply("❌ Invalid title!")
            btn_title = title_msg.text.strip()

            f_msg = await client.ask(chat_id=user_id, text=f" Forward First Message for **'{btn_title}'** from DB Channel or send link:", timeout=60)
            f_chat_id, f_msg_id = await get_chat_and_msg_id(client, f_msg)

            s_msg = await client.ask(chat_id=user_id, text=f" Forward Last Message for **'{btn_title}'** from DB Channel or send link:", timeout=60)
            s_chat_id, s_msg_id = await get_chat_and_msg_id(client, s_msg)

            if not f_chat_id or not s_chat_id or f_chat_id != s_chat_id:
                return await query.message.reply("❌ Invalid links/messages or different channels!")

            db_channel_id = get_db_channel_id(client)
            status = await query.message.reply("⏳ Storing episodes in DB channel...")
            copied_start, copied_end = None, None

            if f_chat_id == db_channel_id:
                copied_start, copied_end = f_msg_id, s_msg_id
            else:
                for m_id in range(f_msg_id, s_msg_id + 1):
                    try:
                        m = await client.get_messages(f_chat_id, m_id)
                        if m and not m.empty:
                            cp = await m.copy(db_channel_id, disable_notification=True)
                            if copied_start is None: copied_start = cp.id
                            copied_end = cp.id
                            await asyncio.sleep(0.3)
                    except Exception as e:
                        logger.error(f"Copy Error: {e}")
                await status.delete()

            new_range = {"title": btn_title, "start_id": copied_start, "end_id": copied_end}
            mb_col = get_mb_collection()
            await mb_col.update_one({"batch_id": batch_id}, {"$push": {"ranges": new_range}})
            return await show_admin_batch_menu(client, user_id, batch_id)

        # 🔵 C) ADMIN: GET MASTER SHARE LINK
        elif data.startswith("get_mlink_"):
            await query.answer()
            batch_id = data.replace("get_mlink_", "")
            bot_username = client.me.username if getattr(client, "me", None) else (await client.get_me()).username
            link = f"https://t.me/{bot_username}?start=mbatch_{batch_id}"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
            return await query.message.reply_text(f"✨ **Here is your Master Episode Link:**\n\n{link}", reply_markup=reply_markup)

        # 🔴 D) ADMIN: DELETE RANGE (Safe Split Fix)
        elif data.startswith("del_mrange_"):
            await query.answer()
            raw = data.replace("del_mrange_", "")
            batch_id, index_str = raw.rsplit("_", 1)  # Fixes crash when batch_id contains '_'
            index = int(index_str)

            mb_col = get_mb_collection()
            batch_data = await mb_col.find_one({"batch_id": batch_id})
            ranges = batch_data.get("ranges", []) if batch_data else []
            if 0 <= index < len(ranges):
                ranges.pop(index)
                await mb_col.update_one({"batch_id": batch_id}, {"$set": {"ranges": ranges}})
            return await show_admin_batch_menu(client, user_id, batch_id, message_to_edit=query.message)

    except Exception as e:
        logger.error(f"❌ Callback Error: {e}\n{traceback.format_exc()}")
        try: await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)
        except Exception: pass


# ==============================================================================
# 🌀 4. CANCEL DELIVERY HANDLER
# ==============================================================================

@Bot.on_callback_query(filters.regex(r"^cancel_delivery_"))
async def cancel_delivery_callback(client: Client, query: CallbackQuery):
    try:
        target_user_id = int(query.data.split("_")[2])
    except Exception:
        return await query.answer("⚠️ Invalid Callback Data!", show_alert=True)
    
    if query.from_user.id != target_user_id:
        return await query.answer("⚠️ This cancel button is not for you!", show_alert=True)

    cancel_tasks[target_user_id] = True
    await query.answer("❌ Stopping delivery...", show_alert=False)
    try: await query.message.delete()
    except Exception: pass


# ==============================================================================
# 👑 5. PREMIUM COMMAND HANDLERS
# ==============================================================================

@Bot.on_message(filters.command("myplan") & filters.private)
async def myplan(client: Client, message: Message):
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    
    if await is_premium_user(user_id):
        expiration_time = user.get("premium_expiration")
        status = f"<b>Pʀᴇᴍɪᴜᴍ Uꜱᴇʀ</b>\n<b>Exᴘɪʀᴀᴛɪᴏɴ Tɪᴍᴇ:</b> {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        status = "<b>Fʀᴇᴇ Uꜱᴇʀ</b>\n<b>Exᴘɪʀᴀᴛɪᴏɴ Tɪᴍᴇ:</b> N/A"
    
    await message.reply_text(f"<b><u>Yᴏᴜʀ Pʟᴀɴ Dᴇᴛᴀɪʟꜱ</u></b>\n\n<b>Uꜱᴇʀ ID:</b> <code>{user_id}</code>\n<b>Sᴛᴀᴛᴜꜱ:</b> {status}")


@Bot.on_message(filters.command("addpremium") & filters.private & admin)
async def add_premium(client: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("<b>Uꜱᴀɢᴇ:</b> /addpremium <user_id> <time_limit_in_days>")
    
    try:
        user_id = int(message.command[1])
        days = int(message.command[2])
    except ValueError:
        return await message.reply_text("<b>Iɴᴠᴀʟɪᴅ Uꜱᴇʀ ID ᴏʀ Tɪᴍᴇ Lɪᴍɪᴛ.</b>")
    
    expiration_time = datetime.now() + timedelta(days=days)
    await add_premium_user(user_id, expiration_time)
    await message.reply_text(f"<b>Pʀᴇᴍɪᴜᴍ ᴀᴅᴅᴇᴅ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ғᴏʀ {days} ᴅᴀʏꜱ ᴛᴏ ᴜꜱᴇʀ {user_id}.</b>")


@Bot.on_message(filters.command("remove_premium") & filters.private & admin)
async def remove_premium(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("<b>Uꜱᴀɢᴇ:</b> /remove_premium <user_id>")
    
    try:
        user_id = int(message.command[1])
    except ValueError:
        return await message.reply_text("<b>Iɴᴠᴀʟɪᴅ Uꜱᴇʀ ID.</b>")
    
    await remove_premium_user(user_id)
    await message.reply_text(f"<b>Pʀᴇᴍɪᴜᴍ ʀᴇᴍᴏᴠᴇᴅ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ғʀᴏᴍ ᴜꜱᴇʀ {user_id}.</b>")


@Bot.on_message(filters.command("premium_users") & filters.private & admin)
async def premium_users(client: Client, message: Message):
    users = await get_all_premium_users()
    if not users:
        return await message.reply_text("<b>Nᴏ Pʀᴇᴍɪᴜᴍ Uꜱᴇʀꜱ Fᴏᴜɴᴅ.</b>")
    
    text = "<b><u>Pʀᴇᴍɪᴜᴍ Uꜱᴇʀꜱ Lɪꜱᴛ</u></b>\n\n"
    for user in users:
        text += f"<b>Uꜱᴇʀ ID:</b> <code>{user['_id']}</code> | <b>Exᴘɪʀᴇꜱ:</b> {user['premium_expiration'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    await message.reply_text(text)
