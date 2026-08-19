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
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MessageNotModified
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, MessageDeleteForbidden
from bot import Bot
from config import *
from helper_func import *
from database.database import *
from database.db_premium import *
from pytz import timezone

logger = logging.getLogger(__name__)

# ==================== GLOBAL QUOTE=FALSE PATCH ====================
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
# ==================================================================

BAN_SUPPORT = f"{BAN_SUPPORT}"
TUT_VID = f"{TUT_VID}"

# Global dict for active cancellation tracking
cancel_tasks = {}

# DB Channel ID Safe Fetcher Helper
def get_db_channel_id(client: Client):
    if hasattr(client, "db_channel") and client.db_channel:
        return getattr(client.db_channel, "id", client.db_channel)
    try:
        from config import DB_CHANNEL
        return DB_CHANNEL
    except Exception:
        return None

# ==============================================================================
# MAIN /start COMMAND HANDLER
# ==============================================================================
@Bot.on_message(filters.command('start') & filters.private)
async def start_command(client: Client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except Exception:
        await message.react(emoji="⚡️", big=True)
        pass
    
    user_id = message.from_user.id
    id = message.from_user.id
    is_premium = await is_premium_user(id)
    
    # Add user if not already present
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except:
            pass

    # ✅ Check Force Subscription First (Subscribers Verification)
    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    # Check if user is banned
    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            "<b>⛔️ You are Bᴀɴɴᴇᴅ from using this bot.</b>\n\n"
            "<i>Contact support if you think this is a mistake.</i>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Contact Support", url=BAN_SUPPORT)]]
            )
        )

    # File auto-delete time in seconds
    FILE_AUTO_DELETE = await db.get_del_timer()
    text = message.text

    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        # 🔥 NEW: Multi-Batch Deep Link Support Check (`mbatch_`)
        if base64_string.startswith("mbatch_"):
            return await handle_multi_batch_start(client, message, base64_string)

        # Token verification status fetch
        verify_status = await db.get_verify_status(id)

        if SHORTLINK_URL or SHORTLINK_API:
            if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
                await db.update_verify_status(user_id, is_verified=False)
                verify_status['is_verified'] = False 

            if "verify_" in text:
                _, token = text.split("_", 1)
                if verify_status['verify_token'] != token:
                    return await message.reply("⚠️ 𝖨nv𝖺ʟɪᴅ 𝗍ᴏᴋᴇɴ. 𝖯ʟᴇᴀ𝗌ᴇ /start 𝖺𝗀αɪɴ.")

                await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

                await db.update_verify_status(id, is_verified=True, verified_time=time.time())
                current = await db.get_verify_count(id)
                await db.set_verify_count(id, current + 1)

                file_id = verify_status.get("link", "")
                if not file_id:
                    file_id = base64_string  

                btn = [[InlineKeyboardButton("🚀 Gᴇᴛ Fɪʟᴇ Nᴏᴡ", url=f"https://t.me/{client.username}?start={file_id}")]]
                
                return await message.reply(
                    f"✅ <b>𝗧𝗼𝗸𝗲𝗻 𝘃𝗲𝗿𝗶𝗳𝗶𝗲𝗱!</b>\n\nVαʟɪᴅ ғᴏʀ: {get_exp_time(VERIFY_EXPIRE)}\n\n"
                    "Cʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇ 👇",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=True
                )

            if not verify_status['is_verified'] and not is_premium:
                await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
                
                token = ''.join(random.choices(rohit.ascii_letters + rohit.digits, k=10))
                await db.update_verify_status(id, verify_token=token, link=base64_string)
                
                link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{client.username}?start=verify_{token}')
                btn = [
                    [InlineKeyboardButton("• 𝚅𝙴𝚁𝙸𝙵𝙸𝙴𝙳 •", url=link),
                     InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
                    [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="premium", style=enums.ButtonStyle.PRIMARY)]
                ]
                return await message.reply(
                    f"<b>𝗬𝗼𝘂𝗿 𝘁𝗼𝗸𝗲𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗿𝗲𝗳𝗿𝗲𝘀𝗵 ʏᴏ𝘂𝗿 𝘁ᴏ𝗸𝗲𝗻 𝘁ᴏ 𝗰𝗼𝗻𝘁𝗶𝗻𝘂𝗲..</b>\n\n<b>Tᴏᴋᴇɴ Tɪᴍᴇᴏᴜᴛ:</b> {get_exp_time(VERIFY_EXPIRE)}",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=True
                )

        # File decoding for Single / Batch Links
        string = await decode(base64_string)
        argument = string.split("-")

        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                return print(f"Error decoding IDs: {e}")
            
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            except Exception as e:
                print(f"Error decoding ID: {e}")
                return

        cancel_tasks[user_id] = False

        wait_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁🛠️", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)
            ],[
                InlineKeyboardButton("🌀 𝙲𝙰𝙽𝙲𝙴𝙻 🌀", callback_data=f"cancel_delivery_{user_id}", style=enums.ButtonStyle.DANGER)
            ]
        ])
        temp_msg = await message.reply("<b>🔺ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ</b>", reply_markup=wait_markup)
        
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("Something went wrong!")
            print(f"Error getting messages: {e}")
            try: await temp_msg.delete()
            except: pass
            return

        codeflix_msgs = []
        for msg in messages:
            await asyncio.sleep(0.05)

            if cancel_tasks.get(user_id, False) is True:
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
                if cancel_tasks.get(user_id, False) is True: 
                    break
                copied_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, 
                                            reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                codeflix_msgs.append(copied_msg)
            except Exception as e:
                print(f"Failed to send message: {e}")
                pass

            await asyncio.sleep(1)

        was_cancelled = cancel_tasks.pop(user_id, False)

        try:
            await temp_msg.delete()
        except:
            pass

        if was_cancelled:
            await message.reply_text("❌ **File delivery has been cancelled successfully.**")
            return

        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply(
                f"<b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇ Deleted ɪɴ  {get_exp_time(FILE_AUTO_DELETE)}. Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢES ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs DᴇʟᴇᴛᴇDeleted.</b>"
            )

            await asyncio.sleep(FILE_AUTO_DELETE)

            for snt_msg in codeflix_msgs:    
                if snt_msg:
                    try:    
                        await snt_msg.delete()  
                    except Exception as e:
                        print(f"Error deleting message {snt_msg.id}: {e}")

            try:
                reload_url = (
                    f"https://t.me/{client.username}?start={message.command[1]}"
                    if message.command and len(message.command) > 1
                    else None
                )
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ!", url=reload_url)]]
                ) if reload_url else None

                await notification_msg.edit(
                    "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱ|ꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇</b>",
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"Error updating notification with 'Get File Again' button: {e}")
    else:
        try:
            sticker_msg = await message.reply_sticker(sticker=START_STICKER)
            await asyncio.sleep(0.4)
            await sticker_msg.delete()
        except Exception as e:
            print(f"Sticker Loading Error: {e}")
            pass  
        
        await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        
        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟs •", callback_data='channels' , style=enums.ButtonStyle.PRIMARY)],
                [
                    InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data = "about"),
                    InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data = "help")
                ]
            ]
        )
        await message.reply_photo(
            photo=START_PIC,
            caption=START_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=reply_markup,
            effect_id=int(random.choice(EFFECT_IDS))) 

        return


