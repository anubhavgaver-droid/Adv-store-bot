import asyncio
from pyrogram import Client, filters, enums
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
        [InlineKeyboardButton("💎 PREMIUM PLAN", callback_data="panel_premium")],
        [InlineKeyboardButton("🪙 TOKEN VERIFICATION", callback_data="panel_verify")],
        [InlineKeyboardButton("✍️ CUSTOM CAPTION", callback_data="panel_caption")],
        [InlineKeyboardButton("📢 CUSTOM FORCE SUBSCRIBE", callback_data="panel_fsub")],
        [InlineKeyboardButton("❌ CLOSE", callback_data="close_panel")]
    ])

    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)
    else:
        await message_or_query.reply_text(caption, reply_markup=buttons, disable_web_page_preview=True)


# ==============================================================================
# 📢 FORCE SUBSCRIBE SETTINGS (NORMAL + REQUEST MODE)
# ==============================================================================
@Bot.on_callback_query(filters.regex("^panel_fsub$"))
async def panel_fsub(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    fsub_mode = settings.get('fsub_mode', 'NORMAL')  # Default Mode: NORMAL

    channels = await db.show_channels()
    
    chnl_text = ""
    if channels:
        for index, ch_id in enumerate(channels, start=1):
            chnl_text += f"{index}. <code>{ch_id}</code>\n"
    else:
        chnl_text = "<i>No channels added yet.</i>"

    mode_display = "📩 JOIN REQUEST" if fsub_mode == "REQUEST" else "🔗 NORMAL JOIN"

    caption = (
        "<b>📢 FORCE SUBSCRIBE MANAGEMENT</b>\n\n"
        f"<b>CURRENT FSUB MODE:</b> <code>{mode_display}</code>\n\n"
        f"<b>ADDED CHANNELS:</b>\n{chnl_text}"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔄 MODE: {mode_display}", callback_data="action_toggle_fsub_mode")],
        [
            InlineKeyboardButton("➕ ADD CHANNEL", callback_data="action_add_fsub"),
            InlineKeyboardButton("➖ REMOVE CHANNEL", callback_data="action_rem_fsub")
        ],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")]
    ])
    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_toggle_fsub_mode$"))
