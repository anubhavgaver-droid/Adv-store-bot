import asyncio
import logging
import traceback
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper_func import admin

# ✅ Bot Instance Import
from bot import Bot

# ✅ Database Import
from database.database import db

# Logger Setup
logger = logging.getLogger(__name__)

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
async def get_chat_and_msg_id(client: Client, message: Message):
    """
    फॉरवर्डेड मैसेज या टेलीग्राम लिंक (t.me/...) से Chat ID और Message ID निकालता है।
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
        except Exception as e:
            logger.error(f"❌ [LINK PARSE ERROR] {e}\n{traceback.format_exc()}")
            return None, None
    return None, None


def get_db_channel_id(client: Client):
    """
    DB Channel ID सुरक्षित तरीके से प्राप्त करता है।
    """
    if hasattr(client, "db_channel") and client.db_channel:
        return getattr(client.db_channel, "id", client.db_channel)
    try:
        from config import DB_CHANNEL
        return DB_CHANNEL
    except Exception:
        return None


async def show_admin_batch_menu(client: Client, user_id: int, batch_id: str, message_to_edit=None):
    """
    एडमिन के लिए Multi-Batch मैनेजमेंट कंट्रोल पैनल दिखाता है।
    """
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
            f"📊 Total Episode Ranges: `{len(ranges)}`\n\n"
            f"नया एपिसोड रेंज जोड़ने के लिए **➕ Add New Episode Range** पर क्लिक करें।"
        )

        if message_to_edit:
            await message_to_edit.edit_text(text, reply_markup=markup)
        else:
            await client.send_message(user_id, text, reply_markup=markup)
    except Exception as e:
        logger.error(f"❌ [MENU DISPLAY ERROR] {e}\n{traceback.format_exc()}")


# ==============================================================================
# 1. /multi_batch <batch_id> COMMAND HANDLER (ADMIN ONLY)
# ==============================================================================
@Bot.on_message(filters.private & admin & filters.command("multi_batch"))
async def multi_batch_cmd(client: Client, message: Message):
    try:
        logger.info(f"📥 [/multi_batch COMMAND] From User: {message.from_user.id}")
        if len(message.command) < 2:
            await message.reply_text(
                "❌ **Usage:** `/multi_batch <batch_id>`\n\n"
                "Example: `/multi_batch naruto_shippuden`",
                quote=True
            )
            return

        batch_id = message.command[1].strip().lower()
        await db.create_multi_batch(batch_id)
        await show_admin_batch_menu(client, message.from_user.id, batch_id)
    except Exception as e:
        logger.error(f"❌ [/multi_batch ERROR] {e}\n{traceback.format_exc()}")
        await message.reply_text(f"❌ **Command Error:** `{e}`")


# ==============================================================================
# 2. CALLBACK QUERY HANDLER (ADD RANGE, DELETE RANGE, GET MASTER LINK)
# ==============================================================================
@Bot.on_callback_query(filters.regex(r"^(add_mrange_|del_mrange_|get_mlink_|ignore)"), group=-1)
async def multi_batch_admin_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    logger.info(f"🔘 [ADMIN BUTTON CLICKED] Data: '{data}' | User ID: {user_id}")

    try:
        if data == "ignore":
            await query.answer("यह सिर्फ़ टाइटल/लेबल बटन है।", show_alert=False)
            return

        await query.answer()

        # --- ➕ नया एपिसोड रेंज जोड़ना ---
        if data.startswith("add_mrange_"):
            batch_id = data.replace("add_mrange_", "")

            if not hasattr(client, "ask"):
                err_msg = "pyromod Client में लोड नहीं है! bot.py में 'import pyromod' जोड़ें।"
                logger.error(f"❌ [ADD RANGE ERROR] {err_msg}")
                await query.message.reply(f"❌ **Error:** `{err_msg}`")
                return

            # Step 1: Title
            logger.info(f"👉 [STEP 1] Prompting Title from user {user_id}")
            try:
                title_msg = await client.ask(
                    chat_id=user_id,
                    text="📝 **Button Name / Episode Title दर्ज करें:**\n\n(उदाहरण: `Episode 01 - 10` या `Season 01`)",
                    timeout=60
                )
                if not title_msg or not title_msg.text:
                    await query.message.reply("❌ अमान्य टाइटल! प्रक्रिया रद्द कर दी गई।")
                    return
                btn_title = title_msg.text.strip()
            except Exception as e:
                logger.error(f"❌ [STEP 1 TIMEOUT/ERROR] {e}\n{traceback.format_exc()}")
                await query.message.reply(f"❌ **समय समाप्त / त्रुटि (Step 1):** `{e}`")
                return

            # Step 2: First Message
            logger.info(f"👉 [STEP 2] Prompting First Message from user {user_id}")
            try:
                f_msg = await client.ask(
                    chat_id=user_id,
                    text=f"📌 **'{btn_title}'** का **पहला (First) मैसेज** फॉरवर्ड करें या उसका पोस्ट लिंक भेजें:",
                    timeout=60
                )
                if not f_msg:
                    return
            except Exception as e:
                logger.error(f"❌ [STEP 2 TIMEOUT/ERROR] {e}\n{traceback.format_exc()}")
                await query.message.reply(f"❌ **समय समाप्त / त्रुटि (Step 2):** `{e}`")
                return

            f_chat_id, f_msg_id = await get_chat_and_msg_id(client, f_msg)

            # Step 3: Last Message
            logger.info(f"👉 [STEP 3] Prompting Last Message from user {user_id}")
            try:
                s_msg = await client.ask(
                    chat_id=user_id,
                    text=f"📌 **'{btn_title}'** का **आखिरी (Last) मैसेज** फॉरवर्ड करें या उसका पोस्ट लिंक भेजें:",
                    timeout=60
                )
                if not s_msg:
                    return
            except Exception as e:
                logger.error(f"❌ [STEP 3 TIMEOUT/ERROR] {e}\n{traceback.format_exc()}")
                await query.message.reply(f"❌ **समय समाप्त / त्रुटि (Step 3):** `{e}`")
                return

            s_chat_id, s_msg_id = await get_chat_and_msg_id(client, s_msg)

            if not f_chat_id or not s_chat_id or f_chat_id != s_chat_id:
                logger.warning(f"⚠️ [INVALID LINK/MSG] Mismatched channels: {f_chat_id} vs {s_chat_id}")
                await query.message.reply("❌ **अमान्य लिंक या चैनल मैच नहीं हुए!** कृपया दोनों मैसेज एक ही चैनल से भेजें।")
                return

            db_channel_id = abs(get_db_channel_id(client))
            status = await query.message.reply("⏳ **फाइलों को DB Channel में प्रोसेस किया जा रहा है...**")
            copied_start, copied_end = None, None

            # यदि मैसेज पहले से ही DB Channel में हैं
            if abs(f_chat_id) == db_channel_id:
                copied_start, copied_end = f_msg_id, s_msg_id
            else:
                logger.info(f"🔄 Copying messages from {f_msg_id} to {s_msg_id} into DB Channel...")
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

            try:
                await status.delete()
            except Exception:
                pass

            if not copied_start or not copied_end:
                await query.message.reply("❌ **फाइल कॉपी करने में विफलता!** कृपया दोबारा प्रयास करें।")
                return

            new_range = {
                "title": btn_title,
                "start_id": copied_start,
                "end_id": copied_end
            }

            await db.add_range_to_multi_batch(batch_id, new_range)
            logger.info(f"✅ [RANGE ADDED] Batch: {batch_id} | Range: {btn_title}")
            await show_admin_batch_menu(client, user_id, batch_id)

        # --- 🔗 Master Share Link प्राप्त करना ---
        elif data.startswith("get_mlink_"):
            batch_id = data.replace("get_mlink_", "")
            bot_username = client.me.username if getattr(client, "me", None) else (await client.get_me()).username
            link = f"https://t.me/{bot_username}?start=mbatch_{batch_id}"
            
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Share URL", url=f"https://telegram.me/share/url?url={link}")]
            ])
            await query.message.reply_text(
                f"✨ **Master Episode Link तैयार है:**\n\n`{link}`",
                reply_markup=reply_markup
            )

        # --- ❌ Episode Range डिलीट करना ---
        elif data.startswith("del_mrange_"):
            parts = data.split("_")
            batch_id = parts[2]
            index = int(parts[3])

            batch_data = await db.get_multi_batch(batch_id)
            ranges = batch_data.get("ranges", []) if batch_data else []

            if 0 <= index < len(ranges):
                removed = ranges.pop(index)
                await db.update_multi_batch_ranges(batch_id, ranges)
                logger.info(f"🗑️ [RANGE DELETED] Removed '{removed.get('title')}' from Batch: {batch_id}")

            await show_admin_batch_menu(client, user_id, batch_id, message_to_edit=query.message)

    except Exception as e:
        full_traceback = traceback.format_exc()
        logger.error(f"💥 [ADMIN CALLBACK ERROR] Data: '{data}' | User: {user_id}\nError: {e}\n{full_traceback}")
        try:
            await query.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)
        except Exception:
            pass
