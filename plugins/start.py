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
    CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges,
    WebAppInfo, LinkPreviewOptions
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

BAN_SUPPORT = f"{BAN_SUPPORT}"
cancel_tasks = {}

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
    
    if not await db.present_user(user_id):
        try:
            await db.add_user(user_id)
        except Exception:
            pass

    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    banned_users = await db.get_ban_users()
    if user_id in banned_users:
        return await message.reply_text(
            "<blockquote>⛔️ <b>Yᴏᴜ Aʀᴇ Bᴀɴɴᴇᴅ Fʀᴏᴍ Uꜱɪɴɢ Tʜɪs Bᴏᴛ.</b>\n\n"
            "<i>Cᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ ɪғ ʏᴏᴜ ᴛʜɪɴᴋ ᴛʜɪs ɪs ᴀ ᴍɪsᴛᴀᴋᴇ.</i></blockquote>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ Sᴜᴘᴘᴏʀᴛ", url=BAN_SUPPORT)]]
            ),
            quote=False
        )

    FILE_AUTO_DELETE = await db.get_del_timer()
    text = message.text

    bot_settings = await db.get_bot_settings()
    protect_content_val = bot_settings.get('protect_content', PROTECT_CONTENT)
    custom_caption_val = bot_settings.get('custom_caption', CUSTOM_CAPTION)

    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return

        if base64_string.startswith("mbatch_") or base64_string.startswith("batch_"):
            return await handle_multi_batch_start(client, message, base64_string)

        # ----------------------------------------------------------------------
        # DYNAMIC ANTI-BYPASS VERIFICATION ENGINE (MINI APP INTEGRATED)
        # ----------------------------------------------------------------------
        verify_status = await db.get_verify_status(user_id)

        verify_mode = bot_settings.get('verify_mode', True)
        shortlink_url = bot_settings.get('shortlink_url', SHORTLINK_URL)
        shortlink_api = bot_settings.get('shortlink_api', SHORTLINK_API)
        tut_vid = bot_settings.get('tut_vid', TUT_VID)
        verify_expire = bot_settings.get('verify_expire', VERIFY_EXPIRE)
        render_domain = bot_settings.get('render_domain', "https://anubhavvgani.onrender.com")

        bot_username = getattr(getattr(client, 'me', None), 'username', None) or "SmartfilestorebyAcbot"

        try:
            await db.settings_col.update_one(
                {"_id": "bot_settings"},
                {"$set": {
                    "shortlink_url": shortlink_url,
                    "shortlink_api": shortlink_api,
                    "bot_username": bot_username
                }},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error syncing settings to MongoDB for Express Proxy: {e}")

        if verify_mode and shortlink_url and shortlink_api:
            if verify_status['is_verified'] and verify_expire < (time.time() - verify_status['verified_time']):
                await db.update_verify_status(user_id, is_verified=False)
                verify_status['is_verified'] = False 

            if "verify_" in text:
                _, token = text.split("_", 1)

                await db.update_verify_status(user_id, is_verified=True, verified_time=time.time())
                current = await db.get_verify_count(user_id)
                await db.set_verify_count(user_id, current + 1)

                file_id = verify_status.get("link", "")
                if not file_id:
                    file_id = base64_string  

                btn = [[InlineKeyboardButton("🚀 Gᴇᴛ Fɪʟᴇ Nᴏᴡ", url=f"https://t.me/{bot_username}?start={file_id}")]]
                
                return await message.reply_text(
                    f"<blockquote>✅ <b>Tᴏᴋᴇɴ Vᴇʀɪғɪᴇᴅ!</b>\n\nVᴀʟɪᴅ Fᴏʀ: {get_exp_time(verify_expire)}\n\n"
                    "Cʟɪᴄᴋ Tʜᴇ Bᴜᴛᴛᴏɴ Bᴇʟᴏᴡ Tᴏ Gᴇᴛ Yᴏᴜʀ Fɪʟᴇ 👇</blockquote>",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=protect_content_val,
                    quote=False
                )

            if not verify_status['is_verified'] and not is_premium:
                # 🛠️ 10 से 12 कैरेक्टर का टोकन जनरेट करने की लॉजिक
                token_length = random.randint(10, 12)
                token = ''.join(random.choices(string.ascii_letters + string.digits, k=token_length))
                
                try:
                    await db.save_verify_token(user_id, token)
                except Exception as e:
                    logger.error(f"Failed to insert verify token: {e}")

                await db.update_verify_status(user_id, verify_token=token, link=base64_string)
                
                render_verify_link = f"{render_domain.rstrip('/')}/verify?token={token}"

                btn = [
                    [
                        InlineKeyboardButton("• Vᴇʀɪғʏ Nᴏᴡ •", web_app=WebAppInfo(url=render_verify_link)),
                        InlineKeyboardButton("• Tᴜᴛᴏʀɪᴀʟ •", url=tut_vid)
                    ],
                    [
                        InlineKeyboardButton("• Bᴜʏ Pʀᴇᴍɪᴜᴍ •", callback_data="premium", style=enums.ButtonStyle.PRIMARY)
                    ]
                ]
                return await message.reply_text(
                    f"<blockquote><b>Yᴏᴜʀ Tᴏᴋᴇɴ Hᴀs E xᴘɪʀᴇᴅ. Pʟᴇᴀsᴇ Rᴇғʀᴇsʜ Yᴏᴜʀ Tᴏᴋᴇɴ Tᴏ Cᴏɴᴛɪɴᴜᴇ..</b>\n\n<b>Tᴏᴋᴇɴ Tɪᴍᴇᴏᴜᴛ:</b> {get_exp_time(verify_expire)}</blockquote>",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=protect_content_val,
                    quote=False
                )

        # Standard Base64 Processing
        try:
            decoded_str = await decode(base64_string)
            argument = decoded_str.split("-")
        except Exception as e:
            logger.error(f"Error decoding string {base64_string}: {e}")
            return await message.reply_text("<blockquote>⚠️ <b>Iɴᴠᴀʟɪᴅ Lɪɴᴋ Oʀ Fɪʟᴇ Hᴀsʜ!</b></blockquote>", quote=False)

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
            [InlineKeyboardButton("🛠️ Dᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)],
            [InlineKeyboardButton("🌀 Cᴀɴᴄᴇʟ 🌀", callback_data=f"cancel_delivery_{user_id}", style=enums.ButtonStyle.DANGER)]
        ])
        temp_msg = await message.reply_text("<blockquote><b>🔺 Pʟᴇᴀsᴇ Wᴀɪᴛ...</b></blockquote>", reply_markup=wait_markup, quote=False)
        
        try:
            messages = await get_messages(client, ids)
        except Exception as e:
            await message.reply_text("<blockquote>⚠️ <b>Sᴏᴍᴇᴛʜɪɴɢ Wᴇɴᴛ Wʀᴏɴɢ!</b></blockquote>", quote=False)
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
            await message.reply_text("<blockquote>❌ <b>Fɪʟᴇ Dᴇʟɪᴠᴇʀʏ Hᴀs Bᴇᴇɴ Cᴀɴᴄᴇʟʟᴇᴅ Sᴜᴄᴄᴇssғᴜʟʟʏ.</b></blockquote>", quote=False)
            return

        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply_text(
                f"<blockquote><b>Tʜɪs Fɪʟᴇ Wɪʟʟ Bᴇ Dᴇʟᴇᴛᴇᴅ Iɴ {get_exp_time(FILE_AUTO_DELETE)}. Pʟᴇᴀsᴇ Sᴀᴠᴇ Oʀ Fᴏʀᴡᴀʀᴅ Iᴛ Tᴏ Yᴏᴜʀ Sᴀᴠᴇᴅ MᴇssᴀɢES Bᴇғᴏʀᴇ Iᴛ Gᴇᴛs Dᴇʟᴇᴛᴇᴅ.</b></blockquote>",
                quote=False
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
                    f"https://t.me/{bot_username}?start={message.command[1]}"
                    if message.command and len(message.command) > 1
                    else None
                )
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("Gᴇᴛ Fɪʟᴇ Aɢᴀɪɴ!", url=reload_url)]]
                ) if reload_url else None

                await notification_msg.edit(
                    "<blockquote><b>Yᴏᴜʀ Vɪᴅᴇᴏ / Fɪʟᴇ Is Sᴜᴄᴄᴇssғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ !!\n\nCʟɪᴄᴋ Bᴇʟᴏᴡ Bᴜᴛᴛᴏɴ Tᴏ Gᴇᴛ Yᴏᴜʀ Dᴇʟᴇᴛᴇᴅ Vɪᴅᴇᴏ / Fɪʟᴇ 👇</b></blockquote>",
                    reply_markup=keyboard
                )
            except Exception:
                pass
    else:
        try:
            sticker_msg = await message.reply_sticker(sticker=START_STICKER, quote=False)
            await asyncio.sleep(0.4)
            await sticker_msg.delete()
        except Exception:
            pass  
        
        dyn_start_msg = bot_settings.get('start_msg') or START_MSG

        dyn_start_pic = bot_settings.get('start_pic', '')
        if isinstance(dyn_start_pic, str):
            dyn_start_pic = dyn_start_pic.strip()
            if dyn_start_pic.lower() in ["none", "off", "no", "false"]:
                dyn_start_pic = ""

        is_spoiler = bot_settings.get('start_pic_spoiler', False)

        reply_markup = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("• Cʜᴀɴɴᴇʟs •", callback_data='channels', style=enums.ButtonStyle.PRIMARY)],
                [
                    InlineKeyboardButton("• Aʙᴏᴜᴛ •", callback_data="about"),
                    InlineKeyboardButton("• Hᴇʟᴘ •", callback_data="help")
                ],
                [
                    InlineKeyboardButton("⚙️ Sᴇᴛᴛɪɴɢs", callback_data="cb_settings")
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

        formatted_caption = f"<blockquote>{formatted_caption}</blockquote>"

        if dyn_start_pic:
            try:
                await message.reply_photo(
                    photo=dyn_start_pic,
                    caption=formatted_caption,
                    has_spoiler=is_spoiler,
                    reply_markup=reply_markup,
                    effect_id=int(random.choice(EFFECT_IDS)),
                    quote=False
                )
            except Exception:
                try:
                    await message.reply_photo(
                        photo=dyn_start_pic,
                        caption=formatted_caption,
                        reply_markup=reply_markup,
                        quote=False
                    )
                except Exception:
                    await message.reply_text(
                        text=formatted_caption,
                        reply_markup=reply_markup,
                        link_preview_options=LinkPreviewOptions(is_disabled=True),
                        quote=False
                    )
        else:
            await message.reply_text(
                text=formatted_caption,
                reply_markup=reply_markup,
                link_preview_options=LinkPreviewOptions(is_disabled=True),
                quote=False
            )
        return


@Bot.on_callback_query(filters.regex("^cb_settings$"))
async def cb_settings_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if user_id not in ADMINS:
        return await query.answer("⚠️ Tʜɪs Is Oɴʟʏ Fᴏʀ Aᴅᴍɪɴs ⚠️", show_alert=True)
    
    await query.answer()
    await send_main_settings_panel(query)


# ==============================================================================
# FIXED MULTI-BATCH START HANDLER (INLINE BUTTONS WITH DIRECT LINKS)
# ==============================================================================
async def handle_multi_batch_start(client: Client, message: Message, payload: str):
    try:
        batch_id = payload.replace("mbatch_", "").replace("batch_", "").strip().lower()
        batch_data = await db.get_multi_batch(batch_id)

        if not batch_data or not batch_data.get("ranges"):
            await message.reply_text("<blockquote>❌ <b>Nᴏ Eᴘɪsᴏᴅᴇs Fᴏᴜɴᴅ Iɴ Tʜɪs Bᴀᴛᴄʜ!</b></blockquote>", quote=False)
            return

        ranges = batch_data.get("ranges", [])
        db_channel_id = abs(get_db_channel_id(client))
        bot_username = getattr(getattr(client, 'me', None), 'username', None) or "SmartfilestorebyAcbot"

        temp_buttons = []
        for item in ranges:
            batch_hash = item.get("base64_hash", "")
            if not batch_hash:
                start_id = item.get("start_id", 0)
                end_id = item.get("end_id", 0)
                raw_string = f"get-{start_id * db_channel_id}-{end_id * db_channel_id}"
                batch_hash = await encode(raw_string)

            batch_url = f"https://t.me/{bot_username}?start={batch_hash}"
            temp_buttons.append(InlineKeyboardButton(f"📺 {item['title']}", url=batch_url))

        keyboard = []
        for i in range(0, len(temp_buttons), 2):
            keyboard.append(temp_buttons[i:i + 2])

        markup = InlineKeyboardMarkup(keyboard)
        
        mbatch_msg = await message.reply_text(
            f"<blockquote>🎬 <b>Mᴜʟᴛɪ-Bᴀᴛᴄʜ Eᴘɪsᴏᴅᴇs:</b> <code>{batch_id.upper()}</code>\n\n"
            f"👇 <b>Cʟɪᴄᴋ Tʜᴇ Bᴜᴛᴛᴏɴs Bᴇʟᴏᴡ Tᴏ Gᴇᴛ Yᴏᴜʀ Eᴘɪsᴏᴅᴇs:</b>\n\n"
            f"⏳ <i>Tʜɪs ᴍᴇssᴀɢE ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛᴇᴅ ɪɴ 1 ᴍɪɴᴜᴛE.</i></blockquote>",
            reply_markup=markup,
            quote=False
        )

        await asyncio.sleep(60)
        try:
            await mbatch_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"❌ [START MBATCH ERROR] {e}\n{traceback.format_exc()}")
        await message.reply_text(f"<blockquote>❌ <b>Sᴛᴀʀᴛ EʀʀᴏR:</b> <code>{e}</code></blockquote>", quote=False)


