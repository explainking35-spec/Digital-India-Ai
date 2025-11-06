import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from bson import ObjectId
from db import users, payments
from datetime import datetime, timedelta

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))

app = Client('admin-bot', api_id=API_ID, api_hash=API_HASH, bot_token=ADMIN_BOT_TOKEN)


# Approve / Reject बटन क्लिक हैंडल करना
@app.on_callback_query(filters.regex(r'^(approve|reject):'))
async def handle_approval(c, cb):
    action, payment_id = cb.data.split(':')
    payment = payments.find_one({"_id": ObjectId(payment_id)})
    if not payment:
        await cb.answer("⚠️ Payment record नहीं मिला।", show_alert=True)
        return

    user_id = payment['user_id']
    if action == 'approve':
        # Subscription activate
        expiry = datetime.utcnow() + timedelta(days=30)
        users.update_one(
            {"user_id": user_id},
            {"$set": {"expiry": expiry, "active": True, "trial": False}},
            upsert=True
        )
        payments.update_one({"_id": ObjectId(payment_id)}, {"$set": {"status": "approved"}})

        # User को message
        try:
            await c.send_message(
                user_id,
                "🎉 आपकी पेमेंट verify हो गई है!\nअब आपका subscription 30 दिनों के लिए सक्रिय है।"
            )
        except Exception:
            pass

        await cb.message.edit_caption(
            caption=cb.message.caption + "\n\n✅ *Payment Approved by Admin*",
            reply_markup=None
        )
        await cb.answer("✅ Payment approved", show_alert=True)

    elif action == 'reject':
        payments.update_one({"_id": ObjectId(payment_id)}, {"$set": {"status": "rejected"}})

        try:
            await c.send_message(
                user_id,
                "❌ आपकी पेमेंट reject कर दी गई है। कृपया सही screenshot और UTR भेजें।"
            )
        except Exception:
            pass

        await cb.message.edit_caption(
            caption=cb.message.caption + "\n\n❌ *Payment Rejected by Admin*",
            reply_markup=None
        )
        await cb.answer("❌ Payment rejected", show_alert=True)


@app.on_message(filters.command("start") & filters.user(OWNER_ID))
async def start(c, m):
    await m.reply("👑 Admin Panel चालू है!\nApprove / Reject requests यहीं आएंगी।")


if __name__ == "__main__":
    app.run()
