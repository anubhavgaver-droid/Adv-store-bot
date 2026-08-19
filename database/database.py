import asyncio
import logging
import time
import os
from datetime import datetime, timedelta
import motor.motor_asyncio
from config import DB_URI, DB_NAME, SHORTLINK_URL, SHORTLINK_API, TUT_VID, VERIFY_EXPIRE

logging.basicConfig(level=logging.INFO)

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

def new_user(id):
    return {
        '_id': id,
        'verify_status': {
            'is_verified': False,
            'verified_time': "",
            'verify_token': "",
            'link': ""
        }
    }

class Rohit:
    def __init__(self, DB_URI, DB_NAME):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(DB_URI)
        self.database = self.dbclient[DB_NAME]

        self.channel_data = self.database['channels']
        self.admins_data = self.database['admins']
        self.user_data = self.database['users']
        self.sex_data = self.database['sex']
        self.banned_user_data = self.database['banned_user']
        self.autho_user_data = self.database['autho_user']
        self.del_timer_data = self.database['del_timer']
        self.fsub_data = self.database['fsub']   
        self.rqst_fsub_data = self.database['request_forcesub']
        self.rqst_fsub_Channel_data = self.database['request_forcesub_channel']
        self.multi_batches = self.database['multi_batches']
        self.settings_col = self.database['settings']

    # USER DATA
    async def present_user(self, user_id: int):
        found = await self.user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_user(self, user_id: int):
        await self.user_data.insert_one({'_id': user_id})

    async def full_userbase(self):
        user_docs = await self.user_data.find().to_list(length=None)
        return [doc['_id'] for doc in user_docs]

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})

    # ADMIN DATA
    async def admin_exist(self, admin_id: int):
        found = await self.admins_data.find_one({'_id': admin_id})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})

    async def del_admin(self, admin_id: int):
        if await self.admin_exist(admin_id):
            await self.admins_data.delete_one({'_id': admin_id})

    async def get_all_admins(self):
        users_docs = await self.admins_data.find().to_list(length=None)
        return [doc['_id'] for doc in users_docs]

    # BAN USER DATA
    async def ban_user_exist(self, user_id: int):
        found = await self.banned_user_data.find_one({'_id': user_id})
        return bool(found)

    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})

    async def del_ban_user(self, user_id: int):
        if await self.ban_user_exist(user_id):
            await self.banned_user_data.delete_one({'_id': user_id})

    async def get_ban_users(self):
        users_docs = await self.banned_user_data.find().to_list(length=None)
        return [doc['_id'] for doc in users_docs]

    # AUTO DELETE TIMER
    async def set_del_timer(self, value: int):        
        await self.del_timer_data.update_one({}, {'$set': {'value': value}}, upsert=True)

    async def get_del_timer(self):
        data = await self.del_timer_data.find_one({})
        return data.get('value', 600) if data else 0

    # CHANNEL MANAGEMENT
    async def channel_exist(self, channel_id: int):
        found = await self.fsub_data.find_one({'_id': channel_id})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})

    async def rem_channel(self, channel_id: int):
        if await self.channel_exist(channel_id):
            await self.fsub_data.delete_one({'_id': channel_id})

    async def show_channels(self):
        channel_docs = await self.fsub_data.find().to_list(length=None)
        return [doc['_id'] for doc in channel_docs]

    async def get_channel_mode(self, channel_id: int):
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one({'_id': channel_id}, {'$set': {'mode': mode}}, upsert=True)

    # REQUEST FORCE-SUB MANAGEMENT
    async def req_user(self, channel_id: int, user_id: int):
        try:
            await self.rqst_fsub_Channel_data.update_one(
                {'_id': int(channel_id)},
                {'$addToSet': {'user_ids': int(user_id)}},
                upsert=True
            )
        except Exception as e:
            print(f"[DB ERROR] Failed to add user: {e}")

    async def del_req_user(self, channel_id: int, user_id: int):
        await self.rqst_fsub_Channel_data.update_one({'_id': channel_id}, {'$pull': {'user_ids': user_id}})

    async def req_user_exist(self, channel_id: int, user_id: int):
        try:
            found = await self.rqst_fsub_Channel_data.find_one({
                '_id': int(channel_id),
                'user_ids': int(user_id)
            })
            return bool(found)
        except Exception as e:
            print(f"[DB ERROR] Failed to check request: {e}")
            return False  

    # VERIFICATION MANAGEMENT
    async def db_verify_status(self, user_id):
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('verify_status', default_verify) if user else default_verify

    async def db_update_verify_status(self, user_id, verify):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

    async def update_verify_status(self, user_id, verify_token="", is_verified=False, verified_time=0, link=""):
        current = await self.db_verify_status(user_id)
        current['verify_token'] = verify_token
        current['is_verified'] = is_verified
        current['verified_time'] = verified_time
        current['link'] = link
        await self.db_update_verify_status(user_id, current)

    # DYNAMIC BOT SETTINGS MANAGEMENT
    async def get_bot_settings(self):
        settings = await self.settings_col.find_one({'_id': 'bot_settings'})
        if not settings:
            default_settings = {
                '_id': 'bot_settings',
                'verify_mode': True,
                'shortlink_url': SHORTLINK_URL,
                'shortlink_api': SHORTLINK_API,
                'tut_vid': TUT_VID,
                'verify_expire': VERIFY_EXPIRE,
                'fsub_mode': 'NORMAL'
            }
            await self.settings_col.insert_one(default_settings)
            return default_settings
        return settings

    async def update_bot_setting(self, key, value):
        await self.settings_col.update_one({'_id': 'bot_settings'}, {'$set': {key: value}}, upsert=True)

db = Rohit(DB_URI, DB_NAME)