# ==============================================================================
# 🔥 MULTI-BATCH START HANDLER (Shows Episode Buttons)
# ==============================================================================
async def handle_multi_batch_start(client: Client, message: Message, payload: str):
    try:
        batch_id = payload.replace("mbatch_", "").strip().lower()
        batch_data = await db.get_multi_batch(batch_id)

        if not batch_data or not batch_data.get("ranges"):
            await message.reply_text("❌ **No episodes found in this batch!**")
            return

        ranges = batch_data.get("ranges", [])
        buttons = []
        for index, item in enumerate(ranges):
            buttons.append([
                InlineKeyboardButton(f"📺 {item['title']}", callback_data=f"user_mget_{batch_id}_{index}")
            ])

        markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            f"🎬 **Multi-Batch Episodes:** `{batch_id}`\n\nNiche दिए गए बटन पर क्लिक करके एपिसोड प्राप्त करें:",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"❌ [START MBATCH ERROR] {e}\n{traceback.format_exc()}")
        await message.reply_text(f"❌ **Start Error:** `{e}`")


# ==============================================================================
# 🔥 FULLY LOADED USER EPISODE DELIVERY CALLBACK HANDLER (With Verify, Wait, Cancel & Auto-Delete)
# ==============================================================================
@Bot.on_callback_query(filters.regex(r"^user_mget_"), group=-1)
async def user_mget_callback(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id
    
    logger.info(f"🟢 [CALLBACK HIT SUCCESS] Data: {data} | User: {user_id}")

    try:
        # 1. Check Force Subscribe before sending files
        if not await is_subscribed(client, user_id):
            await query.answer("❌ Please join our update channels first!", show_alert=True)
            return await not_joined(client, query.message)

        parts = data.split("_")
        if len(parts) < 4:
            await query.answer("❌ Invalid Callback Data Structure!", show_alert=True)
            return

        batch_id = parts[2]
        index = int(parts[3])

        is_premium = await is_premium_user(user_id)
        verify_status = await db.get_verify_status(user_id)

        # 2. Token Verification Check
        if SHORTLINK_URL or SHORTLINK_API and not is_premium:
            if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
                await db.update_verify_status(user_id, is_verified=False)
                verify_status['is_verified'] = False 

            if not verify_status['is_verified']:
                token = ''.join(random.choices(rohit.ascii_letters + rohit.digits, k=10))
                await db.update_verify_status(user_id, verify_token=token, link=f"mbatch_{batch_id}")
                
                link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{client.username}?start=verify_{token}')
                btn = [
                    [InlineKeyboardButton("• 𝚅𝙴𝚁𝙸𝙵𝙸𝙴𝙳 •", url=link),
                     InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
                    [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍ𝙸𝚄𝙼 •", callback_data="premium", style=enums.ButtonStyle.PRIMARY)]
                ]
                await query.message.reply(
                    f"<b>𝗬𝗼𝘂𝗿 𝘁𝗼𝗸𝗲𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗿𝗲𝗳𝗿𝗲𝘀𝗵 ʏᴏᴜʀ 𝘁ᴏ𝗸𝗲𝗻 𝘁ᴏ 𝗰𝗼𝗻𝘁𝗶𝗻𝘂𝗲..</b>\n\n<b>Tᴏᴋᴇɴ Tɪᴍᴇᴏᴜᴛ:</b> {get_exp_time(VERIFY_EXPIRE)}",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=True
                )
                await query.answer("⚠️ Token expired! Please verify first.", show_alert=True)
                return

        batch_data = await db.get_multi_batch(batch_id)

        if not batch_data or "ranges" not in batch_data or index >= len(batch_data["ranges"]):
            await query.answer("❌ Invalid batch or episode range!", show_alert=True)
            return

        target_range = batch_data["ranges"][index]
        db_channel_id = get_db_channel_id(client)

        start_id = target_range["start_id"]
        end_id = target_range["end_id"]
        ids = range(start_id, end_id + 1) if start_id <= end_id else list(range(start_id, end_id - 1, -1))

        cancel_tasks[user_id] = False

        # 3. Please Wait Message & Cancel Button Markup
        wait_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁🛠️", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)
            ],[
                InlineKeyboardButton("🌀 𝙲𝙰𝙽𝙲𝙴𝙻 🌀", callback_data=f"cancel_delivery_{user_id}", style=enums.ButtonStyle.DANGER)
            ]
        ])
        
        temp_msg = await query.message.reply("<b>🔺ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ</b>", reply_markup=wait_markup)
        await query.answer(f"🚀 Sending {target_range['title']}...", show_alert=False)
        logger.info(f"📤 [SENDING EPISODES] To User {user_id} | Range IDs: {start_id} to {end_id}")

        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await query.message.reply_text("Something went wrong!")
            logger.error(f"Error getting messages in multi-batch: {e}")
            try: await temp_msg.delete()
            except: pass
            return

        codeflix_msgs = []
        for msg in messages:
            await asyncio.sleep(0.05)

            if cancel_tasks.get(user_id, False) is True:
                break

            if msg.service or (not msg.text and not msg.media):
                continue  

            await client.send_chat_action(chat_id=user_id, action=ChatAction.UPLOAD_DOCUMENT)

            caption = (CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, 
                                             filename=msg.document.file_name) if bool(CUSTOM_CAPTION) and bool(msg.document)
                       else ("" if not msg.caption else msg.caption.html))

            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                copied_msg = await msg.copy(chat_id=user_id, caption=caption, parse_mode=ParseMode.HTML, 
                                            reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                codeflix_msgs.append(copied_msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                if cancel_tasks.get(user_id, False) is True: 
                    break
                copied_msg = await msg.copy(chat_id=user_id, caption=caption, parse_mode=ParseMode.HTML, 
                                            reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                codeflix_msgs.append(copied_msg)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                pass

            await asyncio.sleep(1)

        was_cancelled = cancel_tasks.pop(user_id, False)

        try:
            await temp_msg.delete()
        except:
            pass

        if was_cancelled:
            await query.message.reply_text("❌ **File delivery has been cancelled successfully.**")
            return

        # 4. Auto Delete Timer & Reload Button Support
        FILE_AUTO_DELETE = await db.get_del_timer()
        if FILE_AUTO_DELETE > 0:
            notification_msg = await query.message.reply(
                f"<b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ {get_exp_time(FILE_AUTO_DELETE)}. Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs Dᴇʟᴇᴛᴇᴅ.</b>"
            )

            await asyncio.sleep(FILE_AUTO_DELETE)

            for snt_msg in codeflix_msgs:    
                if snt_msg:
                    try:    
                        await snt_msg.delete()  
                    except Exception as e:
                        logger.error(f"Error deleting message {snt_msg.id}: {e}")

            try:
                reload_url = f"https://t.me/{client.username}?start=mbatch_{batch_id}"
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("ɢᴇᴛ ғɪʟᴇ ᴀɢᴀɪɴ!", url=reload_url)]]
                )

                await notification_msg.edit(
                    "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇</b>",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error updating notification with 'Get File Again' button: {e}")

    except Exception as e:
        full_traceback = traceback.format_exc()
        logger.error(f"💥 [USER DELIVERY ERROR] Data: '{data}' | User: {user_id}\nError: {e}\n{full_traceback}")
        try:
            await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)
        except Exception:
            pass


