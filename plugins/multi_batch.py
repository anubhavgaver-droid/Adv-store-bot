import asyncio
import logging
import traceback
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper_func import admin, encode

# ✅ Bot Instance Import
from bot import Bot

# ✅ Database Import (Rohit Class Object)
from database.database import db

# Logger Setup
logger = logging.getLogger(__name__)

# --- Helper Functions ---
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
            logger.error(f"❌ [LINK PARSE ERROR] {e}\n{traceback.format_exc()}")
            return None, None
    return None, None


# DB Channel ID Safe Fetcher
def get_db_channel_id(client: Client):
    if hasattr(client, "db_channel") and client.db_channel:
        return getattr(client.db_channel, "id", client.db_channel)
    try:
        from config import DB_CHANNEL
        return DB_CHANNEL
    except Exception:
        return None


# Admin Menu Show Karne Ka Function
async def show_admin_batch_menu(client: Client, user_id: int, batch_id: str, message_to_edit=None):
    try:
        batch_data = await db.get_multi_batch(batch_id)
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
            f"⚙️ **Multi-Batch Editor:** `{batch_id}`\n\n"
            f"Total Episode Buttons: `{len(ranges)}`\n\n"
            f"Naya episode range add karne ke liye **➕ Add** button par click karein."
        )

        if message_to_edit:
            await message_to_edit.edit_text(text, reply_markup=markup)
        else:
            await client.send_message(user_id, text, reply_markup=markup)
    except Exception as e:
        logger.error(f"❌ [MENU DISPLAY ERROR] {e}\n{traceback.format_exc()}")


# ==============================================================================
# 1. /multi_batch <batch_name> Command
# ==============================================================================
@Bot.on_message(filters.private & admin & filters.command("multi_batch"))
async def multi_batch_cmd(client: Client, message: Message):
    try:
        logger.info(f"📥 [/multi_batch COMMAND RECEIVED] From User: {message.from_user.id}")
        if len(message.command) < 2:
            await message.reply_text("❌ **Usage:** `/multi_batch <batch_id>`\n\nExample: `/multi_batch naruto_series`", quote=True)
            return

        batch_id = message.command[1].strip().lower()
        await db.create_multi_batch(batch_id)
        await show_admin_batch_menu(client, message.from_user.id, batch_id)
    except Exception as e:
        logger.error(f"❌ [/multi_batch ERROR] {e}\n{traceback.format_exc()}")
        await message.reply_text(f"❌ **Command Error:** `{e}`")


