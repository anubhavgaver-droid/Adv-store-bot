import asyncio
import os
import random
import sys
import time
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction, ChatMemberStatus, ChatType
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatMemberUpdated
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, InviteHashEmpty, ChatAdminRequired, PeerIdInvalid, UserIsBlocked, InputUserDeactivated
from bot import Bot
from config import *
from helper_func import *
from database.database import *

# ==============================================================================
# 🎛️ FSUB MODE COMMAND & CALLBACK HANDLER
# ==============================================================================

@Bot.on_message(filters.command('fsub_mode') & filters.private & admin)
async def change_force_sub_mode(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    channels = await db.show_channels()

    if not channels:
        return await temp.edit("<b>❌ No force-sub channels found.</b>")

    buttons = []
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            mode = await db.get_channel_mode(ch_id)
            status = "🟢" if mode == "on" else "🔴"
            title = f"{status} {chat.title}"
            buttons.append([InlineKeyboardButton(title, callback_data=f"rfs_ch_{ch_id}")])
        except Exception:
            buttons.append([InlineKeyboardButton(f"⚠️ {ch_id} (Unavailable)", callback_data=f"rfs_ch_{ch_id}")])

    buttons.append([InlineKeyboardButton("Close ✖️", callback_data="close")])

    await temp.edit(
        "<b>⚡ Select a channel to toggle Request Force-Sub Mode:</b>\n"
        "🟢 = Request Mode ON\n🔴 = Request Mode OFF",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )


# 🟢 MISSING CALLBACK HANDLER ADDED HERE 🟢
@Bot.on_callback_query(filters.regex(r"^rfs_ch_"))
async def toggle_req_fsub_mode(client: Client, callback_query: CallbackQuery):
    ch_id = int(callback_query.data.split("_")[2])
    
    # Toggle channel mode in DB
    current_mode = await db.get_channel_mode(ch_id)
    new_mode = "off" if current_mode == "on" else "on"
    
    await db.set_channel_mode(ch_id, new_mode)
    
    # Add or remove channel from reqChannel list
    if new_mode == "on":
        if hasattr(db, 'add_req_channel'):
            await db.add_req_channel(ch_id)
        await callback_query.answer("🟢 Request Mode Turned ON", show_alert=True)
    else:
        if hasattr(db, 'del_req_channel'):
            await db.del_req_channel(ch_id)
        await callback_query.answer("🔴 Request Mode Turned OFF", show_alert=True)

    # Refresh Menu UI
    channels = await db.show_channels()
    buttons = []
    for c_id in channels:
        try:
            chat = await client.get_chat(c_id)
            mode = await db.get_channel_mode(c_id)
            status = "🟢" if mode == "on" else "🔴"
            title = f"{status} {chat.title}"
            buttons.append([InlineKeyboardButton(title, callback_data=f"rfs_ch_{c_id}")])
        except Exception:
            buttons.append([InlineKeyboardButton(f"⚠️ {c_id} (Unavailable)", callback_data=f"rfs_ch_{c_id}")])

    buttons.append([InlineKeyboardButton("Close ✖️", callback_data="close")])
    await callback_query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))


# ==============================================================================
# 📩 JOIN REQUEST & CHAT MEMBER HANDLERS
# ==============================================================================

@Bot.on_chat_member_updated()
async def handle_Chatmembers(client, chat_member_updated: ChatMemberUpdated):    
    chat_id = chat_member_updated.chat.id

    if await db.reqChannel_exist(chat_id):
        old_member = chat_member_updated.old_chat_member

        if not old_member:
            return

        if old_member.status == ChatMemberStatus.MEMBER:
            user_id = old_member.user.id
            if await db.req_user_exist(chat_id, user_id):
                await db.del_req_user(chat_id, user_id)


@Bot.on_chat_join_request()
async def handle_join_request(client, chat_join_request):
    chat_id = chat_join_request.chat.id
    user_id = chat_join_request.from_user.id

    channel_exists = await db.reqChannel_exist(chat_id)
    if channel_exists:
        if not await db.req_user_exist(chat_id, user_id):
            await db.req_user(chat_id, user_id)


# ==============================================================================
# 📢 CHANNEL MANAGEMENT COMMANDS
# ==============================================================================

@Bot.on_message(filters.command('addchnl') & filters.private & admin)
async def add_force_sub(client: Client, message: Message):
    temp = await message.reply("Wait a sec...", quote=True)
    args = message.text.split(maxsplit=1)

    if len(args) != 2:
        return await temp.edit("Usage:\n<code>/addchnl -100xxxxxxxxxx</code>")

    try:
        chat_id = int(args[1])
    except ValueError:
        return await temp.edit("❌ Invalid chat ID!")

    all_chats = await db.show_channels()
    if chat_id in [c if isinstance(c, int) else c[0] for c in all_chats]:
        return await temp.edit(f"Already exists:\n<code>{chat_id}</code>")

    try:
        chat = await client.get_chat(chat_id)
        if chat.type not in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
            return await temp.edit("❌ Only channels/supergroups allowed.")

        bot_member = await client.get_chat_member(chat.id, "me")
        if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return await temp.edit("❌ Bot must be admin in that chat.")

        # Create Join Request Link if supported
        try:
            link = await client.create_chat_invite_link(chat.id, creates_join_request=True)
            invite_link = link.invite_link
        except Exception:
            try:
                invite_link = await client.export_chat_invite_link(chat.id)
            except Exception:
                invite_link = f"https://t.me/{chat.username}" if chat.username else f"https://t.me/c/{str(chat.id)[4:]}"

        await db.add_channel(chat_id)
        return await temp.edit(
            f"✅ Added Successfully!\n\n"
            f"<b>Name:</b> <a href='{invite_link}'>{chat.title}</a>\n"
            f"<b>ID:</b> <code>{chat_id}</code>",
            disable_web_page_preview=True
        )

    except Exception as e:
        return await temp.edit(f"❌ Failed to add chat:\n<code>{chat_id}</code>\n\n<i>{e}</i>")


