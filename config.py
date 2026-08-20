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

import os
import logging
from logging.handlers import RotatingFileHandler

def get_env_int(key: str, default: int = 0) -> int:
    """Safely parse integer environment variables to prevent boot crashes."""
    val = os.getenv(key, "").strip()
    if val.startswith("-") and val[1:].isdigit():
        return int(val)
    return int(val) if val.isdigit() else default

# --------------------------------------------
# Telegram API Credentials
# --------------------------------------------
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
APP_ID = get_env_int("APP_ID", 0)
API_HASH = os.getenv("API_HASH", "")

# --------------------------------------------
# Database & Channel Settings
# --------------------------------------------
CHANNEL_ID = get_env_int("CHANNEL_ID", 0)
OWNER = os.getenv("OWNER", "Kcxry")
OWNER_ID = get_env_int("OWNER_ID", 5898522531)

# Safely parse admin IDs and ensure OWNER_ID is included
raw_admins = os.getenv("ADMINS", "5898522531").split()
ADMINS = [int(x) for x in raw_admins if x.strip().lstrip("-").isdigit()]
if OWNER_ID not in ADMINS:
    ADMINS.append(OWNER_ID)

# --------------------------------------------
# Web Server & Database
# --------------------------------------------
PORT = os.getenv("PORT", "8001")
DB_URI = os.getenv("DATABASE_URL", "")
DB_NAME = os.getenv("DATABASE_NAME", "Cluovvoo")

# --------------------------------------------
# Bot Options & Security
# --------------------------------------------
FSUB_LINK_EXPIRY = get_env_int("FSUB_LINK_EXPIRY", 0)
BAN_SUPPORT = os.getenv("BAN_SUPPORT", "https://t.me/pratilipifm0900")
TG_BOT_WORKERS = get_env_int("TG_BOT_WORKERS", 200)

START_PIC = os.getenv("START_PIC", "https://telegra.ph/file/ec17880d61180d3312d6a.jpg")
FORCE_PIC = os.getenv("FORCE_PIC", "https://telegra.ph/file/e292b12890b8b4b9dcbd1.jpg")

# --------------------------------------------
# Shortener & Verification
# --------------------------------------------
SHORTLINK_URL = os.getenv("SHORTLINK_URL", "linkshortify.com")
SHORTLINK_API = os.getenv("SHORTLINK_API", "")
VERIFY_EXPIRE = get_env_int("VERIFY_EXPIRE", 3600)
TUT_VID = os.getenv("TUT_VID", "https://t.me/howanubhav/14")

# --------------------------------------------
# User Interface Messages
# --------------------------------------------
HELP_TXT = "<b><blockquote>ᴛʜɪs ɪs ᴀɴ ғɪʟᴇ ᴛᴏ ʟɪɴᴋ ʙᴏᴛ ᴡᴏʀᴋ ғᴏʀ @HDFILM0900_BOT\n\n❏ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs\n├/start : sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ\n├/about : ᴏᴜʀ Iɴғᴏʀᴍᴀᴛɪᴏɴ\n└/help : ʜᴇʟᴘ ʀᴇʟᴀᴛᴇᴅ ʙᴏᴛ\n\n sɪᴍᴘʟʏ ᴄʟɪᴄᴋ ᴏɴ ʟɪɴᴋ ᴀɴᴅ sᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ ᴊᴏɪɴ ʙᴏᴛʜ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ ᴛʜᴀᴛs ɪᴛ.....!\n\n ᴅᴇᴠᴇʟᴏᴘᴇᴅ ʙʏ <a href=https://t.me/HDFILM0900_BOT>╰‿╯ ＫＡ ＬＵ u ꔪ</a></blockquote></b>"
CHANNELS_TXT = "<b><blockquote>◈ 𝙷𝙴𝚁𝙴 𝙾𝚄𝚁 𝙲𝙷𝙰𝙽𝙽𝙴𝙻 & 𝙶𝚁𝙾𝚄𝙿 𝙻𝙸𝙽𝙺𝚂</blockquote></b>"
ABOUT_TXT = "<b><blockquote>◈ ᴄʀᴇᴀᴛᴏʀ: <a href=https://t.me/hdfilm0900_bot>╰‿╯ ＫＡ ＬＵ u</a>\n‣ʟɪʙʀᴀʀʏ : ᴘʏʀᴏɢʀᴀᴍ\n‣ ʟᴀɴɢᴜᴀɢE : ᴘʏᴛʜᴏɴ3\n‣ ᴅᴀᴛᴀ ʙᴀsᴇ : ᴍᴏɴɢᴏ ᴅʙ\n‣ ʜᴏsᴛᴇᴅ ᴏɴ  : ʜᴇʀᴏᴋᴜ\n‣ ʙᴜɪʟᴅ sᴛᴀᴛᴜs : ᴠ10+ᵖʳᵒ  [𝙰𝙳𝚅𝙰𝙽𝙲𝙴]</blockquote></b>"

START_MSG = os.getenv("START_MESSAGE", "<b>ʜᴇʟʟᴏ {mention}\n\n<blockquote> ɪ ᴀᴍ ғɪʟᴇ sᴛᴏʀᴇ ʙᴏᴛ, ɪ ᴄᴀɴ sᴛᴏʀᴇ ᴘʀɪᴠᴀᴛᴇ ғɪʟᴇs ɪɴ sᴘᴇᴄɪғɪᴇᴅ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ᴏᴛʜᴇʀ ᴜsᴇʀs ᴄᴀɴ ᴀᴄᴄᴇss ɪᴛ ғʀᴏᴍ sᴘᴇᴄɪᴀʟ ʟɪɴᴋ.</blockquote></b>")
FORCE_MSG = os.getenv("FORCE_SUB_MESSAGE", "ʜᴇʟʟᴏ {mention}\n\n<b><blockquote>ᴊᴏɪɴ ᴏᴜʀ ᴄʜᴀɴɴᴇʟs ᴀɴᴅ ᴛʜᴇɴ ᴄʟɪᴄᴋ ᴏɴ ʀᴇʟᴏᴀᴅ button ᴛᴏ ɢᴇᴛ ʏᴏᴜʀ ʀᴇǫᴜᴇꜱᴛᴇᴅ ꜰɪʟᴇ.</b></blockquote>")

