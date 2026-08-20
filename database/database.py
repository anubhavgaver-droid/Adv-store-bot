import logging
import motor.motor_asyncio
from config import (
    DB_URI, 
    DB_NAME, 
    SHORTLINK_URL, 
    SHORTLINK_API, 
    TUT_VID, 
    VERIFY_EXPIRE,
    START_MSG,
    START_PIC,
    UPI_ID,
    QR_PIC,
    PROTECT_CONTENT
)

logging.basicConfig(level=logging.INFO)

default_verify = {
    'is_verified': False,
    'verified_time': 0,
    'verify_token': "",
    'link': ""
}

class Rohit:
    def __init__(self, db_uri: str, db_name: str):
        self.dbclient = motor.motor_asyncio.AsyncIOMotorClient(db_uri)
        self.database = self.dbclient[db_name]

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

    # ================= USER DATA =================
    async def present_user(self, user_id: int) -> bool:
        found = await self.user_data.find_one({'_id': user_id}, {'_id': 1})
        return bool(found)

    async def add_user(self, user_id: int):
        if not await self.present_user(user_id):
            await self.user_data.insert_one({'_id': user_id})

    async def full_userbase(self) -> list:
        user_docs = await self.user_data.find({}, {'_id': 1}).to_list(length=None)
        return [doc['_id'] for doc in user_docs]

    async def del_user(self, user_id: int):
        await self.user_data.delete_one({'_id': user_id})

    # ================= ADMIN DATA =================
    async def admin_exist(self, admin_id: int) -> bool:
        found = await self.admins_data.find_one({'_id': admin_id}, {'_id': 1})
        return bool(found)

    async def add_admin(self, admin_id: int):
        if not await self.admin_exist(admin_id):
            await self.admins_data.insert_one({'_id': admin_id})

    async def del_admin(self, admin_id: int):
        await self.admins_data.delete_one({'_id': admin_id})

    async def get_all_admins(self) -> list:
        users_docs = await self.admins_data.find({}, {'_id': 1}).to_list(length=None)
        return [doc['_id'] for doc in users_docs]

    # ================= BAN USER DATA =================
    async def ban_user_exist(self, user_id: int) -> bool:
        found = await self.banned_user_data.find_one({'_id': user_id}, {'_id': 1})
        return bool(found)

    async def add_ban_user(self, user_id: int):
        if not await self.ban_user_exist(user_id):
            await self.banned_user_data.insert_one({'_id': user_id})

    async def del_ban_user(self, user_id: int):
        await self.banned_user_data.delete_one({'_id': user_id})

    async def get_ban_users(self) -> list:
        users_docs = await self.banned_user_data.find({}, {'_id': 1}).to_list(length=None)
        return [doc['_id'] for doc in users_docs]

    # ================= AUTO DELETE TIMER =================
    async def set_del_timer(self, value: int):        
        await self.del_timer_data.update_one({}, {'$set': {'value': value}}, upsert=True)

    async def get_del_timer(self) -> int:
        data = await self.del_timer_data.find_one({})
        return data.get('value', 600) if data else 600

    # ================= CHANNEL MANAGEMENT =================
    async def channel_exist(self, channel_id: int) -> bool:
        found = await self.fsub_data.find_one({'_id': channel_id}, {'_id': 1})
        return bool(found)

    async def add_channel(self, channel_id: int):
        if not await self.channel_exist(channel_id):
            await self.fsub_data.insert_one({'_id': channel_id})

    async def rem_channel(self, channel_id: int):
        await self.fsub_data.delete_one({'_id': channel_id})

    async def show_channels(self) -> list:
        channel_docs = await self.fsub_data.find({}, {'_id': 1}).to_list(length=None)
        return [doc['_id'] for doc in channel_docs]

    async def get_channel_mode(self, channel_id: int) -> str:
        data = await self.fsub_data.find_one({'_id': channel_id})
        return data.get("mode", "off") if data else "off"

    async def set_channel_mode(self, channel_id: int, mode: str):
        await self.fsub_data.update_one(
            {'_id': channel_id},
            {'$set': {'mode': mode}},
            upsert=True
        )

    # ================= REQUEST FORCE-SUB MANAGEMENT =================
    async def req_user_exist(self, channel_id: int, user_id: int) -> bool:
        found = await self.rqst_fsub_data.find_one({'channel_id': channel_id, 'user_id': user_id})
        return bool(found)

    async def add_req_user(self, channel_id: int, user_id: int):
        if not await self.req_user_exist(channel_id, user_id):
            await self.rqst_fsub_data.insert_one({'channel_id': channel_id, 'user_id': user_id})

    async def del_req_user(self, channel_id: int, user_id: int):
        await self.rqst_fsub_data.delete_one({'channel_id': channel_id, 'user_id': user_id})

    async def del_req_user_all(self, user_id: int):
        await self.rqst_fsub_data.delete_many({'user_id': user_id})

    # ================= VERIFICATION MANAGEMENT =================
    async def db_verify_status(self, user_id: int) -> dict:
        user = await self.user_data.find_one({'_id': user_id})
        return user.get('verify_status', default_verify) if user else default_verify

    async def db_update_verify_status(self, user_id: int, verify: dict):
        await self.user_data.update_one({'_id': user_id}, {'$set': {'verify_status': verify}})

    async def get_verify_status(self, user_id: int) -> dict:
        return await self.db_verify_status(user_id)

    async def update_verify_status(self, user_id: int, verify_token="", is_verified=False, verified_time=0, link=""):
        current = await self.db_verify_status(user_id)
        current.update({
            'verify_token': verify_token,
            'is_verified': is_verified,
            'verified_time': verified_time,
            'link': link
        })
        await self.db_update_verify_status(user_id, current)

    async def set_verify_count(self, user_id: int, count: int):
        await self.sex_data.update_one({'_id': user_id}, {'$set': {'verify_count': count}}, upsert=True)

    async def get_verify_count(self, user_id: int) -> int:
        user = await self.sex_data.find_one({'_id': user_id})
        return user.get('verify_count', 0) if user else 0

    async def reset_all_verify_counts(self):
        await self.sex_data.update_many({}, {'$set': {'verify_count': 0}})

    async def get_total_verify_count(self) -> int:
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$verify_count"}}}]
        result = await self.sex_data.aggregate(pipeline).to_list(length=1)
        return result[0]["total"] if result else 0

    # ================= MULTI-BATCH MANAGEMENT =================
    async def get_multi_batch(self, batch_id: str):
        return await self.multi_batches.find_one({"batch_id": batch_id})

    async def create_multi_batch(self, batch_id: str):
        batch = await self.get_multi_batch(batch_id)
        if not batch:
            await self.multi_batches.insert_one({"batch_id": batch_id, "ranges": []})

    async def add_range_to_multi_batch(self, batch_id: str, new_range: dict):
        await self.multi_batches.update_one({"batch_id": batch_id}, {"$push": {"ranges": new_range}})

    async def update_multi_batch_ranges(self, batch_id: str, ranges: list):
        await self.multi_batches.update_one({"batch_id": batch_id}, {"$set": {"ranges": ranges}})

    # ================= DYNAMIC BOT SETTINGS MANAGEMENT =================
    async def get_bot_settings(self) -> dict:
        settings = await self.settings_col.find_one({'_id': 'bot_settings'})
        if not settings:
            default_settings = {
                '_id': 'bot_settings',
                'verify_mode': True,
                'shortlink_url': SHORTLINK_URL,
                'shortlink_api': SHORTLINK_API,
                'tut_vid': TUT_VID,
                'verify_expire': VERIFY_EXPIRE,
                'fsub_mode': 'NORMAL',
                'start_msg': START_MSG,
                'start_pic': START_PIC,
                'start_pic_spoiler': False,
                'upi_id': UPI_ID,
                'qr_pic': QR_PIC,
                'premium_plan_text': "",
                'protect_content': PROTECT_CONTENT
            }
            await self.settings_col.insert_one(default_settings)
            return default_settings
        return settings

    async def update_bot_setting(self, key, value):
        await self.settings_col.update_one(
            {'_id': 'bot_settings'},
            {'$set': {key: value}},
            upsert=True
        )

db = Rohit(DB_URI, DB_NAME)
