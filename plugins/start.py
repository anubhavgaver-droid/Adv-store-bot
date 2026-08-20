import asyncio
import os
import random
import sys
import re
import string 
import time
import logging
import traceback
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__, enums
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
)
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MessageNotModified
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, MessageDeleteForbidden
from bot import Bot
from config import *
from helper_func import *
from database.database import *
from database.db_premium import *
from pytz import timezone
from plugins.adminz import send_main_settings_panel


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
        try:
            await message.react(emoji="⚡️", big=True)
        except Exception:
            pass
    
    user_id = message.from_user.id
    is_premium = await is_premium_user(user_id)
    
    # Add user if not already present
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except Exception:
            pass

    # ✅ Check Force Subscription First
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

    FILE_AUTO_DELETE = await db.get_del_timer()
    text = message.text

    # Dynamic Bot Settings Fetching from Database
    bot_settings = await db.get_bot_settings()
    protect_content_val = bot_settings.get('protect_content', PROTECT_CONTENT)
    custom_caption_val = bot_settings.get('custom_caption', CUSTOM_CAPTION)

    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        # 🔥 MULTI-BATCH DEEP LINK HANDLER
        if base64_string.startswith("mbatch_") or base64_string.startswith("batch_"):
            return await handle_multi_batch_start(client, message, base64_string)

        # ----------------------------------------------------------------------
        # DYNAMIC VERIFICATION ENGINE (Database Driven Settings)
        # ----------------------------------------------------------------------
        verify_status = await db.get_verify_status(user_id)

        verify_mode = bot_settings.get('verify_mode', True)
        shortlink_url = bot_settings.get('shortlink_url', SHORTLINK_URL)
        shortlink_api = bot_settings.get('shortlink_api', SHORTLINK_API)
        tut_vid = bot_settings.get('tut_vid', TUT_VID)
        verify_expire = bot_settings.get('verify_expire', VERIFY_EXPIRE)

        # Verification system trigger check
        if verify_mode and shortlink_url and shortlink_api:
            if verify_status['is_verified'] and verify_expire < (time.time() - verify_status['verified_time']):
                await db.update_verify_status(user_id, is_verified=False)
                verify_status['is_verified'] = False 

            if "verify_" in text:
                _, token = text.split("_", 1)
                if verify_status['verify_token'] != token:
                    return await message.reply("⚠️ 𝖨nv𝖺ʟɪᴅ 𝗍ᴏᴋᴇɴ. 𝖯ʟᴇᴀ𝗌ᴇ /start 𝖺𝗀αɪɴ.")

                await db.update_verify_status(user_id, is_verified=True, verified_time=time.time())
                current = await db.get_verify_count(user_id)
                await db.set_verify_count(user_id, current + 1)

                file_id = verify_status.get("link", "")
                if not file_id:
                    file_id = base64_string  

                btn = [[InlineKeyboardButton("🚀 Gᴇᴛ Fɪʟᴇ Nᴏᴡ", url=f"https://t.me/{client.username}?start={file_id}")]]
                
                return await message.reply(
                    f"✅ <b>𝗧𝗼𝗸𝗲𝗻 𝘃𝗲𝗿𝗶𝗳𝗶𝗲𝗱!</b>\n\nVαʟɪᴅ ғᴏʀ: {get_exp_time(verify_expire)}\n\n"
                    "Cʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ғɪʟᴇ 👇",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=protect_content_val
                )

            if not verify_status['is_verified'] and not is_premium:
                token = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                await db.update_verify_status(user_id, verify_token=token, link=base64_string)
                
                # Fast Direct Link Generation
                link = await get_shortlink(shortlink_url, shortlink_api, f'https://t.me/{client.username}?start=verify_{token}')
                btn = [
                    [InlineKeyboardButton("• 𝚅𝙴𝚁𝙸𝙵𝙸𝙴𝙳 •", url=link),
                     InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=tut_vid)],
                    [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •", callback_data="premium", style=enums.ButtonStyle.PRIMARY)]
                ]
                return await message.reply(
                    f"<b>𝗬𝗼𝘂𝗿 𝘁𝗼𝗸𝗲𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗿𝗲𝗳𝗿𝗲𝘀𝗵 ʏᴏ𝘂𝗿 𝘁𝗼𝗸𝗲𝗻 𝘁𝗼 𝗰𝗼𝗻𝘁𝗶𝗻𝘂𝗲..</b>\n\n<b>Tᴏᴋᴇɴ Tɪᴍᴇᴏᴜᴛ:</b> {get_exp_time(verify_expire)}",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=protect_content_val
                )

        # Standard Base64 Batch / Single File Hash Processing
        try:
            decoded_str = await decode(base64_string)
            argument = decoded_str.split("-")
        except Exception as e:
            logger.error(f"Error decoding string {base64_string}: {e}")
            return await message.reply_text("⚠️ **Invalid Link or File Hash!**")

        db_channel_id = abs(get_db_channel_id(client))
        ids = []
        if len(argument) == 3:
            try:
                start = int(int(argument[1]) / db_channel_id)
                end = int(int(argument[2]) / db_channel_id)
                ids = range(start, end + 1) if start <= end else list(range(start, end - 1, -1))
            except Exception as e:
                logger.error(f"Error decoding IDs: {e}")
                return
            
        elif len(argument) == 2:
            try:
                ids = [int(int(argument[1]) / db_channel_id)]
            except Exception as e:
                logger.error(f"Error decoding ID: {e}")
                return

        cancel_tasks[user_id] = False

        wait_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁🛠️", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("🌀 𝙲𝙰𝙽𝙲𝙴𝙻 🌀", callback_data=f"cancel_delivery_{user_id}", style=enums.ButtonStyle.DANGER)]
        ])
        temp_msg = await message.reply("<b>🔺ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ</b>", reply_markup=wait_markup)
        
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("Something went wrong!")
            try: await temp_msg.delete()
            except Exception: pass
            return

        codeflix_msgs = []
        for msg in messages:
            await asyncio.sleep(0.05)

            if cancel_tasks.get(user_id, False) is True:
                break

            if msg.service or (not msg.text and not msg.media):
                continue  

            await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.UPLOAD_DOCUMENT)

            # Dynamic Custom Caption Application
            if bool(custom_caption_val):
                prev_cap = "" if not msg.caption else msg.caption.html
                f_name = msg.document.file_name if msg.document and hasattr(msg.document, 'file_name') else ""
                caption = custom_caption_val.format(previouscaption=prev_cap, filename=f_name)
            else:
                caption = "" if not msg.caption else msg.caption.html

            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id, 
                    caption=caption, 
                    parse_mode=ParseMode.HTML, 
                    reply_markup=reply_markup, 
                    protect_content=protect_content_val
                )
                codeflix_msgs.append(copied_msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                if cancel_tasks.get(user_id, False) is True: 
                    break
                copied_msg = await msg.copy(
                    chat_id=message.from_user.id, 
                    caption=caption, 
                    parse_mode=ParseMode.HTML, 
                    reply_markup=reply_markup, 
                    protect_content=protect_content_val
                )
                codeflix_msgs.append(copied_msg)
            except Exception:
                pass

            await asyncio.sleep(1)

        was_cancelled = cancel_tasks.pop(user_id, False)

        try:
            await temp_msg.delete()
        except Exception:
            pass

        if was_cancelled:
            await message.reply_text("❌ **File delivery has been cancelled successfully.**")
            return

        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply(
                f"<b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ {get_exp_time(FILE_AUTO_DELETE)}. Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs ʙᴇғᴏʀᴇ ɪᴛ ɢᴇᴛs Dᴇʟᴇᴛᴇᴅ.</b>"
            )

            await asyncio.sleep(FILE_AUTO_DELETE)

            for snt_msg in codeflix_msgs:    
                if snt_msg:
                    try:    
                        await snt_msg.delete()  
                    except Exception:
                        pass

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
                    "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇</b>",
                    reply_markup=keyboard
                )
            except Exception:
                pass
    else:
        try:
            sticker_msg = await message.reply_sticker(sticker=START_STICKER)
            await asyncio.sleep(0.4)
            await sticker_msg.delete()
        except Exception:
            pass  
        
        # 🟢 DYNAMIC START MESSAGE, START PIC & SPOILER (BLUR) FROM DB
        dyn_start_msg = bot_settings.get('start_msg') or START_MSG
        dyn_start_pic = bot_settings.get('start_pic') or START_PIC
        is_spoiler = bot_settings.get('start_pic_spoiler', False)

        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟs •", callback_data='channels', style=enums.ButtonStyle.PRIMARY)],
                [
                    InlineKeyboardButton("• ᴀʙᴏᴜᴛ", callback_data="about"),
                    InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data="help")
                ],
                [
                    InlineKeyboardButton("⚙️ SETTINGS", callback_data="cb_settings")
                ]
            ]
        )
        
        try:
            formatted_caption = dyn_start_msg.format(
                first=message.from_user.first_name,
                last=message.from_user.last_name if message.from_user.last_name else "",
                username=f"@{message.from_user.username}" if message.from_user.username else "",
                mention=message.from_user.mention,
                id=message.from_user.id
            )
        except Exception:
            formatted_caption = dyn_start_msg

        # If Photo exists, send Photo else fallback to Text
        if dyn_start_pic:
            try:
                await message.reply_photo(
                    photo=dyn_start_pic,
                    caption=formatted_caption,
                    has_spoiler=is_spoiler,
                    reply_markup=reply_markup,
                    effect_id=int(random.choice(EFFECT_IDS))
                )
            except Exception:
                try:
                    await message.reply_photo(
                        photo=dyn_start_pic,
                        caption=formatted_caption,
                        reply_markup=reply_markup
                    )
                except Exception:
                    await message.reply_text(
                        text=formatted_caption,
                        reply_markup=reply_markup,
                        disable_web_page_preview=True
                    )
        else:
            await message.reply_text(
                text=formatted_caption,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        return


# ==============================================================================
# ⚙️ SETTINGS BUTTON CALLBACK HANDLER (ADMIN ONLY)
# ==============================================================================
@Bot.on_callback_query(filters.regex("^cb_settings$"))
async def cb_settings_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in ADMINS:
        return await query.answer("⚠️ This is only for Admin ⚠️", show_alert=True)
    
    await query.answer()
    await send_main_settings_panel(query)


# ==============================================================================
# MULTI-BATCH START HANDLER (URL Buttons + Auto Delete after 1 Min)
# ==============================================================================
async def handle_multi_batch_start(client: Client, message: Message, payload: str):
    try:
        batch_id = payload.replace("mbatch_", "").replace("batch_", "").strip().lower()
        batch_data = await db.get_multi_batch(batch_id)

        if not batch_data or not batch_data.get("ranges"):
            await message.reply_text("❌ **No episodes found in this batch!**")
            return

        ranges = batch_data.get("ranges", [])
        buttons = []
        db_channel_id = abs(get_db_channel_id(client))

        for item in ranges:
            if "base64_hash" in item and item["base64_hash"]:
                batch_hash = item["base64_hash"]
            else:
                start_id = item["start_id"]
                end_id = item["end_id"]
                raw_string = f"get-{start_id * db_channel_id}-{end_id * db_channel_id}"
                batch_hash = await encode(raw_string)

            batch_url = f"https://t.me/{client.username}?start={batch_hash}"

            buttons.append([
                InlineKeyboardButton(f"📺 {item['title']}", url=batch_url)
            ])

        markup = InlineKeyboardMarkup(buttons)
        
        mbatch_msg = await message.reply_text(
            f"🎬 **Multi-Batch Episodes:** `{batch_id.upper()}`\n\n"
            f"👇 **नीचे दिए गए बटन पर क्लिक करके एपिसोड प्राप्त करें:**\n\n"
            f"⏳ *यह बटन मैसेज 1 मिनट में अपने आप डिलीट हो जाएगा।*",
            reply_markup=markup
        )

        await asyncio.sleep(60)
        try:
            await mbatch_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"❌ [START MBATCH ERROR] {e}\n{traceback.format_exc()}")
        await message.reply_text(f"❌ **Start Error:** `{e}`")