# ==============================================================================
# 2. User Master Link Click Handler (/start mbatch_...)
# ==============================================================================
@Bot.on_message(filters.private & filters.command("start") & filters.regex(r"mbatch_"))
async def start_mbatch_handler(client: Client, message: Message):
    try:
        logger.info(f"📥 [START MBATCH RECEIVED] From User: {message.from_user.id}")
        text_data = message.text.split()
        if len(text_data) > 1:
            batch_id = text_data[1].replace("mbatch_", "").strip().lower()
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
# 3. Callback Query Handler (हर बटन पर ट्रैकिंग और एरर प्रिंटिंग)
# ==============================================================================
@Bot.on_callback_query(filters.regex(r"^(add_mrange_|del_mrange_|get_mlink_|user_mget_|ignore)"), group=-1)
async def multi_batch_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    # 🛑 1. लॉग में हर बटन प्रेस दिखेगा
    logger.info(f"🔘 [BUTTON CLICKED] Data: '{data}' | User ID: {user_id}")

    try:
        if data == "ignore":
            await query.answer("यह सिर्फ़ टाइटल बटन है।", show_alert=False)
            return

        await query.answer()

        # --- Naya Range Add karna (+) ---
        if data.startswith("add_mrange_"):
            batch_id = data.replace("add_mrange_", "")

            if not hasattr(client, "ask"):
                err_msg = "pyromod is missing in Bot client! Add 'import pyromod' in bot.py"
                logger.error(f"❌ [ADD RANGE ERROR] {err_msg}")
                await query.message.reply(f"❌ **Error:** `{err_msg}`")
                return

            # Step 1: Title
            logger.info(f"👉 [ADD RANGE STEP 1] Asking title from user {user_id}")
            try:
                title_msg = await client.ask(
                    chat_id=user_id,
                    text="📝 **Enter Button Name/Title:**\n\n(Example: `Ep 1 to 100` ya `Season 1`)",
                    timeout=60
                )
                if not title_msg or not title_msg.text:
                    await query.message.reply("❌ Invalid title!")
                    return
                btn_title = title_msg.text.strip()
            except Exception as e:
                logger.error(f"❌ [ADD RANGE STEP 1 TIMEOUT/ERROR] {e}\n{traceback.format_exc()}")
                await query.message.reply(f"❌ **Timeout/Error (Step 1):** `{e}`")
                return

            # Step 2: First Message
            logger.info(f"👉 [ADD RANGE STEP 2] Asking First Message from user {user_id}")
            try:
                f_msg = await client.ask(
                    chat_id=user_id,
                    text=f" Forward First Message for **'{btn_title}'** from Channel OR send link:",
                    timeout=60
                )
                if not f_msg:
                    return
            except Exception as e:
                logger.error(f"❌ [ADD RANGE STEP 2 TIMEOUT/ERROR] {e}\n{traceback.format_exc()}")
                await query.message.reply(f"❌ **Timeout/Error (Step 2):** `{e}`")
                return
            f_chat_id, f_msg_id = await get_chat_and_msg_id(client, f_msg)

            # Step 3: Last Message
            logger.info(f"👉 [ADD RANGE STEP 3] Asking Last Message from user {user_id}")
            try:
                s_msg = await client.ask(
                    chat_id=user_id,
                    text=f" Forward Last Message for **'{btn_title}'** from Channel OR send link:",
                    timeout=60
                )
                if not s_msg:
                    return
            except Exception as e:
                logger.error(f"❌ [ADD RANGE STEP 3 TIMEOUT/ERROR] {e}\n{traceback.format_exc()}")
                await query.message.reply(f"❌ **Timeout/Error (Step 3):** `{e}`")
                return
            s_chat_id, s_msg_id = await get_chat_and_msg_id(client, s_msg)

            if not f_chat_id or not s_chat_id or f_chat_id != s_chat_id:
                logger.warning(f"⚠️ [ADD RANGE INVALID] Chat IDs mismatched or null: {f_chat_id} vs {s_chat_id}")
                await query.message.reply("❌ Invalid links/messages or different channels!")
                return

            db_channel_id = get_db_channel_id(client)
            status = await query.message.reply("⏳ Storing episodes in DB channel...")
            copied_start, copied_end = None, None

            if f_chat_id == db_channel_id:
                copied_start, copied_end = f_msg_id, s_msg_id
            else:
                logger.info(f"🔄 Copying messages from {f_msg_id} to {s_msg_id}...")
                for m_id in range(f_msg_id, s_msg_id + 1):
                    try:
                        m = await client.get_messages(f_chat_id, m_id)
                        if m and not m.empty:
                            cp = await m.copy(db_channel_id, disable_notification=True)
                            if copied_start is None:
                                copied_start = cp.id
                            copied_end = cp.id
                            await asyncio.sleep(0.3)
                    except Exception as e:
                        logger.error(f"❌ [COPY MSG ERROR] Msg ID {m_id}: {e}")
                        continue
                await status.delete()

            new_range = {
                "title": btn_title,
                "start_id": copied_start,
                "end_id": copied_end
            }

            await db.add_range_to_multi_batch(batch_id, new_range)
            logger.info(f"✅ [RANGE ADDED SUCCESSFULLY] Batch: {batch_id} | Range: {btn_title}")
            await show_admin_batch_menu(client, user_id, batch_id)

        # --- Master Link Get karna ---
        elif data.startswith("get_mlink_"):
            batch_id = data.replace("get_mlink_", "")
            bot_username = client.me.username if getattr(client, "me", None) else (await client.get_me()).username
            link = f"https://t.me/{bot_username}?start=mbatch_{batch_id}"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
            await query.message.reply_text(f"✨ **Here is your Master Episode Link:**\n\n{link}", reply_markup=reply_markup)

        # --- Delete Range ---
        elif data.startswith("del_mrange_"):
            _, _, batch_id, index = data.split("_")
            index = int(index)
            batch_data = await db.get_multi_batch(batch_id)
            ranges = batch_data.get("ranges", []) if batch_data else []
            if 0 <= index < len(ranges):
                removed = ranges.pop(index)
                await db.update_multi_batch_ranges(batch_id, ranges)
                logger.info(f"🗑️ [RANGE DELETED] Removed '{removed.get('title')}' from Batch {batch_id}")
            await show_admin_batch_menu(client, user_id, batch_id, message_to_edit=query.message)

        # --- User Episode Delivery ---
        elif data.startswith("user_mget_"):
            _, _, batch_id, index = data.split("_")
            index = int(index)
            batch_data = await db.get_multi_batch(batch_id)

            if not batch_data or "ranges" not in batch_data or index >= len(batch_data["ranges"]):
                logger.warning(f"⚠️ [USER GET INVALID] Batch: {batch_id}, Index: {index}")
                await query.answer("❌ Invalid batch or episode range!", show_alert=True)
                return

            target_range = batch_data["ranges"][index]
            db_channel_id = get_db_channel_id(client)

            await query.answer(f"Sending {target_range['title']}...", show_alert=False)
            logger.info(f"📤 [SENDING EPISODES] To User {user_id} | Range: {target_range['start_id']} to {target_range['end_id']}")

            for m_id in range(target_range["start_id"], target_range["end_id"] + 1):
                try:
                    await client.copy_message(
                        chat_id=user_id,
                        from_chat_id=db_channel_id,
                        message_id=m_id
                    )
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"❌ [SEND MSG ERROR] Msg ID {m_id} to User {user_id}: {e}")

    # 🛑 2. पूरे फंक्शन में कोई भी अनपेक्षित (Unhandled) एरर आएगा तो यहाँ प्रिंट होगा
    except Exception as e:
        full_traceback = traceback.format_exc()
        logger.error(f"💥 [CRITICAL CALLBACK ERROR] Button Data: '{data}' | User: {user_id}\nError: {e}\n{full_traceback}")
        
        # यूज़र की स्क्रीन पर अलर्ट दिखाएं
        try:
            await query.answer(f"❌ Bot Internal Error: {str(e)[:50]}", show_alert=True)
            await query.message.reply(f"❌ **Unhandled Error Occurred:**\n`{e}`\n\n Check logs for full Traceback.")
        except Exception:
            pass
