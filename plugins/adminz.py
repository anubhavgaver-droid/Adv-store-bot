import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ForceReply
from bot import Bot
from config import *
from helper_func import admin
from database.database import db

# ==============================================================================
# 🎛️ MAIN ADMIN PANEL (/settings या /panel)
# ==============================================================================
@Bot.on_message(filters.command(['settings', 'panel']) & filters.private & admin)
async def admin_settings_panel(client: Client, message: Message):
    await send_main_settings_panel(message)


async def send_main_settings_panel(message_or_query):
    caption = (
        "<b>HERE IS THE SETTINGS MENU</b>\n\n"
        "<b>CUSTOMIZE YOUR SETTINGS AS PER YOUR NEED</b>"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 PREMIUM PLAN", callback_data="set_premium_info")],
        [InlineKeyboardButton("🪙 TOKEN VERIFICATION", callback_data="panel_verify")],
        [InlineKeyboardButton("✍️ CUSTOM CAPTION", callback_data="set_caption_info")],
        [InlineKeyboardButton("📢 CUSTOM FORCE SUBSCRIBE", callback_data="set_fsub_info")],
        [InlineKeyboardButton("❌ CLOSE", callback_data="close_panel")]
    ])

    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)
    else:
        await message_or_query.reply_text(caption, reply_markup=buttons, disable_web_page_preview=True)


# ==============================================================================
# 🪙 TOKEN VERIFICATION SUB-MENU
# ==============================================================================
@Bot.on_callback_query(filters.regex("^panel_verify$"))
async def panel_verify(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    verify_mode = settings.get('verify_mode', True)
    
    status_icon = "✅" if verify_mode else "❌"

    caption = "<b>MANAGE YOUR TOKEN VERIFICATION SETTINGS FROM HERE GIVEN BELOW BUTTONS</b>"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚠️ VERIFY SHORTNER", callback_data="panel_shortener")],
        [InlineKeyboardButton("🪪 VERIFY TUTORIAL", callback_data="action_set_tut")],
        [InlineKeyboardButton("⏰ VERIFY TIME", callback_data="action_set_verify_time")],
        [InlineKeyboardButton(f"🟢 VERIFY IS ON - {status_icon}", callback_data="action_toggle_verify")],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")]
    ])
    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


# ==============================================================================
# ⚠️ VERIFY SHORTNER MENU (Token Verification ke andar)
# ==============================================================================
@Bot.on_callback_query(filters.regex("^panel_shortener$"))
async def panel_shortener(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    short_url = settings.get('shortlink_url', SHORTLINK_URL)
    short_api = settings.get('shortlink_api', SHORTLINK_API)

    caption = (
        "<b>HERE YOU CAN MANAGE YOUR BOT VERIFY SHORTLINK</b>\n\n"
        f"<b>URL -</b> {short_url}\n"
        f"<b>API -</b> {short_api}"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("SET SHORTLINK", callback_data="action_set_shortlink"),
            InlineKeyboardButton("DELETE SHORTLINK", callback_data="action_del_shortlink")
        ],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_verify")]
    ])
    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


# ==============================================================================
# 🤖 SHORTLINK INPUT PROCESS (pyromod listen)
# ==============================================================================
@Bot.on_callback_query(filters.regex("^action_set_shortlink$"))
async def action_set_shortlink(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    
    # Step 1: Shortlink Domain URL
    msg1 = await client.send_message(
        chat_id=user_id,
        text=(
            "<b>SEND ME A SHORTLINK URL...</b>\n\n"
            "<b>FORMAT :</b>\n"
            "<code>https://vjlink.online</code> - ❌\n\n"
            "<code>vjlink.online</code> - ✅\n\n"
            "<i>/cancel - CANCEL THIS PROCESS.</i>"
        ),
        reply_markup=ForceReply(selective=True)
    )
    try:
        res1 = await client.listen(chat_id=user_id, timeout=300)
    except Exception:
        return await msg1.edit_text("⏳ Request Timed Out.")

    if res1.text and res1.text.startswith('/cancel'):
        return await res1.reply("❌ Cancelled.")

    new_url = res1.text.strip().replace("https://", "").replace("http://", "").rstrip("/")

    # Step 2: Shortlink API Key
    msg2 = await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME SHORTLINK API...</b>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res2 = await client.listen(chat_id=user_id, timeout=300)
    except Exception:
        return await msg2.edit_text("⏳ Request Timed Out.")

    if res2.text and res2.text.startswith('/cancel'):
        return await res2.reply("❌ Cancelled.")

    new_api = res2.text.strip()

    # Database update
    await db.update_bot_setting('shortlink_url', new_url)
    await db.update_bot_setting('shortlink_api', new_api)

    await res2.reply("✅ **SUCCESSFULLY SET SHORTLINK**")


@Bot.on_callback_query(filters.regex("^action_del_shortlink$"))
async def action_del_shortlink(client: Client, callback_query: CallbackQuery):
    await db.update_bot_setting('shortlink_url', "")
    await db.update_bot_setting('shortlink_api', "")
    await callback_query.answer("🗑 Shortlink deleted!", show_alert=True)
    await panel_shortener(client, callback_query)


# ==============================================================================
# ⚙️ OTHER VERIFICATION ACTIONS
# ==============================================================================
@Bot.on_callback_query(filters.regex("^action_toggle_verify$"))
async def action_toggle_verify(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    current_status = settings.get('verify_mode', True)
    await db.update_bot_setting('verify_mode', not current_status)
    await callback_query.answer(f"Verification turned {'OFF' if current_status else 'ON'}")
    await panel_verify(client, callback_query)


@Bot.on_callback_query(filters.regex("^action_set_tut$"))
async def action_set_tut(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await client.send_message(
        chat_id=callback_query.from_user.id,
        text="<b>SEND ME NEW TUTORIAL VIDEO URL...</b>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=callback_query.from_user.id, timeout=300)
        if res.text and not res.text.startswith('/cancel'):
            await db.update_bot_setting('tut_vid', res.text.strip())
            await res.reply("✅ **TUTORIAL LINK UPDATED SUCCESSFULLY!**")
    except Exception:
        pass


@Bot.on_callback_query(filters.regex("^action_set_verify_time$"))
async def action_set_verify_time(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await client.send_message(
        chat_id=callback_query.from_user.id,
        text="<b>SEND ME TOKEN EXPIRE TIME IN SECONDS...</b>\n\n<i>Example: 3600 (1 Hour), 86400 (24 Hours)</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=callback_query.from_user.id, timeout=300)
        if res.text and res.text.isdigit():
            await db.update_bot_setting('verify_expire', int(res.text.strip()))
            await res.reply("✅ **VERIFICATION TIME UPDATED!**")
    except Exception:
        pass


# ==============================================================================
# 🔄 NAVIGATION & CLOSE
# ==============================================================================
@Bot.on_callback_query(filters.regex("^panel_main$"))
async def panel_main(client: Client, callback_query: CallbackQuery):
    await send_main_settings_panel(callback_query)

@Bot.on_callback_query(filters.regex("^close_panel$"))
async def close_panel(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()

@Bot.on_callback_query(filters.regex("^(set_premium_info|set_caption_info|set_fsub_info)$"))
async def placeholder_info(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("Feature Active", show_alert=True)