CMD_TXT = """<blockquote><b>» ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs:</b></blockquote>

<b>›› /dlt_time :</b> sᴇᴛ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /check_dlt_time :</b> ᴄʜᴇᴄᴋ ᴄᴜʀʀᴇɴᴛ ᴅᴇʟᴇᴛᴇ ᴛɪᴍᴇ
<b>›› /dbroadcast :</b> ʙʀᴏᴀᴅᴄᴀsᴛ ᴅᴏᴄᴜᴍᴇɴᴛ / ᴠɪᴅᴇᴏ
<b>›› /ban :</b> ʙᴀɴ ᴀ ᴜꜱᴇʀ
<b>›› /unban :</b> ᴜɴʙᴀɴ ᴀ ᴜꜱᴇʀ
<b>›› /banlist :</b> ɢᴇᴛ ʟɪsᴛ ᴏꜰ ʙᴀɴɴᴇᴅ ᴜꜱᴇʀs
<b>›› /addchnl :</b> ᴀᴅᴅ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ
<b>›› /delchnl :</b> ʀᴇᴍᴏᴠᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴄʜᴀɴɴᴇʟ
<b>›› /listchnl :</b> ᴠɪᴇᴡ ᴀᴅᴅᴇᴅ ᴄʜᴀɴɴᴇʟs
<b>›› /fsub_mode :</b> ᴛᴏɢɢʟᴇ ꜰᴏʀᴄᴇ sᴜʙ ᴍᴏᴅᴇ
<b>›› /pbroadcast :</b> sᴇɴᴅ ᴘʜᴏᴛᴏ ᴛᴏ ᴀʟʟ ᴜꜱᴇʀs
<b>›› /add_admin :</b> ᴀᴅᴅ ᴀɴ ᴀᴅᴍɪɴ
<b>›› /deladmin :</b> ʀᴇᴍᴏᴠᴇ ᴀɴ ᴀᴅᴍɪɴ
<b>›› /admins :</b> ɢᴇᴛ ʟɪsᴛ ᴏꜰ ᴀᴅᴍɪɴs
<b>›› /addpremium :</b> ᴀᴅᴅ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ
<b>›› /premium_users :</b> ʟɪsᴛ ᴀʟʟ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀs
<b>›› /remove_premium :</b> ʀᴇᴍᴏᴠᴇ ᴘʀᴇᴍɪᴜᴍ ꜰʀᴏᴍ ᴀ ᴜꜱᴇʀ
<b>›› /myplan :</b> ᴄʜᴇᴄᴋ ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ sᴛᴀᴛᴜs
<b>›› /count :</b> ᴄᴏᴜɴᴛ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴs
<b>›› /delreq :</b> Rᴇᴍᴏᴠᴇᴅ ʟᴇғᴛᴏᴠᴇʀ ɴᴏɴ-ʀᴇǫᴜᴇsᴛ ᴜsᴇʀs
"""

CUSTOM_CAPTION = os.getenv("CUSTOM_CAPTION", "<b>• ʙʏ @HDFILM0900_BOT</b>")
PROTECT_CONTENT = os.getenv("PROTECT_CONTENT", "False").strip().lower() == "true"
DISABLE_CHANNEL_BUTTON = os.getenv("DISABLE_CHANNEL_BUTTON", "False").strip().lower() == "true"

BOT_STATS_TEXT = "<b>BOT UPTIME</b> = {uptime}"
USER_REPLY_TEXT = "ʙᴀᴋᴋᴀ ! ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴍʏ ꜱᴇɴᴘᴀɪ!!"

# --------------------------------------------
# Premium & Payment Details
# --------------------------------------------
OWNER_TAG = os.getenv("OWNER_TAG", "KCXRY")
UPI_ID = os.getenv("UPI_ID", "")
QR_PIC = os.getenv("QR_PIC", "https://i.ibb.co/PGbZztgZ/photo-2026-05-04-16-41-38-7636287934861148164.jpg")
SCREENSHOT_URL = os.getenv("SCREENSHOT_URL", "t.me/O_Deleted_Account_0")

PRICE1 = os.getenv("PRICE1", "0 rs")
PRICE2 = os.getenv("PRICE2", "60 rs")
PRICE3 = os.getenv("PRICE3", "150 rs")
PRICE4 = os.getenv("PRICE4", "280 rs")
PRICE5 = os.getenv("PRICE5", "550 rs")

# --------------------------------------------
# Telegram Animations & Reactions
# --------------------------------------------
REACTIONS = ["🤝", "😇", "🤗", "😍", "👍", "🎅", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏", "😛", "😈", "🎉", "⚡️", "🫡", "🤓", "😎", "🏆", "🔥", "🤭", "🌚", "🆒", "👻", "😁"]
EFFECT_IDS = os.getenv("EFFECT_IDS", "5104841245755180586 5104858069142078462 5159385139981059251 5046509860389126442 5046589136895476101 5107584321108051014").split()

# --------------------------------------------
# Logger Configuration
# --------------------------------------------
LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50_000_000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
