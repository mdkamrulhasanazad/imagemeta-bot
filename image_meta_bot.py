import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import io

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "your_channel")

logging.basicConfig(level=logging.INFO)

def is_subscribed(user_id, context):
    try:
        member = context.bot.get_chat_member(
            chat_id=f"@{CHANNEL_USERNAME}",
            user_id=user_id
        )
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def ask_to_subscribe(update):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 চ্যানেলে যোগ দিন", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ যোগ দিয়েছি", callback_data="check_subscription")]
    ])
    update.message.reply_text(
        "⚠️ এই বট ব্যবহার করতে হলে আগে আমাদের চ্যানেলে যোগ দিন!\n\n"
        "👇 নিচের বাটনে ক্লিক করে চ্যানেলে যোগ দিন, তারপর ✅ বাটন চাপুন।",
        reply_markup=keyboard
    )

def start(update, context):
    user_id = update.effective_user.id
    if not is_subscribed(user_id, context):
        ask_to_subscribe(update)
        return
    update.message.reply_text(
        "👋 স্বাগতম! আমি Image Metadata Bot।\n\n"
        "📸 যেকোনো ছবি পাঠান, আমি তার metadata বের করে দেব।"
    )

def check_subscription(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    if is_subscribed(user_id, context):
        query.answer("✅ ধন্যবাদ! এখন বট ব্যবহার করতে পারবেন।")
        query.message.edit_text(
            "✅ সফলভাবে যোগ দিয়েছেন!\n\n"
            "📸 এখন যেকোনো ছবি পাঠান, আমি metadata বের করে দেব।"
        )
    else:
        query.answer("❌ আপনি এখনো চ্যানেলে যোগ দেননি!", show_alert=True)

def get_gps_info(gps_data):
    gps_info = {}
    for key in gps_data.keys():
        tag_name = GPSTAGS.get(key, key)
        gps_info[tag_name] = gps_data[key]
    try:
        lat = gps_info.get("GPSLatitude")
        lat_ref = gps_info.get("GPSLatitudeRef")
        lon = gps_info.get("GPSLongitude")
        lon_ref = gps_info.get("GPSLongitudeRef")
        if lat and lon:
            def to_degrees(val):
                d, m, s = float(val[0]), float(val[1]), float(val[2])
                return d + (m / 60.0) + (s / 3600.0)
            lat_deg = to_degrees(lat)
            lon_deg = to_degrees(lon)
            if lat_ref == "S":
                lat_deg = -lat_deg
            if lon_ref == "W":
                lon_deg = -lon_deg
            return f"{lat_deg:.6f}, {lon_deg:.6f}"
    except:
        pass
    return None

def extract_metadata(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    info = {
        "📐 রেজোলিউশন": f"{img.width} x {img.height} px",
        "🎨 মোড": img.mode,
        "📁 ফরম্যাট": img.format or "অজানা",
    }
    exif_data = img._getexif()
    gps_coords = None
    if exif_data:
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                gps_coords = get_gps_info(value)
                continue
            important_tags = {
                "Make": "📷 ক্যামেরা ব্র্যান্ড",
                "Model": "📱 ক্যামেরা মডেল",
                "DateTime": "📅 তারিখ ও সময়",
                "DateTimeOriginal": "📅 তোলার তারিখ",
                "ExposureTime": "⏱ এক্সপোজার টাইম",
                "FNumber": "🔆 F-নম্বর",
                "ISOSpeedRatings": "📊 ISO",
                "FocalLength": "🔭 ফোকাল লেন্থ",
                "Flash": "⚡ ফ্ল্যাশ",
                "Software": "💻 সফটওয়্যার",
            }
            if tag in important_tags:
                info[important_tags[tag]] = str(value)
    if gps_coords:
        info["📍 GPS লোকেশন"] = gps_coords
        info["🗺 Google Maps"] = f"https://maps.google.com/?q={gps_coords}"
    return info

def handle_image(update, context):
    user_id = update.effective_user.id
    if not is_subscribed(user_id, context):
        ask_to_subscribe(update)
        return
    update.message.reply_text("⏳ বিশ্লেষণ করছি...")
    try:
        if update.message.document:
            file = context.bot.get_file(update.message.document.file_id)
        elif update.message.photo:
            file = context.bot.get_file(update.message.photo[-1].file_id)
        else:
            update.message.reply_text("❌ ছবি পাঠাতে পারিনি।")
            return
        image_bytes = file.download_as_bytearray()
        metadata = extract_metadata(bytes(image_bytes))
        result = "🔍 *Image Metadata*\n" + "─" * 25 + "\n"
        for key, value in metadata.items():
            result += f"{key}: `{value}`\n"
        update.message.reply_text(result, parse_mode="Markdown")
    except Exception as e:
        update.message.reply_text(f"❌ সমস্যা হয়েছে: {str(e)}")

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(check_subscription, pattern="check_subscription"))
    dp.add_handler(MessageHandler(Filters.photo | Filters.document.image, handle_image))
    print("✅ বট চালু হয়েছে...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
