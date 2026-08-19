import asyncio
import os
import random
import sys
import re
import string 
import string as rohit
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters, __version__, enums
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MessageNotModified
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, MessageDeleteForbidden
from bot import Bot
from config import *
from helper_func import *
from database.database import *
from database.db_premium import *
from pytz import timezone

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

# Helper Function for Channel Message Parsing
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
        except Exception:
            return None, None
    return None, None


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

    # ✅ Check Force Subscription
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

        # =====================================================================
        # 🔐 UNIFIED TOKEN VERIFICATION SYSTEM (All Payloads Covered)
        # =====================================================================
        verify_status = await db.get_verify_status(id)

        if SHORTLINK_URL or SHORTLINK_API:
            # 1️⃣ Check Expiration
            if verify_status.get('is_verified', False) and VERIFY_EXPIRE < (time.time() - verify_status.get('verified_time', 0)):
                await db.update_verify_status(user_id, is_verified=False)
                verify_status['is_verified'] = False 

            # 2️⃣ CASE: When user completes verification & clicks token link
            if "verify_" in text:
                _, token = text.split("_", 1)
                if verify_status.get('verify_token') != token:
                    return await message.reply("⚠️ 𝖨nv𝖺ʟɪᴅ 𝗍ᴏᴋᴇɴ. 𝖯ʟᴇ𝖺𝗌ᴇ /start 𝖺𝗀αɪɴ.")

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

            # 3️⃣ CASE: If user is NOT verified and NOT premium -> Enforce Shortener Token
            if not verify_status.get('is_verified', False) and not is_premium:
                await client.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
                
                token = ''.join(random.choices(rohit.ascii_letters + rohit.digits, k=10))
                await db.update_verify_status(id, verify_token=token, link=base64_string)
                
                link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{client.username}?start=verify_{token}')
                btn = [
                    [InlineKeyboardButton("• 𝚅𝙴𝚁𝙸𝙵𝚈 •", url=link),
                     InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
                    [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜM •", callback_data="premium", style=enums.ButtonStyle.PRIMARY)]
                ]
                return await message.reply(
                    f"<b>𝗬𝗼𝘂𝗿 𝘁𝗼𝗸𝗲𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗿𝗲𝗳𝗿𝗲𝘀𝗵 ʏᴏᴜʀ ᴛᴏᴋᴇɴ ᴛᴏ 𝗰𝗼𝗻𝘁𝗶𝗻𝘂𝗲..</b>\n\n<b>Tᴏᴋᴇɴ Tɪᴍᴇᴏᴜᴛ:</b> {get_exp_time(VERIFY_EXPIRE)}",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=True
                )

        # =====================================================================
        # 🚀 4️⃣ CASE: User Verified / Premium -> Process Payloads
        # =====================================================================

        # A) MULTI-BATCH MASTER LINK HANDLING
        if base64_string.startswith("mbatch_"):
            batch_id = base64_string.replace("mbatch_", "").strip().lower()
            batch_data = await db.multi_batches.find_one({"batch_id": batch_id})

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

        # B) SINGLE / STANDARD BATCH FILE HANDLING
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

        # Unified UI Wait Markup (Developer + Cancel)
        wait_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁🛠️", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)
            ],[
                InlineKeyboardButton("🌀 𝙲𝙰𝙽𝙲𝙴𝙻 🌀", callback_data=f"cancel_delivery_{user_id}", style=enums.ButtonStyle.DANGER)
            ]
        ])
        temp_msg = await message.reply("<b>🔺 ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...</b>", reply_markup=wait_markup)
        
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
            await message.reply_text("❌ <b>Delivery cancelled successfully!</b>")
            return

        if FILE_AUTO_DELETE > 0:
            notification_msg = await message.reply(
                f"<b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ {get_exp_time(FILE_AUTO_DELETE)}. Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ ᴛᴏ ʏᴏᴜʀ sᴀᴠᴇᴅ ᴍᴇssᴀɢᴇs.</b>"
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
                    "<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!\n\nᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ᴅᴇʟᴇᴛᴇᴅ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ 👇</b>",
                    reply_markup=keyboard
                )
            except Exception as e:
                print(f"Error updating notification: {e}")
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
# 🎬 MULTI-BATCH ADMIN SYSTEM & CALLBACK HANDLERS
# ==============================================================================

async def show_admin_batch_menu(client: Client, user_id: int, batch_id: str, message_to_edit=None):
    batch_data = await db.multi_batches.find_one({"batch_id": batch_id})
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
        await message.reply_text("❌ <b>Usage:</b> <code>/multi_batch <batch_name></code>\n\nExample: <code>/multi_batch naruto</code>")
        return

    batch_id = message.command[1].strip().lower()
    batch_data = await db.multi_batches.find_one({"batch_id": batch_id})

    if not batch_data:
        await db.multi_batches.insert_one({"batch_id": batch_id, "ranges": []})

    await show_admin_batch_menu(client, message.from_user.id, batch_id)


