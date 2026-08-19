# ==============================================================================
# Dynamic Admin Panel & Control Commands
# ==============================================================================

import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import ADMINS, LOG_CHANNEL
from helper_func import admin
from database.database import db

# ==============================================================================
# 🎛️ MAIN ADMIN PANEL COMMAND (/settings ya /panel)
# ==============================================================================
@Bot.on_message(filters.command(['settings', 'panel']) & filters.private & admin)
async def admin_settings_panel(client: Client, message: Message):
    settings = await db.get_bot_settings()
    del_timer = await db.get_del_timer()
    
    verify_mode = settings.get('verify_mode', True)
    verify_status = "🟢 ON (सक्रिय)" if verify_mode else "🔴 OFF (बंद)"
    short_url = settings.get('shortlink_url', 'Not Set')
    tut_vid = settings.get('tut_vid', 'Not Set')
    exp_time = settings.get('verify_expire', 86400) // 3600  # Hours me convert किया गया

    caption = (
        "<b>⚙️ <u>Dynamic Admin Control Panel</u></b>\n\n"
        f"<b>• Verification Status:</b> {verify_status}\n"
        f"<b>• Shortener Domain:</b> <code>{short_url}</code>\n"
        f"<b>• Tutorial Video:</b> <a href='{tut_vid}'>Link Here</a>\n"
        f"<b>• Token Expire Time:</b> {exp_time} घंटे\n"
        f"<b>• File Auto-Delete Time:</b> {del_timer} सेकंड\n\n"
        "<i>नीचे दिए गए बटन का उपयोग करके सेटिंग बदलें 👇</i>"
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"Verify System: {verify_status}", 
                callback_data="toggle_verify_mode"
            )
        ],
        [
            InlineKeyboardButton("🌐 Shortener सेट करें", callback_data="set_shortener_info"),
            InlineKeyboardButton("🎥 Tutorial बदलें", callback_data="set_tutorial_info")
        ],
        [
            InlineKeyboardButton("⏰ Expire Time बदलें", callback_data="set_expire_info"),
            InlineKeyboardButton("🗑 Auto Delete Timer", callback_data="set_del_timer_info")
        ],
        [
            InlineKeyboardButton("❌ Close Panel", callback_data="close")
        ]
    ])

    await message.reply_text(caption, reply_markup=buttons, disable_web_page_preview=True)


# ==============================================================================
# 🔘 TOGGLE VERIFY MODE (ON / OFF) CALLBACK
# ==============================================================================
@Bot.on_callback_query(filters.regex("^toggle_verify_mode$"))
async def toggle_verify_callback(client: Client, callback_query: CallbackQuery):
    if not await db.admin_exist(callback_query.from_user.id) and callback_query.from_user.id not in ADMINS:
        return await callback_query.answer("⛔️ आपके पास इसका अधिकार नहीं है!", show_alert=True)

    settings = await db.get_bot_settings()
    current_mode = settings.get('verify_mode', True)
    new_mode = not current_mode
    
    await db.update_bot_setting('verify_mode', new_mode)
    await callback_query.answer(f"Verification status: {'ON (चालू)' if new_mode else 'OFF (बंद)'}")

    # पैनल रिफ्रेश करें
    del_timer = await db.get_del_timer()
    verify_status = "🟢 ON (सक्रिय)" if new_mode else "🔴 OFF (बंद)"
    short_url = settings.get('shortlink_url', 'Not Set')
    tut_vid = settings.get('tut_vid', 'Not Set')
    exp_time = settings.get('verify_expire', 86400) // 3600

    caption = (
        "<b>⚙️ <u>Dynamic Admin Control Panel</u></b>\n\n"
        f"<b>• Verification Status:</b> {verify_status}\n"
        f"<b>• Shortener Domain:</b> <code>{short_url}</code>\n"
        f"<b>• Tutorial Video:</b> <a href='{tut_vid}'>Link Here</a>\n"
        f"<b>• Token Expire Time:</b> {exp_time} घंटे\n"
        f"<b>• File Auto-Delete Time:</b> {del_timer} सेकंड\n\n"
        "<i>नीचे दिए गए बटन का उपयोग करके सेटिंग बदलें 👇</i>"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Verify System: {verify_status}", callback_data="toggle_verify_mode")],
        [InlineKeyboardButton("🌐 Shortener सेट करें", callback_data="set_shortener_info"),
         InlineKeyboardButton("🎥 Tutorial बदलें", callback_data="set_tutorial_info")],
        [InlineKeyboardButton("⏰ Expire Time बदलें", callback_data="set_expire_info"),
         InlineKeyboardButton("🗑 Auto Delete Timer", callback_data="set_del_timer_info")],
        [InlineKeyboardButton("❌ Close Panel", callback_data="close")]
    ])

    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


# ==============================================================================
# ℹ️ INFORMATION CALLBACKS FOR ADMIN PANEL
# ==============================================================================
@Bot.on_callback_query(filters.regex("^set_shortener_info$"))
async def set_shortener_info(client: Client, callback_query: CallbackQuery):
    await callback_query.answer(
        "Shortener बदलने के लिए कमांड का उपयोग करें:\n\n"
        "/set_shortlink <URL> <API_KEY>\n\n"
        "उदाहरण:\n/set_shortlink mdisklink.link 1234567890abcdef",
        show_alert=True
    )

@Bot.on_callback_query(filters.regex("^set_tutorial_info$"))
async def set_tutorial_info(client: Client, callback_query: CallbackQuery):
    await callback_query.answer(
        "Tutorial Link बदलने के लिए कमांड का उपयोग करें:\n\n"
        "/set_tutorial <Video_URL>\n\n"
        "उदाहरण:\n/set_tutorial https://t.me/HowToOpen/3",
        show_alert=True
    )