# ==============================================================================
# CALLBACK QUEUE FOR CANCEL DELIVERY
# ==============================================================================
@Bot.on_callback_query(filters.regex(r"^cancel_delivery_"), group=-1)
async def cancel_delivery_callback(client: Client, callback_query: CallbackQuery):
    try:
        target_user_id = int(callback_query.data.split("_")[2])
    except (IndexError, ValueError):
        try: await callback_query.answer()
        except Exception: pass
        return
    
    if callback_query.from_user.id != target_user_id:
        try: await callback_query.answer()
        except Exception: pass
        return

    if cancel_tasks.get(target_user_id, False) is True:
        try: await callback_query.answer()
        except Exception: pass
        return

    cancel_tasks[target_user_id] = True
    
    try:
        await callback_query.answer()
    except Exception:
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
                    logger.error(f"Error with chat {chat_id}: {e}")
                    try: return await temp.edit("<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ @rohit_1888</i></b>")
                    except Exception: return

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
                last=message.from_user.last_name if message.from_user.last_name else "",
                username=f"@{message.from_user.username}" if message.from_user.username else "",
                mention=message.from_user.mention,
                id=message.from_user.id
            ),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    except Exception as e:
        logger.error(f"Final Error: {e}")
        try: await temp.edit("<b><i>! Eʀʀᴏʀ, Cᴏɴᴛᴀᴄᴛ ᴅᴇᴠᴇʟᴏᴘᴇʀ...</i></b>")
        except Exception: pass


