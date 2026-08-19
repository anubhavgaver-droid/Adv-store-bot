import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from bot import Bot
from helper_func import encode, admin

def extract_message_id(message: Message):
    """
    Forwarded message ya Telegram link se message ID extract karta hai.
    """
    if message.forward_from_chat:
        return message.forward_from_message_id
    elif message.text and "t.me/" in message.text:
        text = message.text.strip()
        try:
            return int(text.split("/")[-1].split("?")[0])
        except Exception:
            return None
    return None


@Bot.on_message(filters.private & admin & filters.command('batch'))
async def batch(client: Client, message: Message):
    # --- FIRST MESSAGE ---
    while True:
        try:
            first_message = await client.ask(
                text="Forward The Batch First Message From your Batch Channel (With Forward Tag).. or Give Me Batch First Message link from your batch channel",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | filters.text),
                timeout=60
            )
        except Exception:
            return

        if first_message.text and first_message.text.startswith("/"):
            await first_message.reply("Process Cancelled!")
            return

        f_msg_id = extract_message_id(first_message)
        if f_msg_id:
            break
        else:
            await first_message.reply("❌ Invalid Link or Forwarded Message! Please try again.", quote=True)
            continue

    # --- LAST MESSAGE ---
    while True:
        try:
            second_message = await client.ask(
                text="Forward The Batch Last Message From your Batch Channel (With Forward Tag).. or Give Me Batch Last Message link from your batch channel",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | filters.text),
                timeout=60
            )
        except Exception:
            return

        if second_message.text and second_message.text.startswith("/"):
            await second_message.reply("Process Cancelled!")
            return

        s_msg_id = extract_message_id(second_message)
        if s_msg_id:
            break
        else:
            await second_message.reply("❌ Invalid Link or Forwarded Message! Please try again.", quote=True)
            continue

    # Link Generation
    string = f"get-{f_msg_id * abs(client.db_channel.id)}-{s_msg_id * abs(client.db_channel.id)}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"
    
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await second_message.reply_text(f"<b>Here is your link</b>\n\n{link}", quote=True, reply_markup=reply_markup)


@Bot.on_message(filters.private & admin & filters.command('genlink'))
async def link_generator(client: Client, message: Message):
    while True:
        try:
            channel_message = await client.ask(
                text="Send A Message For To Get Your Shareable Link",
                chat_id=message.from_user.id,
                filters=(filters.forwarded | filters.text | filters.media),
                timeout=60
            )
        except Exception:
            return

        if channel_message.text and channel_message.text.startswith("/"):
            await channel_message.reply("Process Cancelled!")
            return

        msg_id = extract_message_id(channel_message)
        
        # Agar link ya forward hai toh id use karein, warna file/msg ko DB Channel mein copy karein
        if msg_id:
            final_id = msg_id
            break
        else:
            try:
                post_msg = await channel_message.copy(chat_id=client.db_channel.id, disable_notification=True)
                final_id = post_msg.id
                break
            except Exception as e:
                await channel_message.reply(f"❌ Error saving message: {e}", quote=True)
                continue

    base64_string = await encode(f"get-{final_id * abs(client.db_channel.id)}")
    link = f"https://t.me/{client.username}?start={base64_string}"
    
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await channel_message.reply_text(f"<b>Here is your link</b>\n\n{link}", quote=True, reply_markup=reply_markup)


@Bot.on_message(filters.private & admin & filters.command("custom_batch"))
async def custom_batch(client: Client, message: Message):
    collected = []
    STOP_KEYBOARD = ReplyKeyboardMarkup([["STOP"]], resize_keyboard=True)

    await message.reply("Send all messages you want to include in batch.\n\nPress STOP when you're done.", reply_markup=STOP_KEYBOARD)

    while True:
        try:
            user_msg = await client.ask(
                chat_id=message.chat.id,
                text="Waiting for files/messages...\nPress STOP to finish.",
                timeout=60
            )
        except asyncio.TimeoutError:
            break

        if user_msg.text and user_msg.text.strip().upper() == "STOP":
            break

        try:
            sent = await user_msg.copy(client.db_channel.id, disable_notification=True)
            collected.append(sent.id)
        except Exception as e:
            await message.reply(f"❌ Failed to store a message:\n<code>{e}</code>")
            continue

    await message.reply("✅ Batch collection complete.", reply_markup=ReplyKeyboardRemove())

    if not collected:
        await message.reply("❌ No messages were added to batch.")
        return

    start_id = collected[0] * abs(client.db_channel.id)
    end_id = collected[-1] * abs(client.db_channel.id)
    string = f"get-{start_id}-{end_id}"
    base64_string = await encode(string)
    link = f"https://t.me/{client.username}?start={base64_string}"

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔁 Share URL", url=f'https://telegram.me/share/url?url={link}')]])
    await message.reply(f"<b>Here is your custom batch link:</b>\n\n{link}", reply_markup=reply_markup)
