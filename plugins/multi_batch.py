import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus
from helper_func import admin, encode

# ✅ Bot Instance Import
from bot import Bot

# ✅ Database Import (Rohit Class Object)
from database.database import db

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
            print(f"[LINK PARSE ERROR] {e}")
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
    # ✅ DB Class Method Call
    batch_data = await db.get_multi_batch(batch_id)
    ranges = batch_data.get("ranges", []) if batch_data else []

    buttons = []
    # Purane Saare Ranges Button format mein
    for index, item in enumerate(ranges):
        buttons.append([
            InlineKeyboardButton(f"📺 {item['title']}", callback_data="ignore"),
            InlineKeyboardButton("❌ Delete", callback_data=f"del_mrange_{batch_id}_{index}")
        ])

    # Naya Episode Range Jodne ke liye Plus (+) Button
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


# ==============================================================================
# 1. /multi_batch <batch_name> Command
# ==============================================================================
@Bot.on_message(filters.private & admin & filters.command("multi_batch"))
async def multi_batch_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage:** `/multi_batch <batch_id>`\n\nExample: `/multi_batch naruto_series`", quote=True)
        return

    batch_id = message.command[1].strip().lower()
    
    # ✅ DB Class Method Call
    await db.create_multi_batch(batch_id)

    await show_admin_batch_menu(client, message.from_user.id, batch_id)


# ==============================================================================
# 2. User Master Link Click Handler (/start mbatch_...)
# ==============================================================================
@Bot.on_message(filters.private & filters.command("start") & filters.regex(r"mbatch_"))
async def start_mbatch_handler(client: Client, message: Message):
    try:
        text_data = message.text.split()
        if len(text_data) > 1:
            batch_id = text_data[1].replace("mbatch_", "").strip().lower()
            # ✅ DB Class Method Call
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
                f"🎬 **Multi-Batch Episodes:** `{batch_id}`\n\nNiche diye gaye button par click karke episodes prapt karein:",
                reply_markup=markup
            )
    except Exception as e:
        print(f"[MBATCH START ERROR] {e}")
        await message.reply_text(f"❌ **Error:** `{e}`")