# ==============================================================================
# FALLBACK PLAIN TEXT RESPONSE HANDLER (FOR KEYBOARD BUTTON TEXT CLICKS)
# ==============================================================================
@Bot.on_message(filters.private & filters.text & ~filters.command(["start", "myplan", "addpremium", "remove_premium", "premium_users", "count", "commands", "multi_batch"]))
async def handle_text_button_click(client: Client, message: Message):
    text = message.text.replace("📺", "").strip()
    user_id = message.from_user.id

    if not await is_subscribed(client, user_id):
        return await not_joined(client, message)

    try:
        all_batches = await db.get_all_multi_batches() if hasattr(db, "get_all_multi_batches") else []
        for batch in all_batches:
            for item in batch.get("ranges", []):
                if item.get("title", "").strip().lower() == text.lower():
                    batch_hash = item.get("base64_hash", "")
                    if batch_hash:
                        message.text = f"/start {batch_hash}"
                        return await start_command(client, message)
    except Exception as e:
        logger.error(f"Error handling plain text button fallback: {e}")


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


chat_data_cache = {}

async def not_joined(client: Client, message: Message):
    temp = await message.reply_text("<blockquote><b><i>Cʜᴇᴄᴋɪɴɢ Sᴜʙsᴄʀɪᴘᴛɪᴏɴ...</i></b></blockquote>", quote=False)
    user_id = message.from_user.id
    buttons = []
    count = 0
    bot_username = getattr(getattr(client, 'me', None), 'username', None) or "SmartfilestorebyAcbot"

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
                    await temp.edit(f"<blockquote><b>{'! ' * count}</b></blockquote>")

                except Exception as e:
                    logger.error(f"Error with chat {chat_id}: {e}")
                    try: return await temp.edit("<blockquote><b><i>! EʀʀᴏR, Cᴏɴᴛᴀᴄᴛ Dᴇᴠᴇʟᴏᴘᴇʀ @rohit_1888</i></b></blockquote>")
                    except Exception: return

        try:
            buttons.append([
                InlineKeyboardButton(
                    text='♻️ Tʀʏ Aɢᴀɪɴ',
                    url=f"https://t.me/{bot_username}?start={message.command[1]}"
                )
            ])
        except IndexError:
            pass

        await message.reply_photo(
            photo=FORCE_PIC,
            caption=f"<blockquote>{FORCE_MSG.format(first=message.from_user.first_name, last=message.from_user.last_name if message.from_user.last_name else '', username=f'@{message.from_user.username}' if message.from_user.username else '', mention=message.from_user.mention, id=message.from_user.id)}</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=False
        )

    except Exception as e:
        logger.error(f"Final Error: {e}")
        try: await temp.edit("<blockquote><b><i>! EʀʀᴏR, Cᴏɴᴛᴀᴄᴛ Dᴇᴠᴇʟᴏᴘᴇʀ...</i></b></blockquote>")
        except Exception: pass


