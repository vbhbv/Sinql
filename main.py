import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ===== إعداد التوكن =====
TOKEN = os.getenv("BOT_TOKEN")  # ضع التوكن في متغير بيئة في Railway

# ===== دالة الترحيب =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 مرحباً بك في بوت تحميل الفيديوهات من فيسبوك 🔥\n\n"
        "أرسل رابط أي فيديو أو ريلز أو ستوري من فيسبوك، وسأقوم بتحميله لك!"
    )

# ===== دالة التحميل =====
def get_facebook_video_url(url):
    """
    تستخدم API خارجي مجاني لاستخراج رابط التحميل.
    يمكن تغييره لاحقًا إلى أداة خاصة بك.
    """
    api_url = "https://fbdownloader.online/api/get.php?url=" + url
    try:
        r = requests.get(api_url)
        if r.status_code == 200 and "download" in r.text:
            data = r.json()
            return data.get("hd", "") or data.get("sd", "")
        return None
    except Exception as e:
        print("Error:", e)
        return None

# ===== عند استلام رابط =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "facebook.com" in text or "fb.watch" in text:
        await update.message.reply_text("⏳ جاري معالجة الرابط وتحميل الفيديو...")
        video_url = get_facebook_video_url(text)
        if video_url:
            await update.message.reply_video(video=video_url, caption="✅ تم التحميل بنجاح!")
        else:
            await update.message.reply_text("❌ لم أستطع استخراج الفيديو، حاول برابط آخر.")
    else:
        await update.message.reply_text("⚠️ أرسل رابط فيديو من فيسبوك فقط.")

# ===== تشغيل البوت =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