# ==============================================================================
# 3. Callback Query Handler (Add, Delete, Get Link & User Get Buttons)
# ==============================================================================
@Bot.on_callback_query(filters.regex(r"^(add_mrange_|del_mrange_|get_mlink_|user_mget_|ignore)"))
async def multi_batch_callbacks(client: Client, query: CallbackQuery):
    data = query.data

    # Label Button ignore handler
    if data == "ignore":
        await query.answer("यह सिर्फ़ टाइटल बटन है।", show_alert=False)
        return

    await query.answer()

    # --- Naya Range Add karna (+) ---
    if data.startswith("add_mrange_"):
        batch_id = data.replace("add_mrange_", "")
        chat_id = query.from_user.id

        # Check if pyromod is available for client.ask
        if not hasattr(client, "ask"):
            await query.message.reply("❌ **Error:** `pyromod` is missing in your bot instance! Make sure `import pyromod` is added in `bot.py` or `main.py`.")
            return

        # Step 1: Button Title
        try:
            title_msg = await client.ask(
                chat_id=chat_id,
                text="📝 **Enter Button Name/Title:**\n\n(Example: `Ep 1 to 100` ya `Season 1`)",
                timeout=60
            )
            if not title_msg or not title_msg.text:
                await query.message.reply("❌ Invalid title!")
                return
            btn_title = title_msg.text.strip()
        except Exception as e:
            print(f"[ADD RANGE STEP 1 ERROR] {e}")
            await query.message.reply(f"❌ **Timeout/Error:** `{e}`")
            return

        # Step 2: First Message
        try:
            f_msg = await client.ask(
                chat_id=chat_id,
                text=f" Forward First Message for **'{btn_title}'** from Channel OR send link:",
                timeout=60
            )
            if not f_msg:
                return
        except Exception as e:
            print(f"[ADD RANGE STEP 2 ERROR] {e}")
            await query.message.reply(f"❌ **Timeout/Error:** `{e}`")
            return
        f_chat_id, f_msg_id = await get_chat_and_msg_id(client, f_msg)

        # Step 3: Last Message
        try:
            s_msg = await client.ask(
                chat_id=chat_id,
                text=f" Forward Last Message for **'{btn_title}'** from Channel OR send link:",
                timeout=60
            )
            if not s_msg:
                return
        except Exception as e:
            print(f"[ADD RANGE STEP 3 ERROR] {e}")
            await query.message.reply(f"❌ **Timeout/Error:** `{e}`")
            return
        s_chat_id, s_msg_id = await get_chat_and_msg_id(client, s_msg)

        if not f_chat_id or not s_chat_id or f_chat_id != s_chat_id:
            await query.message.reply("❌ Invalid links/messages or different channels!")
            return

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
                        if copied_start is None:
                            copied_start = cp.id
                        copied_end = cp.id
                        await asyncio.sleep(0.3)
                except Exception as e:
                    print(f"[COPY ERROR] Msg ID {m_id}: {e}")
                    continue
            await status.delete()

        new_range = {
            "title": btn_title,
            "start_id": copied_start,
            "end_id": copied_end
        }
        
        # ✅ DB Class Method Call
        await db.add_range_to_multi_batch(batch_id, new_range)
        await show_admin_batch_menu(client, chat_id, batch_id)

    # --- Master Link Get karna ---
    elif data.startswith("get_mlink_"):
        try:
            batch_id = data.replace("get_mlink_", "")
            bot_username = client.me.username if getattr(client, "me", None) else (await client.get_me()).username
            link = f"https://t.me/{bot_username}?start=mbatch_{batch_id}"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
            await query.message.reply_text(f"✨ **Here is your Master Episode Link:**\n\n{link}", reply_markup=reply_markup)
        except Exception as e:
            print(f"[GET LINK ERROR] {e}")
            await query.message.reply(f"❌ **Error:** `{e}`")

    # --- Delete Range ---
    elif data.startswith("del_mrange_"):
        try:
            _, _, batch_id, index = data.split("_")
            index = int(index)
            # ✅ DB Class Method Call
            batch_data = await db.get_multi_batch(batch_id)
            ranges = batch_data.get("ranges", []) if batch_data else []
            if 0 <= index < len(ranges):
                ranges.pop(index)
                # ✅ DB Class Method Call
                await db.update_multi_batch_ranges(batch_id, ranges)
            await show_admin_batch_menu(client, query.from_user.id, batch_id, message_to_edit=query.message)
        except Exception as e:
            print(f"[DEL RANGE ERROR] {e}")
            await query.message.reply(f"❌ **Error:** `{e}`")

    # --- User Episode Delivery ---
    elif data.startswith("user_mget_"):
        try:
            _, _, batch_id, index = data.split("_")
            index = int(index)
            # ✅ DB Class Method Call
            batch_data = await db.get_multi_batch(batch_id)
            
            if not batch_data or "ranges" not in batch_data or index >= len(batch_data["ranges"]):
                await query.answer("❌ Invalid batch or episode range!", show_alert=True)
                return

            target_range = batch_data["ranges"][index]
            db_channel_id = get_db_channel_id(client)

            await query.answer(f"Sending {target_range['title']}...", show_alert=False)

            for m_id in range(target_range["start_id"], target_range["end_id"] + 1):
                try:
                    await client.copy_message(
                        chat_id=query.from_user.id,
                        from_chat_id=db_channel_id,
                        message_id=m_id
                    )
                    await asyncio.sleep(0.5)
                except Exception as e:
                    print(f"Error sending msg: {e}")
        except Exception as e:
            print(f"[USER MGET ERROR] {e}")