@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id  
    status_message = await check_user_plan(user_id)
    await message.reply_text(f"<blockquote>{status_message}</blockquote>", quote=False)


@Bot.on_message(filters.command('addpremium') & filters.private & admin)
async def add_premium_user_command(client: Client, msg: Message):
    if len(msg.command) != 4:
        await msg.reply_text(
            "<blockquote>⚠️ <b>UꜱᴀɢE:</b> /addpremium &lt;user_id&gt; &lt;time_value&gt; &lt;time_unit&gt;\n\n"
            "<b>Tɪᴍᴇ Uɴɪᴛs:</b>\n"
            "s - sᴇᴄᴏɴᴅs\n"
            "m - ᴍɪɴᴜᴛES\n"
            "h - ʜᴏᴜʀs\n"
            "d - ᴅᴀʏs\n"
            "y - ʏᴇᴀʀs\n\n"
            "<b>E xᴀᴍᴘʟES:</b>\n"
            "/addpremium 123456789 30 m → 30 ᴍɪɴᴜᴛᴇs\n"
            "/addpremium 123456789 2 h → 2 ʜᴏᴜʀs\n"
            "/addpremium 123456789 1 d → 1 ᴅᴀʏ\n"
            "/addpremium 123456789 1 y → 1 ʏᴇᴀʀ</blockquote>",
            quote=False
        )
        return

    try:
        user_id = int(msg.command[1])
        time_value = int(msg.command[2])
        time_unit = msg.command[3].lower()  

        expiration_time = await add_premium(user_id, time_value, time_unit)

        await msg.reply_text(
            f"<blockquote>✅ <b>Uꜱᴇʀ <code>{user_id}</code> Aᴅᴅᴇᴅ As A PʀᴇᴍɪᴜM Uꜱᴇʀ Fᴏʀ {time_value} {time_unit}.</b>\n"
            f"<b>E xᴘɪʀᴀᴛɪᴏɴ Tɪᴍᴇ:</b> <code>{expiration_time}</code></blockquote>",
            quote=False
        )

        try:
            await client.send_message(
                chat_id=user_id,
                text=(
                    f"<blockquote>🎉 <b>PʀᴇᴍɪᴜM Aᴄᴛɪᴠᴀᴛᴇᴅ!</b>\n\n"
                    f"Yᴏᴜ ʜᴀᴠᴇ ʀᴇᴄᴇɪᴠᴇᴅ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ғᴏʀ <code>{time_value} {time_unit}</code>.\n"
                    f"<b>E xᴘɪʀᴇs Oɴ:</b> <code>{expiration_time}</code></blockquote>"
                ),
            )
        except Exception:
            pass

    except ValueError:
        await msg.reply_text("<blockquote>❌ <b>Iɴᴠᴀʟɪᴅ Iɴᴘᴜᴛ. Pʟᴇᴀsᴇ Eɴsᴜʀᴇ Uꜱᴇʀ ID Aɴᴅ Tɪᴍᴇ Vᴀʟᴜᴇ Aʀᴇ NᴜᴍʙᴇRs.</b></blockquote>", quote=False)
    except Exception as e:
        await msg.reply_text(f"<blockquote>⚠️ <b>Aɴ EʀʀᴏR Oᴄᴄᴜʀʀᴇᴅ:</b> <code>{str(e)}</code></blockquote>", quote=False)