# ==============================================================================
# PREMIUM AND COMMAND HANDLERS
# ==============================================================================
@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id  
    status_message = await check_user_plan(user_id)
    await message.reply(status_message)


@Bot.on_message(filters.command('addpremium') & filters.private & admin)
async def add_premium_user_command(client: Client, msg: Message):
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

        try:
            await client.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 Premium Activated!\n\n"
                    f"You have received premium access for `{time_value} {time_unit}`.\n"
                    f"Expires on: `{expiration_time}`"
                ),
            )
        except Exception:
            pass

    except ValueError:
        await msg.reply_text("❌ Invalid input. Please ensure user ID and time value are numbers.")
    except Exception as e:
        await msg.reply_text(f"⚠️ An error occurred: `{str(e)}`")


@Bot.on_message(filters.command('remove_premium') & filters.private & admin)
async def pre_remove_user(client: Client, msg: Message):
    if len(msg.command) != 2:
        await msg.reply_text("Usage: /remove_premium user_id")
        return
    try:
        user_id = int(msg.command[1])
        await remove_premium(user_id)
        await msg.reply_text(f"User {user_id} has been removed.")
    except ValueError:
        await msg.reply_text("user_id must be an integer or not available in database.")


@Bot.on_message(filters.command('premium_users') & filters.private & admin)
async def list_premium_users_command(client: Client, message: Message):
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
            mention = user_info.mention

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
async def total_verify_count_cmd(client: Client, message: Message):
    total = await db.get_total_verify_count()
    await message.reply_text(f"Tᴏᴛᴀʟ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴋᴇɴs ᴛᴏᴅᴀʏ: <b>{total}</b>")


@Bot.on_message(filters.command('commands') & filters.private & admin)
async def bcmd(bot: Bot, message: Message):        
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data="close")]])
    await message.reply(text=CMD_TXT, reply_markup=reply_markup, quote=True)