@Bot.on_callback_query(filters.regex(r"^(add_mrange_|del_mrange_|get_mlink_|user_mget_)"))
async def multi_batch_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # --- 1. User Clicks Episode Range Button ---
    if data.startswith("user_mget_"):
        _, _, batch_id, index = data.split("_")
        index = int(index)

        # 🔐 Episode Click Token Verification Check
        is_premium = await is_premium_user(user_id)
        verify_status = await db.get_verify_status(user_id)

        if SHORTLINK_URL or SHORTLINK_API:
            if verify_status.get('is_verified', False) and VERIFY_EXPIRE < (time.time() - verify_status.get('verified_time', 0)):
                await db.update_verify_status(user_id, is_verified=False)
                verify_status['is_verified'] = False

            if not verify_status.get('is_verified', False) and not is_premium:
                token = ''.join(random.choices(rohit.ascii_letters + rohit.digits, k=10))
                await db.update_verify_status(user_id, verify_token=token, link=f"mbatch_{batch_id}")
                link = await get_shortlink(SHORTLINK_URL, SHORTLINK_API, f'https://t.me/{client.username}?start=verify_{token}')
                
                btn = [
                    [InlineKeyboardButton("• 𝚅𝙴𝚁𝙸𝙵𝚈 •", url=link),
                     InlineKeyboardButton("• ᴛᴜᴛᴏʀɪᴀʟ •", url=TUT_VID)],
                    [InlineKeyboardButton("• ʙᴜʏ ᴘʀᴇᴍɪᴜM •", callback_data="premium", style=enums.ButtonStyle.PRIMARY)]
                ]
                await query.answer("⚠️ Verification required!", show_alert=True)
                return await query.message.reply(
                    f"<b>𝗬𝗼𝘂𝗿 𝘁𝗼𝗸𝗲𝗻 𝗵𝗮𝘀 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗣𝗹𝗲𝗮𝘀𝗲 𝗿𝗲𝗳𝗿𝗲𝘀𝗵 ʏᴏᴜʀ ᴛᴏᴋ𝗲ɴ ᴛᴏ 𝗰𝗼𝗻𝘁𝗶𝗻𝘂𝗲..</b>\n\n<b>Tᴏᴋᴇɴ Tɪᴍᴇᴏᴜᴛ:</b> {get_exp_time(VERIFY_EXPIRE)}",
                    reply_markup=InlineKeyboardMarkup(btn),
                    protect_content=True
                )

        batch_data = await db.multi_batches.find_one({"batch_id": batch_id})
        if not batch_data or index >= len(batch_data.get("ranges", [])):
            return await query.answer("❌ Episode range unavailable!", show_alert=True)

        target_range = batch_data["ranges"][index]
        await query.answer(f"Sending {target_range['title']}...", show_alert=False)

        start_id = target_range["start_id"]
        end_id = target_range["end_id"]
        cancel_tasks[user_id] = False

        # Unified Wait UI (Developer + Cancel)
        wait_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("𝙳𝙴𝚅𝙴𝙻𝙾𝙿𝙴𝚁🛠️", url="https://t.me/HDFILM0900_BOT", style=enums.ButtonStyle.PRIMARY)
            ],[
                InlineKeyboardButton("🌀 𝙲𝙰𝙽𝙲𝙴𝙻 🌀", callback_data=f"cancel_delivery_{user_id}", style=enums.ButtonStyle.DANGER)
            ]
        ])
        temp_msg = await client.send_message(user_id, "<b>🔺 ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ... Fetching Episodes</b>", reply_markup=wait_markup)

        codeflix_msgs = []
        FILE_AUTO_DELETE = await db.get_del_timer()

        for m_id in range(start_id, end_id + 1):
            await asyncio.sleep(0.05)
            if cancel_tasks.get(user_id, False) is True:
                break

            await client.send_chat_action(chat_id=user_id, action=ChatAction.UPLOAD_DOCUMENT)
            try:
                copied_msg = await client.copy_message(
                    chat_id=user_id,
                    from_chat_id=client.db_channel.id,
                    message_id=m_id,
                    protect_content=PROTECT_CONTENT
                )
                codeflix_msgs.append(copied_msg)
            except FloodWait as e:
                await asyncio.sleep(e.x)
                if cancel_tasks.get(user_id, False) is True:
                    break
                copied_msg = await client.copy_message(
                    chat_id=user_id,
                    from_chat_id=client.db_channel.id,
                    message_id=m_id,
                    protect_content=PROTECT_CONTENT
                )
                codeflix_msgs.append(copied_msg)
            except Exception as e:
                print(f"Error sending message {m_id}: {e}")

            await asyncio.sleep(0.8)

        was_cancelled = cancel_tasks.pop(user_id, False)
        try: await temp_msg.delete()
        except: pass

        if was_cancelled:
            await client.send_message(user_id, "❌ <b>Delivery cancelled successfully!</b>")
            return

        if FILE_AUTO_DELETE > 0 and codeflix_msgs:
            notification_msg = await client.send_message(
                user_id,
                f"<b>Tʜɪs Fɪʟᴇ ᴡɪʟʟ ʙᴇ Dᴇʟᴇᴛᴇᴅ ɪɴ {get_exp_time(FILE_AUTO_DELETE)}. Pʟᴇᴀsᴇ sᴀᴠᴇ ᴏʀ ғᴏʀᴡᴀʀᴅ ɪᴛ.</b>"
            )
            await asyncio.sleep(FILE_AUTO_DELETE)
            for snt_msg in codeflix_msgs:
                try: await snt_msg.delete()
                except: pass
            try:
                await notification_msg.edit("<b>ʏᴏᴜʀ ᴠɪᴅᴇᴏ / ꜰɪʟᴇ ɪꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ !!</b>")
            except: pass

    # --- 2. Admin Adds Episode Range (+) ---
    elif data.startswith("add_mrange_"):
        batch_id = data.replace("add_mrange_", "")
        chat_id = query.from_user.id

        try:
            title_msg = await client.ask(
                chat_id=chat_id,
                text="📝 <b>Enter Button Name/Title:</b>\n\n(Example: <code>Ep 1 to 100</code> ya <code>Season 1</code>)",
                timeout=60
            )
        except Exception:
            return
        btn_title = title_msg.text.strip()

        try:
            f_msg = await client.ask(
                chat_id=chat_id,
                text=f" Forward First Message for <b>'{btn_title}'</b> from DB Channel OR send link:",
                timeout=60
            )
        except Exception:
            return
        f_chat_id, f_msg_id = await get_chat_and_msg_id(client, f_msg)

        try:
            s_msg = await client.ask(
                chat_id=chat_id,
                text=f" Forward Last Message for <b>'{btn_title}'</b> from DB Channel OR send link:",
                timeout=60
            )
        except Exception:
            return
        s_chat_id, s_msg_id = await get_chat_and_msg_id(client, s_msg)

        if not f_chat_id or not s_chat_id or f_chat_id != s_chat_id:
            await query.message.reply("❌ Invalid links/messages or different channels!")
            return

        status = await query.message.reply("⏳ Storing episodes in DB channel...")
        copied_start, copied_end = None, None

        if f_chat_id == client.db_channel.id:
            copied_start, copied_end = f_msg_id, s_msg_id
        else:
            for m_id in range(f_msg_id, s_msg_id + 1):
                try:
                    m = await client.get_messages(f_chat_id, m_id)
                    if m and not m.empty:
                        cp = await m.copy(client.db_channel.id, disable_notification=True)
                        if copied_start is None:
                            copied_start = cp.id
                        copied_end = cp.id
                        await asyncio.sleep(0.3)
                except Exception:
                    continue
            await status.delete()

        new_range = {
            "title": btn_title,
            "start_id": copied_start,
            "end_id": copied_end
        }
        await db.multi_batches.update_one({"batch_id": batch_id}, {"$push": {"ranges": new_range}})
        await show_admin_batch_menu(client, chat_id, batch_id)

    # --- 3. Admin Gets Master Link ---
    elif data.startswith("get_mlink_"):
        batch_id = data.replace("get_mlink_", "")
        link = f"https://t.me/{client.username}?start=mbatch_{batch_id}"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share Master URL", url=f'https://telegram.me/share/url?url={link}')]])
        await query.message.reply_text(f"✨ <b>Here is your Permanent Editable Link:</b>\n\n{link}", reply_markup=reply_markup)

    # --- 4. Admin Deletes Range ---
    elif data.startswith("del_mrange_"):
        _, _, batch_id, index = data.split("_")
        index = int(index)
        batch_data = await db.multi_batches.find_one({"batch_id": batch_id})
        ranges = batch_data.get("ranges", [])
        if 0 <= index < len(ranges):
            ranges.pop(index)
            await db.multi_batches.update_one({"batch_id": batch_id}, {"$set": {"ranges": ranges}})
        await show_admin_batch_menu(client, query.from_user.id, batch_id, message_to_edit=query.message)


# 🔥 UNIVERSAL CANCELLATION CALLBACK HANDLER 🔥
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

#=====================================================================================##

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

#=====================================================================================##

@Bot.on_message(filters.command('myplan') & filters.private)
async def check_plan(client: Client, message: Message):
    user_id = message.from_user.id  
    status_message = await check_user_plan(user_id)
    await message.reply(status_message)

#=====================================================================================##
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

#=====================================================================================##

@Bot.on_message(filters.command("count") & filters.private & admin)
async def total_verify_count_cmd(client, message: Message):
    total = await db.get_total_verify_count()
    await message.reply_text(f"Tᴏᴛᴀʟ ᴠᴇʀɪғɪᴇᴅ ᴛᴏᴋᴇɴs ᴛᴏᴅᴀʏ: <b>{total}</b>")

#=====================================================================================##

@Bot.on_message(filters.command('commands') & filters.private & admin)
async def bcmd(bot: Bot, message: Message):        
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄʟᴏsᴇ •", callback_data = "close")]])
    await message.reply(text=CMD_TXT, reply_markup = reply_markup, quote=True)
