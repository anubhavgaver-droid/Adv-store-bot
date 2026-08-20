#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#

from pyrogram import Client 
from bot import Bot
from config import *
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import *
from pyrogram import enums
from plugins.adminz import send_main_settings_panel

@Bot.on_callback_query()
async def cb_handler(client: Bot, query: CallbackQuery):
    data = query.data

    if data == "help":
        await query.message.edit_text(
            text=HELP_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton("ᴄʟᴏꜱᴇ", callback_data='close')]
            ])
        )

    elif data == "about":
        await query.message.edit_text(
            text=ABOUT_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='start'),
                 InlineKeyboardButton('ᴄʟᴏꜱᴇ', callback_data='close')]
            ])
        )

    elif data == "start":
        await query.message.edit_text(
            text=START_MSG.format(first=query.from_user.first_name,
                last=query.from_user.last_name or "",
                mention=query.from_user.mention,
                id=query.from_user.id),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
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
        )

    # ⚙️ SETTINGS BUTTON HANDLER (ONLY FOR ADMIN)
    elif data == "cb_settings":
        if query.from_user.id not in ADMINS:
            return await query.answer("⚠️ दिस इज ओनली फॉर एडमिन! (This is only for Admin)", show_alert=True)
        await query.answer()
        await send_main_settings_panel(query)

    elif data == "channels":
        await query.message.edit_text(
            text=CHANNELS_TXT.format(first=query.from_user.first_name),
            disable_web_page_preview=True,
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

    # 💎 DYNAMIC PREMIUM PLAN DISPLAY (FIXED DYNAMIC DB FETCHING)
    elif data == "premium":
        await query.message.delete()
        
        # 1. डेटाबेस से लाइव सेटिंग्स निकालें
        settings = await db.get_bot_settings()
        plan_text = settings.get('premium_plan_text', None)
        upi_id = settings.get('upi_id', UPI_ID)
        qr_pic = settings.get('qr_pic', QR_PIC)

        # 2. अगर DB में नया टेक्स्ट सेट न हो तो डिफ़ॉल्ट दिखाएगा
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

        await client.send_photo(
            chat_id=query.message.chat.id,
            photo=qr_pic,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("ADMIN 24/7", url=SCREENSHOT_URL)],
                    [InlineKeyboardButton("🔒 Close", callback_data="close")]
                ]
            )
        )

    elif data == "close":
        await query.message.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
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
            await query.message.edit_text(
                f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            await query.answer("Failed to fetch channel info", show_alert=True)

    elif data.startswith("rfs_toggle_"):
        cid, action = data.split("_")[2:]
        cid = int(cid)
        mode = "on" if action == "on" else "off"

        await db.set_channel_mode(cid, mode)
        await query.answer(f"Force-Sub set to {'ON' if mode == 'on' else 'OFF'}")

        chat = await client.get_chat(cid)
        status = "🟢 ON" if mode == "on" else "🔴 OFF"
        new_mode = "off" if mode == "on" else "on"
        buttons = [
            [InlineKeyboardButton(f"ʀᴇǫ ᴍᴏᴅᴇ {'OFF' if mode == 'on' else 'ON'}", callback_data=f"rfs_toggle_{cid}_{new_mode}")],
            [InlineKeyboardButton("‹ ʙᴀᴄᴋ", callback_data="fsub_back")]
        ]
        await query.message.edit_text(
            f"Channel: {chat.title}\nCurrent Force-Sub Mode: {status}",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data == "fsub_back":
        channels = await db.show_channels()
        buttons = []
        for cid in channels:
            try:
                chat = await client.get_chat(cid)
                mode = await db.get_channel_mode(cid)
                status = "🟢" if mode == "on" else "🔴"
                buttons.append([InlineKeyboardButton(f"{status} {chat.title}", callback_data=f"rfs_ch_{cid}")])
            except:
                continue

        await query.message.edit_text(
            "sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴛᴏɢɢʟᴇ ɪᴛs ғᴏʀᴄᴇ-sᴜʙ ᴍᴏᴅᴇ:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
