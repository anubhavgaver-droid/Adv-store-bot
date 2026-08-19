import asyncio
import logging
import traceback
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus
from helper_func import admin, encode

# ✅ Bot Instance & Database Import
from bot import Bot
from database.database import db

logger = logging.getLogger(__name__)

# --- Helper Functions (Your Code Pattern) ---
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


async def is_bot_admin(client: Client, chat_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, "me")
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception:
        return False


# Admin Menu Display
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
# 1. /multi_batch <batch_id> Command Handler
# ==============================================================================
@Bot.on_message(filters.private & admin & filters.command("multi_batch"))
async def multi_batch_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ **Usage:** `/multi_batch <batch_id>`\n\nExample: `/multi_batch naruto_series`", quote=True)
        return

    batch_id = message.command[1].strip().lower()
    await db.create_multi_batch(batch_id)
    await show_admin_batch_menu(client, message.from_user.id, batch_id)


# ==============================================================================
# 2. Admin Callback Query Handler
# ==============================================================================
@Bot.on_callback_query(filters.regex(r"^(add_mrange_|del_mrange_|get_mlink_|ignore)"), group=-1)
async def multi_batch_admin_callbacks(client: Client, query: CallbackQuery):
    data = query.data
    user_id = query.from_user.id

    if data == "ignore":
        await query.answer("यह सिर्फ़ टाइटल बटन है।", show_alert=False)
        return

    await query.answer()

    # --- Naya Episode Range Add karna (+) ---
    if data.startswith("add_mrange_"):
        batch_id = data.replace("add_mrange_", "")

        # Step 1: Button Title
        title_msg = await client.ask(
            chat_id=user_id,
            text="📝 **Enter Button Title:**\n\n(Example: `Ep 1 to 10` ya `Season 1`)",
            timeout=60
        )
        if not title_msg or (title_msg.text and title_msg.text.startswith("/")):
            await query.message.reply("❌ Process Cancelled!")
            return
        btn_title = title_msg.text.strip()

        # Step 2: First Message
        first_message = await client.ask(
            chat_id=user_id,
            text=f"Forward First Message for **'{btn_title}'** or Send Link:",
            timeout=60
        )
        if not first_message or (first_message.text and first_message.text.startswith("/")):
            await query.message.reply("❌ Process Cancelled!")
            return

        f_chat_id, f_msg_id = await get_chat_and_msg_id(client, first_message)
        if not f_chat_id or not f_msg_id:
            await query.message.reply("❌ Invalid Link or Message!")
            return

        if not await is_bot_admin(client, f_chat_id):
            await query.message.reply("⚠️ Bot is not Admin in target channel!")
            return

        # Step 3: Last Message
        second_message = await client.ask(
            chat_id=user_id,
            text=f"Forward Last Message for **'{btn_title}'** or Send Link:",
            timeout=60
        )
        if not second_message or (second_message.text and second_message.text.startswith("/")):
            await query.message.reply("❌ Process Cancelled!")
            return

        s_chat_id, s_msg_id = await get_chat_and_msg_id(client, second_message)
        if not s_chat_id or not s_msg_id or f_chat_id != s_chat_id:
            await query.message.reply("❌ Both messages must be from the same channel!")
            return

        # --- DB Channel Copy Processing (Codexbotz Standard) ---
        db_channel_id = client.db_channel.id
        if f_chat_id != db_channel_id:
            status_msg = await query.message.reply("⏳ Copying messages to DB channel...", quote=True)
            copied_start_id = None
            copied_end_id = None

            for m_id in range(f_msg_id, s_msg_id + 1):
                try:
                    msg = await client.get_messages(f_chat_id, m_id)
                    if msg and not msg.empty:
                        copied = await msg.copy(db_channel_id, disable_notification=True)
                        if copied_start_id is None:
                            copied_start_id = copied.id
                        copied_end_id = copied.id
                        await asyncio.sleep(0.3)
                except Exception:
                    continue

            await status_msg.delete()

            if copied_start_id and copied_end_id:
                f_msg_id = copied_start_id
                s_msg_id = copied_end_id
            else:
                await query.message.reply("❌ Failed to copy messages to DB channel.")
                return

        # 🎯 Codexbotz Exact Formula to create Base64 Hash
        string = f"get-{f_msg_id * abs(db_channel_id)}-{s_msg_id * abs(db_channel_id)}"
        base64_string = await encode(string)

        new_range = {
            "title": btn_title,
            "base64_hash": base64_string  # 👈 Storing Codexbotz standard batch link hash
        }

        await db.add_range_to_multi_batch(batch_id, new_range)
        await show_admin_batch_menu(client, user_id, batch_id)

    # --- Master Link Generation ---
    elif data.startswith("get_mlink_"):
        batch_id = data.replace("get_mlink_", "")
        bot_username = client.username if hasattr(client, "username") else (await client.get_me()).username
        link = f"https://t.me/{bot_username}?start=batch_{batch_id}"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
        await query.message.reply_text(f"✨ **Master Episode Link:**\n\n{link}", reply_markup=reply_markup)

    # --- Delete Range ---
    elif data.startswith("del_mrange_"):
        _, _, batch_id, index = data.split("_")
        index = int(index)
        batch_data = await db.get_multi_batch(batch_id)
        ranges = batch_data.get("ranges", []) if batch_data else []
        if 0 <= index < len(ranges):
            ranges.pop(index)
            await db.update_multi_batch_ranges(batch_id, ranges)
        await show_admin_batch_menu(client, user_id, batch_id, message_to_edit=query.message)
