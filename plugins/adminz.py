import io
import asyncio
from datetime import datetime
from pytz import timezone
from pyrogram import Client, filters, enums
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, ForceReply, ChatMemberUpdated, ChatJoinRequest
)
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from bot import Bot
from config import *
from helper_func import admin
from database.database import db
from database.db_premium import add_premium, remove_premium, collection

# ==============================================================================
# 📩 JOIN REQUEST & CHAT MEMBER LISTENERS (BACKGROUND HANDLERS)
# ==============================================================================

@Bot.on_chat_join_request()
async def handle_join_request(client: Client, chat_join_request: ChatJoinRequest):
    chat_id = chat_join_request.chat.id
    user_id = chat_join_request.from_user.id

    if await db.reqChannel_exist(chat_id):
        if not await db.req_user_exist(chat_id, user_id):
            await db.req_user(chat_id, user_id)


@Bot.on_chat_member_updated()
async def handle_Chatmembers(client: Client, chat_member_updated: ChatMemberUpdated):    
    chat_id = chat_member_updated.chat.id

    if await db.reqChannel_exist(chat_id):
        old_member = chat_member_updated.old_chat_member
        if not old_member:
            return

        if old_member.status == ChatMemberStatus.MEMBER:
            user_id = old_member.user.id
            if await db.req_user_exist(chat_id, user_id):
                await db.del_req_user(chat_id, user_id)


# ==============================================================================
# 🎛️ MAIN ADMIN PANEL & SETTINGS BUTTON TRIGGER
# ==============================================================================

@Bot.on_message(filters.command(['settings', 'panel']) & filters.private & admin)
async def admin_settings_panel(client: Client, message: Message):
    await send_main_settings_panel(message)


@Bot.on_callback_query(filters.regex("^cb_settings$"))
async def cb_settings_handler(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    if user_id not in ADMINS:
        return await callback_query.answer("⚠️ This is only for Admin ⚠️", show_alert=True)
    
    await send_main_settings_panel(callback_query)


async def send_main_settings_panel(message_or_query):
    caption = "<b>HERE IS THE SETTINGS MENU</b>\n\n<b>CUSTOMIZE YOUR SETTINGS AS PER YOUR NEED</b>"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 START SETTINGS", callback_data="panel_start_settings")],
        [InlineKeyboardButton("💎 PREMIUM PLAN", callback_data="panel_premium")],
        [InlineKeyboardButton("🪙 TOKEN VERIFICATION", callback_data="panel_verify")],
        [InlineKeyboardButton("✍️ CUSTOM CAPTION", callback_data="panel_caption")],
        [InlineKeyboardButton("📢 FORCE SUBSCRIBE PANEL", callback_data="panel_fsub")],
        [InlineKeyboardButton("🛡️ PROTECT CONTENT", callback_data="panel_protect")],
        [
            InlineKeyboardButton("ᐸ BACK", callback_data="start"),
            InlineKeyboardButton("❌ CLOSE", callback_data="close_panel")
        ]
    ])
    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)
    else:
        await message_or_query.reply_text(caption, reply_markup=buttons, disable_web_page_preview=True)


# ==============================================================================
# 🛡️ PROTECT CONTENT MANAGEMENT
# ==============================================================================

@Bot.on_callback_query(filters.regex("^panel_protect$"))
async def panel_protect(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    is_protect = settings.get('protect_content', False)
    status_str = "🟢 ENABLED (FORWARDING OFF)" if is_protect else "🔴 DISABLED (FORWARDING ON)"

    caption = (
        "<b>🛡️ PROTECT CONTENT SETTINGS</b>\n\n"
        "<i>Enable or disable content protection. When enabled, users cannot forward or save files sent by the bot.</i>\n\n"
        f"<b>• Current Status:</b> <code>{status_str}</code>"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🛡️ PROTECT: {'ON ✅' if is_protect else 'OFF ❌'}", callback_data="action_toggle_protect")],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")]
    ])

    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_toggle_protect$"))
