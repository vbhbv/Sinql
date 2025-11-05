import os
import yt_dlp
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")

# ===== رسالة البدء =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 مرحباً بك في بوت تحميل الفيديوهات من فيسبوك 🔥\n\n"
        "أرسل لي أي رابط من فيسبوك وسأحمله لك 💥"
    )

# ===== دالة التحميل =====
def download_video(url: str):
    output_path = "video.mp4"
    ydl_opts = {
        "outtmpl": output_path,
        "quiet": True,
        "format": "best[ext=mp4]/best"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    except Exception as e:
        print(f"❌ خطأ أثناء التحميل: {e}")
        return None

# ===== عند استقبال رابط =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "facebook.com" not in text and "fb.watch" not in text:
        await update.message.reply_text("⚠️ أرسل لي رابط فيسبوك فقط.")
        return

    await update.message.reply_text("⏳ جاري تحميل الفيديو...")

    video_path = await asyncio.to_thread(download_video, text)

    if video_path and os.path.exists(video_path):
        await update.message.reply_video(video=open(video_path, "rb"), caption="✅ تم التحميل بنجاح!")
        os.remove(video_path)
    else:
        await update.message.reply_text("❌ لم أستطع تحميل الفيديو. تأكد أن الرابط عام.")

# ===== التشغيل =====
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
