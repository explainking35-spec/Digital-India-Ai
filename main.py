import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from db import create_trial, is_active, add_payment_record
from utils.qr_generator import generate_upi_qr

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')
OWNER_ID = int(os.getenv('OWNER_ID'))
UPI_ID = os.getenv('UPI_ID')
AMOUNT = int(os.getenv('SUBSCRIPTION_AMOUNT', 49))

app = Client('copy-bot', api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
SOURCE_CHAT = CHANNEL_USERNAME
TARGET_CHAT = CHANNEL_USERNAME


async def is_member_of_channel(client, user_id):
    try:
        await client.get_chat_member(CHANNEL_USERNAME, user_id)
        return True
    except Exception:
        return False


@app.on_message(filters.command('start'))
async def start(c, m):
    user = m.from_user
    if not await is_member_of_channel(c, user.id):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton('🔗 चैनल जॉइन करें', url=f'https://t.me/{CHANNEL_USERNAME.strip("@")}')]
        ])
        await m.reply("🚫 कृपया पहले चैनल जॉइन करें ताकि आप बॉट का उपयोग कर सकें।", reply_markup=kb)
        return

    await create_trial(user.id, user.username or '')
    await m.reply("✅ आपका 7 दिन का फ्री ट्रायल शुरू हो गया है!\nअब आप बॉट की सुविधाएँ आज़मा सकते हैं।")


@app.on_message(filters.command('subscribe'))
async def subscribe(c, m):
    user = m.from_user
    qr_image = generate_upi_qr(UPI_ID, AMOUNT)
    caption = (
        f"💳 *Subscription Payment*\n\n"
        f"🔸 Amount: ₹{AMOUNT}\n"
        f"🔹 Payment UPI ID: `{UPI_ID}`\n"
        f"👤 User: @{user.username or user.id}\n\n"
        f"कृपया पेमेंट के बाद Screenshot और UTR नंबर भेजें।"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ Payment Done - Proof भेजें', callback_data='paid')]
    ])
    await c.send_photo(m.chat.id, photo=qr_image, caption=caption, reply_markup=kb)


@app.on_callback_query(filters.regex('paid'))
async def ask_for_receipt(c, cb):
    await cb.message.reply('कृपया Payment Screenshot और UTR नंबर भेजें (UTR caption में लिखें)।')
    await cb.answer()


@app.on_message(filters.photo & filters.private)
async def receive_payment_screenshot(c, m):
    user = m.from_user
    caption = m.caption or ''
    utr = None
    for part in caption.split():
        if len(part) >= 6 and any(ch.isdigit() for ch in part):
            utr = part
            break

    file_id = m.photo.file_id
    payment_id = await add_payment_record(user.id, AMOUNT, utr or 'N/A', file_id)

    text = (
        f"🔔 *New Payment Request*\n\n"
        f"👤 User: @{user.username or user.id}\n"
        f"💰 Amount: ₹{AMOUNT}\n"
        f"🧾 UTR: {utr or 'N/A'}\n"
        f"🆔 PaymentID: {payment_id}"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('✅ Approve', callback_data=f'approve:{payment_id}'),
         InlineKeyboardButton('❌ Reject', callback_data=f'reject:{payment_id}')]
    ])

    await c.send_photo(OWNER_ID, photo=file_id, caption=text, reply_markup=kb)
    await m.reply("✅ आपकी पेमेंट रिक्वेस्ट भेज दी गई है। Admin verify करने के बाद approve/reject करेगा।")


@app.on_message(filters.chat(SOURCE_CHAT) & ~filters.service)
async def handle_source_message(c, m):
    try:
        if m.text:
            await c.send_message(TARGET_CHAT, m.text)
        elif m.photo:
            await c.send_photo(TARGET_CHAT, m.photo.file_id, caption=m.caption or "")
        elif m.video:
            await c.send_video(TARGET_CHAT, m.video.file_id, caption=m.caption or "")
        elif m.document:
            await c.send_document(TARGET_CHAT, m.document.file_id, caption=m.caption or "")
        else:
            await c.copy_message(TARGET_CHAT, m.chat.id, m.id)
    except Exception as e:
        print("⚠️ Copy error:", e)


if __name__ == "__main__":
    app.run()