async def action_toggle_protect(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    current_status = settings.get('protect_content', False)
    new_status = not current_status

    await db.update_bot_setting('protect_content', new_status)
    status_text = "🟢 Protect Content Enabled!" if new_status else "🔴 Protect Content Disabled!"
    await callback_query.answer(status_text, show_alert=True)
    await panel_protect(client, callback_query)


# ==============================================================================
# 🚀 START MESSAGE, PIC & SPOILER (BLUR) MANAGEMENT
# ==============================================================================

@Bot.on_callback_query(filters.regex("^panel_start_settings$"))
async def panel_start_settings(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    start_msg = settings.get('start_msg', START_MSG)
    start_pic = settings.get('start_pic', START_PIC)
    is_spoiler = settings.get('start_pic_spoiler', False)

    spoiler_status = "🟢 BLUR / SPOILER ON" if is_spoiler else "🔴 BLUR / SPOILER OFF"

    caption = (
        "<b>🚀 START SETTINGS MANAGEMENT</b>\n\n"
        f"<b>• Start Pic Link:</b> {start_pic if start_pic else '❌ NOT SET'}\n"
        f"<b>• Blur (Spoiler) Mode:</b> <code>{spoiler_status}</code>\n\n"
        f"<b>• Current Start Text:</b>\n<code>{start_msg if start_msg else '❌ NOT SET (DEFAULT WILL BE USED)'}</code>"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ SET START MSG", callback_data="action_set_start_msg"), InlineKeyboardButton("🗑️ DEL MSG", callback_data="action_del_start_msg")],
        [InlineKeyboardButton("🖼️ SET START PIC", callback_data="action_set_start_pic"), InlineKeyboardButton("🗑️ DEL PIC", callback_data="action_del_start_pic")],
        [InlineKeyboardButton(f"👁️ {spoiler_status}", callback_data="action_toggle_spoiler")],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")]
    ])

    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_toggle_spoiler$"))
async def action_toggle_spoiler(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    current_status = settings.get('start_pic_spoiler', False)
    new_status = not current_status
    
    await db.update_bot_setting('start_pic_spoiler', new_status)
    status_text = "🟢 Pic Blur (Spoiler) Turned ON!" if new_status else "🔴 Pic Blur Turned OFF!"
    await callback_query.answer(status_text, show_alert=True)
    await panel_start_settings(client, callback_query)


@Bot.on_callback_query(filters.regex("^action_set_start_msg$"))
async def action_set_start_msg(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_start_settings")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW START MESSAGE...</b>\n\n<b>Available tags:</b>\n• <code>{mention}</code>\n• <code>{first}</code>\n• <code>{id}</code>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        new_text = res.text.html if hasattr(res.text, 'html') else res.text
        await db.update_bot_setting('start_msg', new_text)
        await res.reply("✅ <b>START MESSAGE UPDATED SUCCESSFULLY!</b>", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_del_start_msg$"))
async def action_del_start_msg(client: Client, callback_query: CallbackQuery):
    await db.update_bot_setting('start_msg', None)
    await callback_query.answer("🗑️ Start Message Deleted!", show_alert=True)
    await panel_start_settings(client, callback_query)


@Bot.on_callback_query(filters.regex("^action_set_start_pic$"))
async def action_set_start_pic(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_start_settings")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW START PHOTO URL...</b>\n\n<i>Example: https://telegra.ph/file/xxx.jpg</i>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        await db.update_bot_setting('start_pic', res.text.strip())
        await res.reply("✅ <b>START PIC UPDATED SUCCESSFULLY!</b>", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_del_start_pic$"))
async def action_del_start_pic(client: Client, callback_query: CallbackQuery):
    await db.update_bot_setting('start_pic', None)
    await callback_query.answer("🗑️ Start Photo Deleted!", show_alert=True)
    await panel_start_settings(client, callback_query)


# ==============================================================================
# 📢 FORCE SUBSCRIBE MANAGEMENT (DYNAMIC BUTTONS & MODE TOGGLE)
# ==============================================================================

@Bot.on_callback_query(filters.regex("^panel_fsub$"))
async def panel_fsub(client: Client, callback_query: CallbackQuery):
    channels = await db.show_channels()
    buttons = []

    if channels:
        for ch_id in channels:
            try:
                chat = await client.get_chat(ch_id)
                mode = await db.get_channel_mode(ch_id)
                status = "🟢 REQ" if mode == "on" else "🔴 NORMAL"
                title = f"{chat.title}"
            except Exception:
                status = "⚠️ UNKNOWN"
                title = f"ID: {ch_id}"
            
            buttons.append([
                InlineKeyboardButton(f"{status} | {title}", callback_data=f"toggle_rfs_{ch_id}"),
                InlineKeyboardButton("❌", callback_data=f"rem_ch_{ch_id}")
            ])

    buttons.append([InlineKeyboardButton("➕ ADD CHANNEL", callback_data="action_add_fsub")])
    buttons.append([InlineKeyboardButton("🧹 CLEANUP REQUESTS", callback_data="action_clean_req_menu")])
    buttons.append([InlineKeyboardButton("🗑️ DELETE ALL CHANNELS", callback_data="action_del_all_fsub")])
    buttons.append([InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")])

    caption = (
        "<b>📢 FORCE SUBSCRIBE MANAGEMENT PANEL</b>\n\n"
        f"<b>TOTAL CHANNELS:</b> <code>{len(channels)}</code>\n\n"
        "<b>• Mode Status:</b>\n"
        "🟢 REQ = Join Request Force Sub ON\n"
        "🔴 NORMAL = Direct Join Link ON\n\n"
        "<i>किसी भी चैनल के मोड को बदलने या हटाने के लिए बटन पर क्लिक करें।</i>"
    )

    await callback_query.message.edit_text(caption, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex(r"^toggle_rfs_"))
async def toggle_rfs_mode_callback(client: Client, callback_query: CallbackQuery):
    ch_id = int(callback_query.data.split("_")[2])
    current_mode = await db.get_channel_mode(ch_id)
    new_mode = "off" if current_mode == "on" else "on"
    
    await db.set_channel_mode(ch_id, new_mode)
    status_msg = "🟢 Request Mode Turned ON" if new_mode == "on" else "🔴 Normal Join Mode Turned ON"
    await callback_query.answer(status_msg, show_alert=True)
    await panel_fsub(client, callback_query)


@Bot.on_callback_query(filters.regex(r"^rem_ch_"))
async def handle_dynamic_rem_channel(client: Client, callback_query: CallbackQuery):
    ch_id = int(callback_query.data.split("_")[2])
    await db.rem_channel(ch_id)
    await callback_query.answer("✅ Channel Removed!", show_alert=True)
    await panel_fsub(client, callback_query)


@Bot.on_callback_query(filters.regex("^action_add_fsub$"))
async def action_add_fsub(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_fsub")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND CHANNEL ID OR USERNAME...</b>\n\n<i>Example: -1001234567890 or @MyChannel</i>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        input_text = res.text.strip()
        ch_id = int(input_text) if input_text.lstrip('-').isdigit() else input_text

        try:
            chat = await client.get_chat(ch_id)
            if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
                return await res.reply("❌ **Only Channels or Supergroups allowed.**", reply_markup=back_btn)

            bot_member = await client.get_chat_member(chat.id, "me")
            if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await res.reply("❌ **Bot must be Admin in that Channel.**", reply_markup=back_btn)

            try:
                link_obj = await client.create_chat_invite_link(chat.id, creates_join_request=True)
                invite_link = link_obj.invite_link
            except Exception:
                try:
                    invite_link = await client.export_chat_invite_link(chat.id)
                except Exception:
                    invite_link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}"

            await db.add_channel(chat.id)
            await res.reply(
                f"✅ **CHANNEL ADDED SUCCESSFULLY!**\n\n"
                f"<b>Title:</b> <a href='{invite_link}'>{chat.title}</a>\n"
                f"<b>ID:</b> <code>{chat.id}</code>",
                disable_web_page_preview=True,
                reply_markup=back_btn
            )
        except Exception as e:
            await res.reply(f"❌ **Failed to Add Chat:**\n<code>{e}</code>", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_del_all_fsub$"))
async def action_del_all_fsub(client: Client, callback_query: CallbackQuery):
    all_channels = await db.show_channels()
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_fsub")]])

    if not all_channels:
        return await callback_query.answer("❌ No Force-Sub Channels found!", show_alert=True)

    for ch_id in all_channels:
        await db.rem_channel(ch_id)

    await callback_query.message.edit_text("✅ **ALL FORCE-SUB CHANNELS HAVE BEEN REMOVED.**", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_clean_req_menu$"))
async def action_clean_req_menu(client: Client, callback_query: CallbackQuery):
    channels = await db.show_channels()
    buttons = []

    if channels:
        for ch_id in channels:
            buttons.append([InlineKeyboardButton(f"🧹 Clean ID: {ch_id}", callback_data=f"run_clean_req_{ch_id}")])

    buttons.append([InlineKeyboardButton("ᐸ BACK", callback_data="panel_fsub")])
    await callback_query.message.edit_text(
        "<b>🧹 SELECT CHANNEL TO CLEAN LEFT/NON-REQUEST USERS:</b>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Bot.on_callback_query(filters.regex(r"^run_clean_req_"))
async def run_clean_req_callback(client: Client, callback_query: CallbackQuery):
    channel_id = int(callback_query.data.split("_")[3])
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_fsub")]])

    await callback_query.message.edit_text("⏳ **Cleaning up request list... Please wait.**")

    channel_data = await db.rqst_fsub_Channel_data.find_one({'_id': channel_id})
    if not channel_data:
        return await callback_query.message.edit_text("ℹ️ **No request data found for this channel.**", reply_markup=back_btn)

    user_ids = channel_data.get("user_ids", [])
    if not user_ids:
        return await callback_query.message.edit_text("✅ **No users to process.**", reply_markup=back_btn)

    skipped = 0
    left_users = 0

    for u_id in user_ids:
        try:
            member = await client.get_chat_member(channel_id, u_id)
            if member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                skipped += 1
            else:
                await db.del_req_user(channel_id, u_id)
                left_users += 1
        except UserNotParticipant:
            await db.del_req_user(channel_id, u_id)
            left_users += 1
        except Exception:
            skipped += 1

    await callback_query.message.edit_text(
        f"✅ **Cleanup completed for Channel:** <code>{channel_id}</code>\n\n"
        f"👤 **Removed non-members:** <code>{left_users}</code>\n"
        f"✅ **Active Members retained:** <code>{skipped}</code>",
        reply_markup=back_btn
    )


# ==============================================================================
# 💎 PREMIUM PLAN MANAGEMENT & SETTINGS
# ==============================================================================

@Bot.on_callback_query(filters.regex("^panel_premium$"))
async def panel_premium(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    is_premium_on = settings.get('premium_mode', True)
    upi_id = settings.get('upi_id', UPI_ID)
    qr_pic = settings.get('qr_pic', QR_PIC)
    
    status_btn = (
        InlineKeyboardButton("🟢 PREMIUM IS ON - ✅", callback_data="action_toggle_premium")
        if is_premium_on else 
        InlineKeyboardButton("🔴 PREMIUM IS OFF - ❌", callback_data="action_toggle_premium")
    )

    caption = (
        "<b>💎 PREMIUM PLAN CONFIGURATION PANEL</b>\n\n"
        f"<b>• UPI ID:</b> <code>{upi_id}</code>\n"
        f"<b>• QR PIC LINK:</b> {qr_pic}\n\n"
        "<i>MANAGE PREMIUM USERS, PLAN TEXT, AND PAYMENT DETAILS HERE.</i>"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 PREMIUM PLAN TEXT", callback_data="panel_premium_text")],
        [InlineKeyboardButton("➕ ADD PREMIUM USER", callback_data="action_add_premium")],
        [InlineKeyboardButton("➖ REMOVE PREMIUM USER", callback_data="action_remove_premium")],
        [InlineKeyboardButton("📊 PREMIUM USERS LIST", callback_data="action_premium_list")],
        [InlineKeyboardButton("💳 SET UPI ID", callback_data="action_set_upi"), InlineKeyboardButton("🖼️ SET QR PIC", callback_data="action_set_qr")],
        [status_btn],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")]
    ])

    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_toggle_premium$"))
async def action_toggle_premium(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    current_status = settings.get('premium_mode', True)
    new_status = not current_status
    
    await db.update_bot_setting('premium_mode', new_status)
    status_text = "🟢 Premium Enabled!" if new_status else "🔴 Premium Disabled!"
    await callback_query.answer(status_text, show_alert=True)
    await panel_premium(client, callback_query)


@Bot.on_callback_query(filters.regex("^panel_premium_text$"))
async def panel_premium_text(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    plan_text = settings.get('premium_plan_text', None)

    default_text = (
        "<b><u>🎁 PREMIUM PLANS</u></b>\n\n"
        "<b>1. 15₹ = 7 DAY</b>\n"
        "<b>2. 49₹ = 1 MONTH</b>\n"
        "<b>3. 120₹ = 3 MONTH</b>\n"
        "<b>4. 220₹ = 6 MONTH</b>\n\n"
        "<b>🎁 PREMIUM FEATURES:</b>\n"
        "<b>◯ GET UNLIMITED FILES</b>\n"
        "<b>◯ NO NEED VERIFY</b>\n"
        "<b>◯ DIRECT FILES</b>\n\n"
        "<b>‼️ MUST SEND SCREENSHOT AFTER PAYMENT</b>"
    )

    display_text = plan_text if plan_text else default_text

    caption = (
        f"<b>HERE YOU CAN MANAGE YOUR PREMIUM PLAN TEXT HERE</b>\n\n"
        f"{display_text}"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("SET PREMIUM PLAN TEXT", callback_data="action_set_plan_text")],
        [InlineKeyboardButton("DELETE PREMIUM PLAN TEXT", callback_data="action_del_plan_text")],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_premium")]
    ])

    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_set_plan_text$"))
async def action_set_plan_text(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_premium_text")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW PREMIUM PLAN TEXT...</b>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)
            
        new_text = res.text.html if hasattr(res.text, 'html') else res.text
        await db.update_bot_setting('premium_plan_text', new_text)
        await res.reply("✅ <b>PREMIUM PLAN TEXT UPDATED SUCCESSFULLY!</b>", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_del_plan_text$"))
async def action_del_plan_text(client: Client, callback_query: CallbackQuery):
    await db.update_bot_setting('premium_plan_text', "")
    await callback_query.answer("🗑 Premium Plan Text Deleted!", show_alert=True)
    await panel_premium_text(client, callback_query)


@Bot.on_callback_query(filters.regex("^action_add_premium$"))
async def action_add_premium(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_premium")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>NOW SEND ME USER ID</b>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        target_id = int(res.text.strip())

        await client.send_message(
            chat_id=user_id,
            text=(
                "<b>SEND DURATION AND UNIT</b>\n\n"
                "<b>Example Formats:</b>\n"
                "• <code>30 d</code> (30 Days)\n"
                "• <code>2 h</code> (2 Hours)\n"
                "• <code>1 y</code> (1 Year)\n\n"
                "<i>Units: s = seconds, m = minutes, h = hours, d = days, y = years</i>\n\n"
                "<i>/cancel - CANCEL THIS PROCESS.</i>"
            ),
            reply_markup=ForceReply(selective=True)
        )
        res_time = await client.listen(chat_id=user_id, timeout=300)
        if not res_time.text or res_time.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        time_parts = res_time.text.strip().split()
        time_value = int(time_parts[0])
        time_unit = time_parts[1].lower() if len(time_parts) > 1 else 'd'

        expiration_time = await add_premium(target_id, time_value, time_unit)

        await res_time.reply(
            f"✅ <b>USER <code>{target_id}</code> ADDED TO PREMIUM!</b>\n\n"
            f"<b>Duration:</b> <code>{time_value} {time_unit}</code>\n"
            f"<b>Expires On:</b> <code>{expiration_time}</code>",
            reply_markup=back_btn
        )

        try:
            await client.send_message(
                chat_id=target_id,
                text=(
                    f"🎉 <b>PREMIUM ACTIVATED!</b>\n\n"
                    f"You have received premium access for <code>{time_value} {time_unit}</code>.\n"
                    f"<b>Expires On:</b> <code>{expiration_time}</code>"
                )
            )
        except Exception:
            pass

    except ValueError:
        await client.send_message(chat_id=user_id, text="❌ <b>INVALID INPUT FORMAT!</b>", reply_markup=back_btn)
    except Exception as e:
        await client.send_message(chat_id=user_id, text=f"❌ <b>ERROR:</b> <code>{e}</code>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_remove_premium$"))
async def action_remove_premium(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_premium")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>NOW SEND ME USER ID</b>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        target_id = int(res.text.strip())
        await remove_premium(target_id)

        await res.reply(f"✅ <b>USER <code>{target_id}</code> REMOVED FROM PREMIUM LIST!</b>", reply_markup=back_btn)
    except ValueError:
        await client.send_message(chat_id=user_id, text="❌ <b>INVALID USER ID!</b>", reply_markup=back_btn)
    except Exception as e:
        await client.send_message(chat_id=user_id, text=f"❌ <b>ERROR:</b> <code>{e}</code>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_premium_list$"))
async def action_premium_list(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("SENDING PREMIUM USERS LIST FILE IN SOME SECONDS", show_alert=True)
    
    close_btn = InlineKeyboardMarkup([[InlineKeyboardButton("❌ CLOSE", callback_data="close_panel")]])
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_premium")]])

    ist = timezone("Asia/Kolkata")
    current_time = datetime.now(ist)
    premium_user_list = ["📊 --- ACTIVE PREMIUM USERS LIST ---\n"]
    count = 0

    try:
        premium_users_cursor = collection.find({})
        async for user in premium_users_cursor:
            u_id = user.get("user_id")
            expiration_timestamp = user.get("expiration_timestamp")

            if not u_id or not expiration_timestamp:
                continue

            try:
                expiration_time = datetime.fromisoformat(expiration_timestamp).astimezone(ist)
                remaining_time = expiration_time - current_time

                if remaining_time.total_seconds() <= 0:
                    await collection.delete_one({"user_id": u_id})
                    continue  

                count += 1
                days, hours, minutes, seconds = (
                    remaining_time.days,
                    remaining_time.seconds // 3600,
                    (remaining_time.seconds // 60) % 60,
                    remaining_time.seconds % 60,
                )
                expiry_info = f"{days}d {hours}h {minutes}m {seconds}s left"

                try:
                    user_info = await client.get_users(u_id)
                    username = f"@{user_info.username}" if user_info.username else "No Username"
                    name = user_info.first_name
                except Exception:
                    username = "Unknown"
                    name = "Unknown"

                premium_user_list.append(
                    f"{count}. UserID: {u_id}\n"
                    f"   Name: {name}\n"
                    f"   Username: {username}\n"
                    f"   Expiry: {expiry_info}\n"
                )
            except Exception:
                pass

        if count == 0:
            return await callback_query.message.edit_text("ℹ️ <b>NO ACTIVE PREMIUM USERS FOUND IN DATABASE.</b>", reply_markup=back_btn)

        text_data = "\n".join(premium_user_list)
        file = io.BytesIO(text_data.encode('utf-8'))
        file.name = "premium_users.txt"
        
        await client.send_document(
            chat_id=callback_query.from_user.id,
            document=file,
            caption=f"<b>📊 TOTAL ACTIVE PREMIUM USERS:</b> <code>{count}</code>",
            reply_markup=close_btn
        )

    except Exception as e:
        await callback_query.message.edit_text(f"❌ <b>Error fetching list:</b> <code>{e}</code>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_set_upi$"))
async def action_set_upi(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_premium")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW UPI ID...</b>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        await db.update_bot_setting('upi_id', res.text.strip())
        await res.reply("✅ **UPI ID UPDATED!**", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_set_qr$"))
async def action_set_qr(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_premium")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW QR IMAGE URL...</b>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        await db.update_bot_setting('qr_pic', res.text.strip())
        await res.reply("✅ **QR PIC UPDATED!**", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


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

    caption = f"<b>HERE YOU CAN MANAGE YOUR BOT VERIFY SHORTLINK</b>\n\n<b>URL -</b> {short_url}\n<b>API -</b> {short_api}"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("SET SHORTLINK", callback_data="action_set_shortlink"), InlineKeyboardButton("DELETE SHORTLINK", callback_data="action_del_shortlink")],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_verify")]
    ])
    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_set_shortlink$"))
async def action_set_shortlink(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_shortener")]])

    msg1 = await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME A SHORTLINK URL...</b>\n\n<b>FORMAT:</b> <code>vjlink.online</code>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res1 = await client.listen(chat_id=user_id, timeout=300)
        if not res1.text or res1.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        new_url = res1.text.strip().replace("https://", "").replace("http://", "").rstrip("/")

        msg2 = await client.send_message(
            chat_id=user_id,
            text="<b>SEND ME SHORTLINK API...</b>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
            reply_markup=ForceReply(selective=True)
        )
        res2 = await client.listen(chat_id=user_id, timeout=300)
        if not res2.text or res2.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        await db.update_bot_setting('shortlink_url', new_url)
        await db.update_bot_setting('shortlink_api', res2.text.strip())
        await res2.reply("✅ **SUCCESSFULLY SET SHORTLINK!**", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


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
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_verify")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW TUTORIAL VIDEO URL...</b>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        await db.update_bot_setting('tut_vid', res.text.strip())
        await res.reply("✅ **TUTORIAL LINK UPDATED!**", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_set_verify_time$"))
async def action_set_verify_time(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_verify")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME TOKEN EXPIRE TIME IN SECONDS...</b>\n\n<i>Example: 3600 (1 Hour)</i>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        if res.text.isdigit():
            await db.update_bot_setting('verify_expire', int(res.text.strip()))
            await res.reply("✅ **VERIFICATION TIME UPDATED!**", reply_markup=back_btn)
        else:
            await client.send_message(chat_id=user_id, text="❌ **INVALID NUMBER!**", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


# ==============================================================================
# ✍️ CUSTOM CAPTION SETTINGS
# ==============================================================================

@Bot.on_callback_query(filters.regex("^panel_caption$"))
async def panel_caption(client: Client, callback_query: CallbackQuery):
    settings = await db.get_bot_settings()
    current_cap = settings.get('custom_caption', CUSTOM_CAPTION)

    caption = f"<b>✍️ CUSTOM CAPTION SETTINGS</b>\n\n<b>CURRENT CAPTION:</b>\n<code>{current_cap if current_cap else 'Disabled'}</code>"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ SET CAPTION", callback_data="action_set_caption"), InlineKeyboardButton("🗑️ DELETE CAPTION", callback_data="action_del_caption")],
        [InlineKeyboardButton("ᐸ BACK", callback_data="panel_main")]
    ])
    await callback_query.message.edit_text(caption, reply_markup=buttons, disable_web_page_preview=True)


@Bot.on_callback_query(filters.regex("^action_set_caption$"))
async def action_set_caption(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    user_id = callback_query.from_user.id
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("ᐸ BACK", callback_data="panel_caption")]])

    await client.send_message(
        chat_id=user_id,
        text="<b>SEND ME NEW CUSTOM CAPTION...</b>\n\n<b>Available Fillings:</b>\n• <code>{filename}</code>\n• <code>{previouscaption}</code>\n\n<i>/cancel - CANCEL THIS PROCESS.</i>",
        reply_markup=ForceReply(selective=True)
    )
    try:
        res = await client.listen(chat_id=user_id, timeout=300)
        if not res.text or res.text.startswith('/cancel'):
            return await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)

        await db.update_bot_setting('custom_caption', res.text.html if hasattr(res.text, 'html') else res.text)
        await res.reply("✅ **CUSTOM CAPTION UPDATED!**", reply_markup=back_btn)
    except Exception:
        await client.send_message(chat_id=user_id, text="<b>CANCELLED THIS PROCESS...</b>", reply_markup=back_btn)


@Bot.on_callback_query(filters.regex("^action_del_caption$"))
async def action_del_caption(client: Client, callback_query: CallbackQuery):
    await db.update_bot_setting('custom_caption', "")
    await callback_query.answer("🗑 Caption cleared!", show_alert=True)
    await panel_caption(client, callback_query)


# ==============================================================================
# 💬 TEXT COMMAND COMPATIBILITY (/addchnl, /delchnl, /fsub_mode, /listchnl, /delreq)
# ==============================================================================

@Bot.on_message(filters.command('fsub_mode') & filters.private & admin)
async def change_force_sub_mode_cmd(client: Client, message: Message):
    temp = await message.reply("Wait a sec...", quote=True)
    channels = await db.show_channels()
    if not channels:
        return await temp.edit("❌ No force-sub channels found.")

    buttons = []
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            mode = await db.get_channel_mode(ch_id)
            status = "🟢" if mode == "on" else "🔴"
            buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"toggle_rfs_{ch_id}")])
        except Exception:
            buttons.append([InlineKeyboardButton(f"⚠️ {ch_id}", callback_data=f"toggle_rfs_{ch_id}")])

    buttons.append([InlineKeyboardButton("Close ✖️", callback_data="close_panel")])
    await temp.edit("<b>Select channel to toggle Request Mode:</b>", reply_markup=InlineKeyboardMarkup(buttons))


@Bot.on_message(filters.command('addchnl') & filters.private & admin)
async def add_force_sub_cmd(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        return await message.reply("Usage: <code>/addchnl -100xxxxxxxxxx</code>")

    try:
        chat_id = int(args[1])
        chat = await client.get_chat(chat_id)
        await db.add_channel(chat.id)
        await message.reply(f"✅ **Added Channel:** {chat.title} (<code>{chat.id}</code>)")
    except Exception as e:
        await message.reply(f"❌ **Error:** {e}")


@Bot.on_message(filters.command('delchnl') & filters.private & admin)
async def del_force_sub_cmd(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) != 2:
        return await message.reply("Usage: <code>/delchnl <channel_id | all></code>")

    if args[1].lower() == "all":
        channels = await db.show_channels()
        for c in channels:
            await db.rem_channel(c)
        return await message.reply("✅ All channels removed.")

    try:
        ch_id = int(args[1])
        await db.rem_channel(ch_id)
        await message.reply(f"✅ Channel removed: <code>{ch_id}</code>")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@Bot.on_message(filters.command('listchnl') & filters.private & admin)
async def list_force_sub_channels_cmd(client: Client, message: Message):
    channels = await db.show_channels()
    if not channels:
        return await message.reply("❌ No channels found.")

    res = "<b>⚡ Force-sub Channels:</b>\n\n"
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            mode = await db.get_channel_mode(ch_id)
            m_icon = "🟢 REQ" if mode == "on" else "🔴 NORMAL"
            res += f"• <b>{chat.title}</b> [<code>{ch_id}</code>] - {m_icon}\n"
        except Exception:
            res += f"• <code>{ch_id}</code> (Unavailable)\n"

    await message.reply(res)


@Bot.on_message(filters.command('delreq') & filters.private & admin)
async def delete_requested_users_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/delreq <channel_id></code>")

    try:
        channel_id = int(message.command[1])
        channel_data = await db.rqst_fsub_Channel_data.find_one({'_id': channel_id})
        if not channel_data or not channel_data.get("user_ids"):
            return await message.reply("ℹ️ No request users found.")

        user_ids = channel_data.get("user_ids", [])
        removed = 0
        for u_id in user_ids:
            try:
                member = await client.get_chat_member(channel_id, u_id)
                if member.status not in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                    await db.del_req_user(channel_id, u_id)
                    removed += 1
            except UserNotParticipant:
                await db.del_req_user(channel_id, u_id)
                removed += 1
            except Exception:
                pass

        await message.reply(f"✅ Cleanup complete for `{channel_id}`. Removed non-members: `{removed}`")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


# ==============================================================================
# 🔄 GLOBAL NAVIGATION & CLOSE
# ==============================================================================

@Bot.on_callback_query(filters.regex("^panel_main$"))
async def panel_main(client: Client, callback_query: CallbackQuery):
    await send_main_settings_panel(callback_query)


@Bot.on_callback_query(filters.regex("^close_panel$"))
async def close_panel(client: Client, callback_query: CallbackQuery):
    await callback_query.message.delete()
