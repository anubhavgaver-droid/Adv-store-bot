#(©)CodeFlix_Bots
#rohit_1888 on Tg #Dont remove this line

import base64
import re
import asyncio
import time
from datetime import date
from pyrogram import filters
from pyrogram.enums import ChatMemberStatus
from config import *
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant
from shortzy import Shortzy
from pyrogram.errors import FloodWait
from database.database import *


# Don't Remove Credit @CodeFlix_Bots, @rohit_1888
# Ask Doubt on telegram @CodeflixSupport

async def check_admin(filter, client, update):
    try:
        user_id = update.from_user.id       
        return any([user_id == OWNER_ID, await db.admin_exist(user_id)])
    except Exception as e:
        print(f"! Exception in check_admin: {e}")
        return False


async def is_subscribed(client, user_id):
    channel_ids = await db.show_channels()

    if not channel_ids:
        return True

    if user_id == OWNER_ID:
        return True

    for cid in channel_ids:
        if not await is_sub(client, user_id, cid):
            mode = await db.get_channel_mode(cid)
            if mode == "on":
                await asyncio.sleep(2)  # give time for @on_chat_join_request to process
                if await is_sub(client, user_id, cid):
                    continue
            return False

    return True


async def is_sub(client, user_id, channel_id):
    try:
        member = await client.get_chat_member(channel_id, user_id)
        status = member.status
        return status in {
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER
        }

    except UserNotParticipant:
        mode = await db.get_channel_mode(channel_id)
        if mode == "on":
            exists = await db.req_user_exist(channel_id, user_id)
            return exists
        return False

    except Exception as e:
        print(f"[!] Error in is_sub(): {e}")
        return False


async def encode(string):
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes) 
    string = string_bytes.decode("ascii")
    return string

async def get_messages(client, message_ids):
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temb_ids = message_ids[total_messages:total_messages+200]
        try:
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temb_ids
            )
        except FloodWait as e:
            await asyncio.sleep(e.x)
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temb_ids
            )
        except:
            pass
        total_messages += len(temb_ids)
        messages.extend(msgs)
    return messages

async def get_message_id(client, message):
    if message.forward_from_chat:
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
        else:
            return 0
    elif message.forward_sender_name:
        return 0
    elif message.text:
        pattern = "https://t.me/(?:c/)?(.*)/(\d+)"
        matches = re.match(pattern,message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            if f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
        else:
            if channel_id == client.db_channel.username:
                return msg_id
    else:
        return 0


def get_readable_time(seconds: int) -> str:
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time


def get_exp_time(seconds):
    periods = [('days', 86400), ('hours', 3600), ('mins', 60), ('secs', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)} {period_name}'
    return result


async def get_shortlink(url, api, link):
    shortzy = Shortzy(api_key=api, base_site=url)
    link = await shortzy.convert(link)
    return link


# ==================== DUAL VERIFICATION ENGINE ====================

async def check_user_verification(user_id: int) -> tuple[bool, int]:
    """
    यह फंक्शन चेक करता है कि यूजर का वेरिफिकेशन स्टेटस क्या है:
    - Returns (True, 0)  -> अगर यूजर वेरीफाइड है (फ्री एक्सेस)
    - Returns (False, 1) -> अगर Step 1/2 वेरिफिकेशन चाहिए
    - Returns (False, 2) -> अगर Gap Time खत्म हो चुका है और Step 2/2 चाहिए
    """
    if user_id == OWNER_ID or await db.admin_exist(user_id):
        return True, 0

    settings = await db.get_bot_settings()
    verify_mode = settings.get('verify_mode', True)
    if not verify_mode:
        return True, 0

    user_status = await db.get_verify_status(user_id)
    step = user_status.get('step', 0)
    step1_time = user_status.get('step1_time', 0)
    last_date = user_status.get('last_date', '')
    
    current_time = time.time()
    today_str = date.today().isoformat()

    # 1. Midnight Reset Check (रात 12:00 बजे अपने आप रिसेट करने के लिए)
    if last_date != today_str:
        await db.update_verify_status(user_id, step=0, step1_time=0, verify_token="", link="")
        return False, 1

    # 2. Config से गैप टाइमर निकालें
    gap_expire = int(settings.get('verify_expire', VERIFY_EXPIRE))

    # 3. Check Steps
    if step == 0:
        return False, 1  # Step 1 Verification Pending

    elif step == 1:
        # गैप टाइमर चेक करें
        if (current_time - step1_time) < gap_expire:
            return True, 0  # Allowed under Gap Timer!
        else:
            return False, 2 # Gap Time over -> Need Step 2 Verification

    elif step == 2:
        return True, 0  # Fully verified till midnight!

    return False, 1


subscribed = filters.create(is_subscribed)
admin = filters.create(check_admin)