async def action_toggle_fsub_mode(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    current_mode = settings.get('fsub_mode', 'NORMAL')
    
    # Toggle Mode between NORMAL and REQUEST
    new_mode = "REQUEST" if current_mode == "NORMAL" else "NORMAL"
    await db.update_bot_setting('fsub_mode', new_mode)
    
    await callback_query.answer(f"Switched Force Sub Mode to: {new_mode}", show_alert=True)
    await panel_fsub(client, callback_query)


@Bot.on_callback_query(filters.regex("^action_add_fsub$"))
async def action_add_fsub(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id

    msg = await client.send_message(
        chat_id=user_id,
        text="<b>SEND CHANNEL ID TO ADD IN FORCE SUB...</b>\n\n<i>Example: -1001234567890</i>\n\n<i>/cancel - CANCEL PROCESS</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if res.text and not res.text.startswith('/cancel'):
            try:
                ch_id = int(res.text.strip())
                await db.add_channel(ch_id)
                await res.reply("✅ **CHANNEL ADDED TO FORCE SUB!**")
            except ValueError:
                await res.reply("❌ **Invalid Channel ID format!**")
    except Exception:
        pass


@Bot.on_callback_query(filters.regex("^action_rem_fsub$"))
async def action_rem_fsub(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id

    msg = await client.send_message(
        chat_id=user_id,
        text="<b>SEND CHANNEL ID TO REMOVE FROM FORCE SUB...</b>\n\n<i>/cancel - CANCEL PROCESS</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if res.text and not res.text.startswith('/cancel'):
            try:
                ch_id = int(res.text.strip())
                await db.rem_channel(ch_id)
                await res.reply("✅ **CHANNEL REMOVED FROM FORCE SUB!**")
            except ValueError:
                await res.reply("❌ **Invalid Channel ID format!**")
    except Exception:
        pass


# ==============================================================================
# 💎 PREMIUM PLAN SETTINGS
# ==============================================================================
@Bot.on_callback_query(filters.regex("^panel_premium$"))
async def panel_premium(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    upi_id = settings.get('upi_id', UPI_ID)
    qr_pic = settings.get('qr_pic', QR_PIC)

    caption = (
        "<b>💎 PREMIUM PLAN CONFIGURATION</b>\n\n"
        f"<b>• UPI ID:</b> <code>{upi_id}</code>\n"
        f"<b>• QR PIC LINK:</b> {qr_pic}"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 SET UPI ID", callback_data="action_set_upi"),
            InlineKeyboardButton("🖼️ SET QR PIC", callback_data="action_set_qr")
        ],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")]
    ])
    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_set_upi$"))
async def action_set_upi(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW UPI ID...</b>\n\n<i>/cancel - CANCEL PROCESS</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if res.text and not res.text.startswith('/cancel'):
            await db.update_bot_setting('upi_id', res.text.strip())
            await res.reply("✅ **UPI ID UPDATED!**")
    except Exception:
        pass


@Bot.on_callback_query(filters.regex("^action_set_qr$"))
async def action_set_qr(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW QR IMAGE URL...</b>\n\n<i>/cancel - CANCEL PROCESS</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if res.text and not res.text.startswith('/cancel'):
            await db.update_bot_setting('qr_pic', res.text.strip())
            await res.reply("✅ **QR PIC UPDATED!**")
    except Exception:
        pass


# ==============================================================================
# 🪙 TOKEN VERIFICATION SETTINGS
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


@Bot.on_callback_query(filters.regex("^action_set_shortlink$"))
async def action_set_shortlink(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    
    msg1 = await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME A SHORTLINK URL...</b>\n\n<b>FORMAT :</b>\n<code>vjlink.online</code> - ✅\n\n<i>/cancel - CANCEL PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res1 = await client.listen(chat_id=user_id, timeout=300)
    except Exception:
        return await msg1.edit_text("⏳ Request Timed Out.")

    if res1.text and res1.text.startswith('/cancel'):
        return await res1.reply("❌ Cancelled.")

    new_url = res1.text.strip().replace("https://", "").replace("http://", "").rstrip("/")

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

    await db.update_bot_setting('shortlink_url', new_url)
    await db.update_bot_setting('shortlink_api', new_api)
    await res2.reply("✅ **SUCCESSFULLY SET SHORTLINK**")


@Bot.on_callback_query(filters.regex("^action_del_shortlink$"))
async def action_del_shortlink(client: Client, callback_query: CallbackQuery):
    await db.update_bot_setting('shortlink_url', "")
    await db.update_bot_setting('shortlink_api', "")
    await callback_query.answer("🗑 Shortlink deleted!", show_alert=True)
    await panel_shortener(client, callback_query)


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
    user_id = callback_query.from_user.id
    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW TUTORIAL VIDEO URL...</b>\n\n<i>/cancel - CANCEL PROCESS</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if res.text and not res.text.startswith('/cancel'):
            await db.update_bot_setting('tut_vid', res.text.strip())
            await res.reply("✅ **TUTORIAL LINK UPDATED!**")
    except Exception:
        pass


@Bot.on_callback_query(filters.regex("^action_set_verify_time$"))
async def action_set_verify_time(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME TOKEN EXPIRE TIME IN SECONDS...</b>\n\n<i>Example: 3600 (1 Hour), 86400 (24 Hours)</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if res.text and res.text.isdigit():
            await db.update_bot_setting('verify_expire', int(res.text.strip()))
            await res.reply("✅ **VERIFICATION TIME UPDATED!**")
    except Exception:
        pass


# ==============================================================================
# ✍️ CUSTOM CAPTION SETTINGS
# ==============================================================================
@Bot.on_callback_query(filters.regex("^panel_caption$"))
async def panel_caption(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    current_cap = settings.get('custom_caption', CUSTOM_CAPTION)

    caption = (
        "<b>✍️ CUSTOM CAPTION SETTINGS</b>\n\n"
        f"<b>CURRENT CAPTION:</b>\n<code>{current_cap if current_cap else 'Disabled'}</code>"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ SET CAPTION", callback_data="action_set_caption"),
            InlineKeyboardButton("🗑️ DELETE CAPTION", callback_data="action_del_caption")
        ],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")]
    ])
    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_set_caption$"))
async def action_set_caption(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id

    msg = await client.send_message(
        chat_id=user_id,
        text=(
            "<b>SEND ME NEW CUSTOM CAPTION...</b>\n\n"
            "<b>Available Fillings:</b>\n"
            "• <code>{filename}</code> - File Name\n"
            "• <code>{previouscaption}</code> - Original Caption\n\n"
            "<i>/cancel - CANCEL PROCESS</i>"
        ),
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if res.text and not res.text.startswith('/cancel'):
            await db.update_bot_setting('custom_caption', res.text.html)
            await res.reply("✅ **CUSTOM CAPTION UPDATED!**")
    except Exception:
        pass


@Bot.on_callback_query(filters.regex("^action_del_caption$"))
async def action_del_caption(client: Client, callback_query: CallbackQuery):
    await db.update_bot_setting('custom_caption', "")
    await callback_query.answer("🗑 Caption cleared!", show_alert=True)
    await panel_caption(client, callback_query)


# ==============================================================================
# 🔄 GLOBAL NAVIGATION & CLOSE
# ==============================================================================
@Bot.on_callback_query(filters.regex("^panel_main$"))
async def panel_main(client: Client, callback_query: CallbackQuery):
    await send_main_settings_panel(callback_query)

@Bot.on_callback_query(filters.regex("^close_panel$"))
async def close_panel(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