@Bot.on_message(filters.command('remove_premium') & filters.private & admin)
async def pre_remove_user(client: Client, msg: Message):
    if len(msg.command) != 2:
        await msg.reply_text("<blockquote>⚠️ <b>UꜱᴀɢE:</b> /remove_premium user_id</blockquote>", quote=False)
        return
    try:
        user_id = int(msg.command[1])
        await remove_premium(user_id)
        await msg.reply_text(f"<blockquote>✅ <b>Uꜱᴇʀ <code>{user_id}</code> Hᴀs Bᴇᴇɴ Rᴇᴍᴏᴠᴇᴅ.</b></blockquote>", quote=False)
    except ValueError:
        await msg.reply_text("<blockquote>⚠️ <b>Uꜱᴇʀ ID Mᴜsᴛ Bᴇ Aɴ IɴᴛᴇGFᴇʀ Oʀ Nᴏᴛ Aᴠᴀɪʟᴀʙʟᴇ Iɴ Dᴀᴛᴀʙᴀsᴇ.</b></blockquote>", quote=False)


@Bot.on_message(filters.command('premium_users') & filters.private & admin)
async def list_premium_users_command(client: Client, message: Message):
    ist = timezone("Asia/Kolkata")
    premium_users_cursor = collection.find({})
    premium_user_list = ['Aᴄᴛɪᴠᴇ Pʀᴇᴍɪᴜᴍ Uꜱᴇʀs Iɴ Dᴀᴛᴀʙᴀsᴇ:']
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
        await message.reply_text("<blockquote><b>I ғᴏᴜɴᴅ 0 ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴜsᴇʀs ɪɴ ᴍʏ DB</b></blockquote>", quote=False)
    else:
        out_text = "\n\n".join(premium_user_list)
        await message.reply_text(f"<blockquote>{out_text}</blockquote>", quote=False)


@Bot.on_message(filters.command("count") & filters.private & admin)
async def total_verify_count_cmd(client: Client, message: Message):
    total = await db.get_total_verify_count()
    await message.reply_text(f"<blockquote><b>Tᴏᴛᴀʟ Vᴇʀɪғɪᴇᴅ Tᴏᴋᴇɴs Tᴏᴅᴀʏ:</b> <code>{total}</code></blockquote>", quote=False)


@Bot.on_message(filters.command('commands') & filters.private & admin)
async def bcmd(bot: Bot, message: Message):        
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• Cʟᴏsᴇ •", callback_data="close")]])
    await message.reply_text(text=f"<blockquote>{CMD_TXT}</blockquote>", reply_markup=reply_markup, quote=True)