@Bot.on_callback_query(filters.regex("^set_expire_info$"))
async def set_expire_info(client: Client, callback_query: CallbackQuery):
    await callback_query.answer(
        "Token Expiry टाइम बदलने के लिए कमांड का उपयोग करें:\n\n"
        "/set_expire <घंटे>\n\n"
        "उदाहरण:\n/set_expire 24",
        show_alert=True
    )

@Bot.on_callback_query(filters.regex("^set_del_timer_info$"))
async def set_del_timer_info(client: Client, callback_query: CallbackQuery):
    await callback_query.answer(
        "Auto Delete टाइम (सेकंड में) बदलने के लिए कमांड का उपयोग करें:\n\n"
        "/dlt_time <सेकंड>\n\n"
        "उदाहरण:\n/dlt_time 600 (10 मिनट के लिए)",
        show_alert=True
    )

@Bot.on_callback_query(filters.regex("^close$"))
async def close_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()


# ==============================================================================
# ✏️ DIRECT COMMANDS FOR SETTINGS UPDATE
# ==============================================================================

# 1. Shortlink URL और API Key बदलने की कमांड
@Bot.on_message(filters.command('set_shortlink') & filters.private & admin)
async def set_shortlink_cmd(client: Client, message: Message):
    if len(message.command) < 3:
        return await message.reply_text("<b>उपयोग का तरीका:</b>\n`/set_shortlink <domain_url> <api_key>`\n\n<b>उदाहरण:</b>\n`/set_shortlink shareus.io 12345678`")
    
    url = message.command[1].strip()
    api = message.command[2].strip()

    await db.update_bot_setting('shortlink_url', url)
    await db.update_bot_setting('shortlink_api', api)

    await message.reply_text(f"✅ <b>Shortlink सफलतापूर्वक अपडेट हो गया!</b>\n\n<b>URL:</b> <code>{url}</code>\n<b>API:</b> <code>{api}</code>")

# 2. Tutorial Video Link बदलने की कमांड
@Bot.on_message(filters.command('set_tutorial') & filters.private & admin)
async def set_tutorial_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("<b>उपयोग का तरीका:</b>\n`/set_tutorial <video_url>`")
    
    tut_url = message.command[1].strip()
    await db.update_bot_setting('tut_vid', tut_url)

    await message.reply_text(f"✅ <b>Tutorial Link अपडेट हो गया!</b>\n\n<b>New URL:</b> {tut_url}")

# 3. Token Expire Time बदलने की कमांड (घंटों में)
@Bot.on_message(filters.command('set_expire') & filters.private & admin)
async def set_expire_cmd(client: Client, message: Message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("<b>उपयोग का तरीका:</b>\n`/set_expire <घंटे>`\n\n<b>उदाहरण:</b>\n`/set_expire 12` (12 घंटे के लिए)")
    
    hours = int(message.command[1])
    expire_seconds = hours * 3600
    
    await db.update_bot_setting('verify_expire', expire_seconds)

    await message.reply_text(f"✅ <b>Token Expiry Time अपडेट हो गया!</b>\n\n<b>नया समय:</b> {hours} घंटे ({expire_seconds} सेकंड)")

# 4. Auto-Delete Time बदलने की कमांड (सेकंड में)
@Bot.on_message(filters.command(['dlt_time', 'set_timer']) & filters.private & admin)
async def set_del_timer_cmd(client: Client, message: Message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("<b>उपयोग का तरीका:</b>\n`/dlt_time <seconds>`\n\n<b>उदाहरण:</b>\n`/dlt_time 600` (10 मिनट)")
    
    seconds = int(message.command[1])
    await db.set_del_timer(seconds)
    await message.reply_text(f"✅ <b>Auto-Delete Timer अपडेट हो गया!</b>\n\n<b>नया समय:</b> `{seconds}` सेकंड")

# 5. वर्तमान Auto-Delete टाइम चेक करने की कमांड
@Bot.on_message(filters.command('check_dlt_time') & filters.private & admin)
async def check_del_timer_cmd(client: Client, message: Message):
    timer = await db.get_del_timer()
    await message.reply_text(f"⏱️ <b>Current Auto-Delete Timer:</b> `{timer}` सेकंड")


# ==============================================================================
# 👤 USER & BAN MANAGEMENT COMMANDS
# ==============================================================================

# Ban User
@Bot.on_message(filters.command('ban') & filters.private & admin)
async def ban_user_cmd(client: Client, message: Message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("<b>उपयोग का तरीका:</b> `/ban <user_id>`")
    
    user_id = int(message.command[1])
    await db.add_ban_user(user_id)
    await message.reply_text(f"🚫 <b>User <code>{user_id}</code> को बैन कर दिया गया है!</b>")

# Unban User
@Bot.on_message(filters.command('unban') & filters.private & admin)
async def unban_user_cmd(client: Client, message: Message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await message.reply_text("<b>उपयोग का तरीका:</b> `/unban <user_id>`")
    
    user_id = int(message.command[1])
    await db.del_ban_user(user_id)
    await message.reply_text(f"✅ <b>User <code>{user_id}</code> को अनबैन कर दिया गया है!</b>")

# Ban List
@Bot.on_message(filters.command('banlist') & filters.private & admin)
async def banlist_cmd(client: Client, message: Message):
    banned = await db.get_ban_users()
    if not banned:
        return await message.reply_text("✅ कोई भी यूजर बैन नहीं है।")
    
    msg = "<b>🚫 Banned Users List:</b>\n\n"
    for user_id in banned:
        msg += f"• <code>{user_id}</code>\n"
    await message.reply_text(msg)