# ==============================================================================
# CALLBACK QUEUE FOR CANCEL DELIVERY
# ==============================================================================
@Bot.on_callback_query(filters.regex(r"^cancel_delivery_"), group=-1)
async def cancel_delivery_callback(client: Client, callback_query: CallbackQuery):
    try:
        target_user_id = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        try: await callback_query.answer("⚠️ Invalid Callback Data!", show_alert=True)
        except: pass
        return
    
    if callback_query.from_user.id != target_user_id:
        try: await callback_query.answer("⚠️ Yeh cancel button aapke liye nahi hai!", show_alert=True)
        except: pass
        return

    if cancel_tasks.get(target_user_id, False) is True:
        try: await callback_query.answer("⏳ Processing cancellation, please wait...", show_alert=False)
        except: pass
        return

    cancel_tasks[target_user_id] = True
    
    try:
        await callback_query.answer("❌ Stopping delivery queue...", show_alert=False)
    except:
        pass
    
    try:
        await callback_query.message.delete()
    except (MessageDeleteForbidden, Exception):
        pass


# ==============================================================================
# FORCE SUBSCRIBE NOT JOINED HANDLER
# ==============================================================================
chat_data_cache = {}

async def not_joined(client: Client, message: Message):
    temp = await message.reply("<b><i>Checking Subscription...</i></b>")
    user_id = message.from_user.id
    buttons = []
    count = 0

    try:
        all_channels = await db.show_channels()  
        for total, chat_id in enumerate(all_channels, start=1):
            mode = await db.get_channel_mode(chat_id)  

            await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

            if not await is_sub(client, user_id, chat_id):
                try:
                    if chat_id in chat_data_cache:
                        data = chat_data_cache[chat_id]
                    else:
                        data = await client.get_chat(chat_id)
                        chat_data_cache[chat_id] = data

                    name = data.title

                    if mode == "on" and not data.username:
                        invite = await client.create_chat_invite_link(
                            chat_id=chat_id,
                            creates_join_request=True,
                            expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None
                        )
                        link = invite.invite_link
                    else:
                        if data.username:
                            link = f"https://t.me/{data.username}"
                        else:
                            invite = await client.create_chat_invite_link(
                                chat_id=chat_id,
                                expire_date=datetime.utcnow() + timedelta(seconds=FSUB_LINK_EXPIRY) if FSUB_LINK_EXPIRY else None)
                            link = invite.invite_link

                    buttons.append([InlineKeyboardButton(text=name, url=link)])
                    count += 1
                    await temp.edit(f"<b>{'! ' * count}</b>")

                except Exception as e:
                    print(f"Error with chat {chat_id}: {e}")
                    try: return await temp.edit(f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ @rohit_1888</i></b>")
                    except: return

        try:
            buttons.append([
                InlineKeyboardButton(
                    text='♻️ Tʀʏ Aɢᴀɪɴ',
                    url=f"https://t.me/{client.username}?start={message.command[1]}"
                )
            ])
        except IndexError:
            pass

        await message.reply_photo(
            photo=FORCE_PIC,
            caption=FORCE_MSG.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name,
                username=None if not message.from_user.username else '@' + message.from_user.username,
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        print(f"Final Error: {e}")
        try: await temp.edit(f"<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ...</i></b>")
        except: pass


# ==============================================================================
# PREMIUM AND COMMAND HANDLERS
# ==============================================================================
@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id  
    status_message = await check_user_plan(user_id)
    await message.reply(status_message)


@Bot.on_message(filters.command('addpremium') & filters.private & admin)
async def add_premium_user_command(client, msg):
    if len(msg.command) != 4:
        await msg.reply_text(
            "Usage: /addpremium <user_id> <time_value> <time_unit>\n\n"
            "Time Units:\n"
            "s - seconds\n"
            "m - minutes\n"
            "h - hours\n"
            "d - days\n"
            "y - years\n\n"
            "Examples:\n"
            "/addpremium 123456789 30 m → 30 minutes\n"
            "/addpremium 123456789 2 h → 2 hours\n"
            "/addpremium 123456789 1 d → 1 day\n"
            "/addpremium 123456789 1 y → 1 year"
        )
        return

    try:
        user_id = int(msg.command[1])
        time_value = int(msg.command[2])
        time_unit = msg.command[3].lower()  

        expiration_time = await add_premium(user_id, time_value, time_unit)

        await msg.reply_text(
            f"✅ User `{user_id}` added as a premium user for {time_value} {time_unit}.\n"
            f"Expiration Time: `{expiration_time}`"
        )

        await client.send_message(
            chat_id=user_id,
            text=(
                f"🎉 Premium Activated!\n\n"
                f"You have received premium access for `{time_value} {time_unit}`.\n"
                f"Expires on: `{expiration_time}`"
            ),
        )

    except ValueError:
        await msg.reply_text("❌ Invalid input. Please ensure user ID and time value are numbers.")
    except Exception as e:
        await msg.reply_text(f"⚠️ An error occurred: `{str(e)}`")


@Bot.on_message(filters.command('remove_premium') & filters.private & admin)
async def pre_remove_user(client: Client, msg: Message):
    if len(msg.command) != 2:
        await msg.reply_text("useage: /remove_premium user_id ")
        return
    try:
        user_id = int(msg.command[1])
        await remove_premium(user_id)
        await msg.reply_text(f"User {user_id} has been removed.")
    except ValueError:
        await msg.reply_text("user_id must be an integer or not available in database.")


@Bot.on_message(filters.command('premium_users') & filters.private & admin)
async def list_premium_users_command(client, message):
    ist = timezone("Asia/Kolkata")
    premium_users_cursor = collection.find({})
    premium_user_list = ['Active Premium Users in database:']
    current_time = datetime.now(ist)  

    async for user in premium_users_cursor:
        user_id = user["user_id"]
        expiration_timestamp = user["expiration_timestamp"]

        try:
            expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
            remaining_time = expiration_time - current_time

            if remaining_time.total_seconds() <= 0:
                await collection.delete_one({"user_id": user_id})
                continue  

            user_info = await client.get_users(user_id)
            username = user_info.username if user_info.username else "No Username"
            first_name = user_info.first_name
            mention=user_info.mention

            days, hours, minutes, seconds = (
                remaining_time.days,
                remaining_time.seconds // 3600,
                (remaining_time.seconds // 60) % 60,
                remaining_time.seconds % 60,
            )
            expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"

            premium_user_list.append(
                f"UserID: <code>{user_id}</code>\n"
                f"User: @{username}\n"
                f"Name: {mention}\n"
                f"Expiry: {expiry_info}"
            )
        except Exception as e:
            premium_user_list.append(
                f"UserID: <code>{user_id}</code>\n"
                f"Error: Unable to fetch user details ({str(e)})"
            )

    if len(premium_user_list) == 1:  
        await message.reply_text("I found 0 active premium users in my DB")
    else:
        await message.reply_text("\n\n".join(premium_user_list), parse_mode=None)


@Bot.on_message(filters.command("count") & filters.private & admin)
async def total_verify_count_cmd(client, message: Message):
    total = await db.get_total_verify_count()
    await message.reply_text(f"Tᴏᴛᴀʟ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴋᴇɴs ᴛᴏᴅᴀʏ: <b>{total}</b>")


@Bot.on_message(filters.command('commands') & filters.private & admin)
async def bcmd(bot: Bot, message: Message):        
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data = "close")]])
    await message.reply(text=CMD_TXT, reply_markup = reply_markup, quote=True)
