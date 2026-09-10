# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport
#
# Copyright (C) 2025 by Codeflix-Bots@Github, < https://github.com/Codeflix-Bots >.
#
# This file is part of < https://github.com/Codeflix-Bots/FileStore > project,
# and is released under the MIT License.
# Please see < https://github.com/Codeflix-Bots/FileStore/blob/master/LICENSE >
#
# All rights reserved.
#

import asyncio
import os
import random
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta, timezone
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode, ChatAction
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, ChatInviteLink, ChatPrivileges
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from bot import Bot
from config import *
from helper_func import *
from database.database import *

# Logging setup for Render logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#=====================================================================================##

@Bot.on_message(filters.command('stats') & filters.user(ADMINS))
async def stats(bot: Bot, message: Message):
    try:
        now = datetime.now(timezone.utc)
        delta = now - bot.uptime
        time_str = get_readable_time(delta.seconds)
        await message.reply(BOT_STATS_TEXT.format(uptime=time_str))
    except Exception as e:
        err = traceback.format_exc()
        logger.error(f"[STATS ERROR] User ID: {message.from_user.id}\n{err}")
        await message.reply(f"❌ <b>Error running /stats:</b>\n<code>{e}</code>")

#=====================================================================================##

WAIT_MSG = "<b>Working....</b>"

#=====================================================================================##

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    try:
        msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
        users = await db.full_userbase()
        await msg.edit(f"{len(users)} users are using this bot")
    except Exception as e:
        err = traceback.format_exc()
        logger.error(f"[USERS ERROR] User ID: {message.from_user.id}\n{err}")
        await message.reply(f"❌ <b>Error running /users:</b>\n<code>{e}</code>")

#=====================================================================================##

#AUTO-DELETE

@Bot.on_message(filters.private & filters.command('dlt_time') & filters.user(ADMINS))
async def set_delete_time(client: Bot, message: Message):
    try:
        duration = int(message.command[1])
        await db.set_del_timer(duration)
        await message.reply(f"<b>Dᴇʟᴇᴛᴇ Tɪᴍᴇʀ ʜᴀs ʙᴇᴇɴ sᴇᴛ ᴛᴏ <blockquote>{duration} sᴇᴄᴏɴᴅs.</blockquote></b>")
    except (IndexError, ValueError):
        await message.reply("<b>Pʟᴇᴀsᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴠᴀʟɪᴅ ᴅᴜʀᴀᴛɪᴏɴ ɪɴ sᴇᴄᴏɴᴅs.</b> Usage: /dlt_time {duration}")
    except Exception as e:
        err = traceback.format_exc()
        logger.error(f"[DLT_TIME ERROR] User ID: {message.from_user.id}\n{err}")
        await message.reply(f"❌ <b>Error running /dlt_time:</b>\n<code>{e}</code>")

@Bot.on_message(filters.private & filters.command('check_dlt_time') & filters.user(ADMINS))
async def check_delete_time(client: Bot, message: Message):
    try:
        duration = await db.get_del_timer()
        await message.reply(f"<b><blockquote>CᴜʀʀᴇɴT ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇʀ ɪs sᴇᴛ ᴛᴏ {duration}sᴇᴄᴏɴᴅs.</blockquote></b>")
    except Exception as e:
        err = traceback.format_exc()
        logger.error(f"[CHECK_DLT_TIME ERROR] User ID: {message.from_user.id}\n{err}")
        await message.reply(f"❌ <b>Error running /check_dlt_time:</b>\n<code>{e}</code>")

#=====================================================================================##
