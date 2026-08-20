#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#

import logging
from pyrogram import Client, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified, FloodWait
from bot import Bot
from config import *
from database.database import *
from plugins.adminz import send_main_settings_panel

logger = logging.getLogger(__name__)

# ==================== SAFE MESSAGE EDIT HELPER ====================
async def safe_edit_text(message: Message, text: str, reply_markup=None, disable_web_page_preview=True):
    """
    Safely edits text whether the original message was a Photo or Text message.
    Prevents Telegram API errors when switching media types.
    """
    try:
        if message.photo or message.video or message.document:
            await message.edit_caption(
                caption=text,
                reply_markup=reply_markup
            )
        else:
            await message.edit_text(
                text=text,
                disable_web_page_preview=disable_web_page_preview,
                reply_markup=reply_markup
            )
    except MessageNotModified:
        pass
    except Exception:
        try:
            await message.delete()
        except Exception:
            pass
        await message.reply_text(
            text=text,
            disable_web_page_preview=disable_web_page_preview,
            reply_markup=reply_markup
        )


# ==================== MAIN CALLBACK HANDLER ====================
@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    if data == "help":
        try:
            text = HELP_TXT.format(
                first=query.from_user.first_name,
                last=query.from_user.last_name or "",
                mention=query.from_user.mention,
                id=query.from_user.id
            )
        except Exception:
            text = HELP_TXT

        await safe_edit_text(
            message=query.message,
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]
            ])
        )

    elif data == "about":
        try:
            text = ABOUT_TXT.format(
                first=query.from_user.first_name,
                last=query.from_user.last_name or "",
                mention=query.from_user.mention,
                id=query.from_user.id
            )
        except Exception:
            text = ABOUT_TXT

        await safe_edit_text(
            message=query.message,
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close')]
            ])
        )

    # 🟢 DYNAMIC START MESSAGE & PHOTO CHECK FROM DATABASE
    elif data == "start":
        bot_settings = await db.get_bot_settings()
        dyn_start_msg = bot_settings.get('start_msg') or START_MSG
        
        # 🟢 केवल DB से फोटो चेक करें (कोई हार्डकोडेड फॉलबैक नहीं)
        dyn_start_pic = bot_settings.get('start_pic', '')
        if isinstance(dyn_start_pic, str):
            dyn_start_pic = dyn_start_pic.strip()
            if dyn_start_pic.lower() in ["none", "off", "no", "false"]:
                dyn_start_pic = ""

        try:
            caption = dyn_start_msg.format(
                first=query.from_user.first_name,
                last=query.from_user.last_name or "",
                username=f"@{query.from_user.username}" if query.from_user.username else "",
                mention=query.from_user.mention,
                id=query.from_user.id
            )
        except Exception:
            caption = dyn_start_msg

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟꜱ •", callback_data='channels', style=enums.ButtonStyle.PRIMARY)
            ],
            [
                InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data='about'),
                InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data='help')
            ],
            [
                InlineKeyboardButton("⚙️ SETTINGS", callback_data='cb_settings')
            ]
        ])

        # अगर DB में फोटो मौजूद है
        if dyn_start_pic:
            if query.message.photo:
                await safe_edit_text(
                    message=query.message,
                    text=caption,
                    reply_markup=buttons
                )
            else:
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await client.send_photo(
                    chat_id=query.message.chat.id,
                    photo=dyn_start_pic,
                    caption=caption,
                    reply_markup=buttons
                )
        # अगर फोटो डिलीट/खाली है तो केवल टेक्स्ट भेजेगा
        else:
            if query.message.photo:
                try:
                    await query.message.delete()
                except Exception:
                    pass
                await client.send_message(
                    chat_id=query.message.chat.id,
                    text=caption,
                    reply_markup=buttons,
                    disable_web_page_preview=True
                )
            else:
                await safe_edit_text(
                    message=query.message,
                    text=caption,
                    reply_markup=buttons
                )

    # ⚙️ SETTINGS BUTTON HANDLER (ONLY FOR ADMIN)
    elif data == "cb_settings":
        if query.from_user.id not in ADMINS:
            return await query.answer("⚠️ This is only for Admin ⚠️", show_alert=True)
        await query.answer()
        await send_main_settings_panel(query)

    elif data == "channels":
        try:
            text = CHANNELS_TXT.format(
                first=query.from_user.first_name,
                last=query.from_user.last_name or "",
                mention=query.from_user.mention,
                id=query.from_user.id
            )
        except Exception:
            text = CHANNELS_TXT

        await safe_edit_text(
            message=query.message,
            text=text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("• ᴄʜᴀɴɴᴇʟꜱ •", url="https://t.me/freestoryhubMR", style=enums.ButtonStyle.PRIMARY)
                ],
                [
                    InlineKeyboardButton("• ReQeST GrOuP •", url="https://t.me/pratilipifm0900", style=enums.ButtonStyle.PRIMARY)
                ],
                [
                    InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                    InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close', style=enums.ButtonStyle.DANGER)
                ]
            ])
        )

    # 💎 DYNAMIC PREMIUM PLAN DISPLAY
    elif data == "premium":
        try:
            await query.message.delete()
        except Exception:
            pass
        
        settings = await db.get_bot_settings()
        plan_text = settings.get('premium_plan_text', None)
        upi_id = settings.get('upi_id', UPI_ID)
        qr_pic = settings.get('qr_pic', '')

        default_text = (
            f"👋 {query.from_user.mention}\n\n"
            f"🎖️ <b>Available Plans :</b>\n\n"
            f"● {PRICE1} For 7 Days Membership\n\n"
            f"● {PRICE2} For 1 Month Membership\n\n"
            f"● {PRICE3} For 3 Months Membership\n\n"
            f"● {PRICE4} For 6 Months Membership\n\n"
            f"● {PRICE5} For 1 Year Membership\n"
        )

        final_plan_text = plan_text if (plan_text and plan_text.strip()) else default_text

        caption = (
            f"{final_plan_text}\n\n"
            f"💵 <b>UPI ID:</b> <code>{upi_id}</code>\n\n"
            f"♻️ After Payment You Will Get Instant Membership\n\n"
            f"‼️ Must Send Screenshot after payment."
        )

        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("ADMIN 24/7", url=SCREENSHOT_URL)],
            [InlineKeyboardButton("🔒 Close", callback_data="close")]
        ])

        if qr_pic:
            try:
                await client.send_photo(
                    chat_id=query.message.chat.id,
                    photo=qr_pic,
                    caption=caption,
                    reply_markup=reply_markup
                )
            except Exception:
                await client.send_message(
                    chat_id=query.message.chat.id,
                    text=caption,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
        else:
            await client.send_message(
                chat_id=query.message.chat.id,
                text=caption,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )

    elif data == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        try:
            if query.message.reply_to_message:
                await query.message.reply_to_message.delete()
        except Exception:
            pass

    elif data.startswith("rfs_ch_"):
        cid = int(data.split("_")[2])
        try:
            chat = await client.get_chat(cid)
            mode = await db.get_channel_mode(cid)
            status = "🟢 ᴏɴ" if mode == "on" else "🔴 ᴏғғ"
            new_mode = "ᴏғғ" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
            ]
            await safe_edit_text(
                message=query.message,
                text=f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logger.error(f"Error fetching channel info: {e}")
            await query.answer("Failed to fetch channel info", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

        try:
            chat = await client.get_chat(cid)
            status = "🟢 ON" if mode == "on" else "🔴 OFF"
            new_mode = "off" if mode == "on" else "on"
            buttons = [
                [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
                [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
            ]
            await safe_edit_text(
                message=query.message,
                text=f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception as e:
            logger.error(f"Error toggling force-sub: {e}")

    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                mode = await db.get_channel_mode(cid)
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")])
            except Exception:
                continue

        await safe_edit_text(
            message=query.message,
            text="sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