@Bot.on_message(filters.command('delchnl') & filters.private & admin)
async def del_force_sub(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    args = message.text.split(maxsplit=1)
    all_channels = await db.show_channels()

    if len(args) != 2:
        return await temp.edit("<b>Usage:</b> <code>/delchnl <channel_id | all></code>")

    if args[1].lower() == "all":
        if not all_channels:
            return await temp.edit("<b>❌ No force-sub channels found.</b>")
        for ch_id in all_channels:
            await db.del_channel(ch_id)
        return await temp.edit("<b>✅ All force-sub channels have been removed.</b>")

    try:
        ch_id = int(args[1])
    except ValueError:
        return await temp.edit("<b>❌ Invalid Channel ID</b>")

    if ch_id in all_channels:
        await db.rem_channel(ch_id)
        return await temp.edit(f"<b>✅ Channel removed:</b> <code>{ch_id}</code>")
    else:
        return await temp.edit(f"<b>❌ Channel not found in force-sub list:</b> <code>{ch_id}</code>")


@Bot.on_message(filters.command('listchnl') & filters.private & admin)
async def list_force_sub_channels(client: Client, message: Message):
    temp = await message.reply("<b><i>ᴡᴀɪᴛ ᴀ sᴇᴄ..</i></b>", quote=True)
    channels = await db.show_channels()

    if not channels:
        return await temp.edit("<b>❌ No force-sub channels found.</b>")

    result = "<b>⚡ Force-sub Channels:</b>\n\n"
    for ch_id in channels:
        try:
            chat = await client.get_chat(ch_id)
            link = chat.invite_link or await client.export_chat_invite_link(chat.id)
            result += f"<b>•</b> <a href='{link}'>{chat.title}</a> [<code>{ch_id}</code>]\n"
        except Exception:
            result += f"<b>•</b> <code>{ch_id}</code> — <i>Unavailable</i>\n"

    await temp.edit(result, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Close ✖️", callback_data="close")]]))


@Bot.on_message(filters.command('delreq') & filters.private & admin)
async def delete_requested_users(client, message: Message):
    if len(message.command) < 2:
        return await message.reply("⚠️ Usᴀɢᴇ: `/delreq <channel_id>`", quote=True)

    try:
        channel_id = int(message.command[1])
    except ValueError:
        return await message.reply("❌ Iɴᴠᴀʟɪᴅ ᴄʜᴀɴɴᴇʟ ID.", quote=True)

    channel_data = await db.rqst_fsub_Channel_data.find_one({'_id': channel_id})
    if not channel_data:
        return await message.reply("ℹ️ Nᴏ ʀᴇǫᴜᴇsᴛ ᴄʜᴀɴɴᴇʟ ғᴏᴜɴᴅ ғᴏᴏʀ ᴛʜɪs ᴄʜᴀɴɴᴇʟ.", quote=True)

    user_ids = channel_data.get("user_ids", [])
    if not user_ids:
        return await message.reply("✅ Nᴏ ᴜsᴇʀs ᴛᴏ ᴘʀᴏᴄᴇss.", quote=True)

    removed = 0
    skipped = 0
    left_users = 0

    for user_id in user_ids:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                skipped += 1
                continue
            else:
                await db.del_req_user(channel_id, user_id)
                left_users += 1
        except UserNotParticipant:
            await db.del_req_user(channel_id, user_id)
            left_users += 1
        except Exception as e:
            skipped += 1

    for user_id in user_ids:
        if not await db.req_user_exist(channel_id, user_id):
            await db.del_req_user(channel_id, user_id)
            removed += 1

    return await message.reply(
        f"✅ Cʟᴇᴀɴᴜᴘ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ғᴏʀ ᴄʜᴀɴɴᴇʟ `{channel_id}`\n\n"
        f"👤 Rᴇᴍᴏᴠᴇᴅ ᴜsᴇʀs ɴᴏᴛ ɪɴ ᴄʜᴀɴɴᴇʟ: `{left_users}`\n"
        f"🗑️ Rᴇᴍᴏᴠᴇᴅ ʟᴇғᴛᴏᴠᴇʀ ɴᴏɴ-ʀᴇǫᴜᴇsᴛ ᴜsᴇʀs: `{removed}`\n"
        f"✅ Sᴛɪʟʟ ᴍᴇᴍʙᴇʀs: `{skipped}`",
        quote=True
    )
