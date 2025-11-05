import os
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 بوت تحميل الفيديوهات من فيسبوك 🔥\n\n"
        "أرسل رابط فيديو أو ريلز من فيسبوك وسأقوم بتحميله لك بجودة عالية 💥"
    )

async def download_facebook_video(url: str):
    output_path = "video.mp4"
    ydl_opts = {
        "outtmpl": output_path,
        "format": "best[ext=mp4]/best",
        "quiet": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path
    except Exception as e:
        print(f"❌ خطأ أثناء التحميل: {e}")
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "facebook.com" not in url and "fb.watch" not in url:
        await update.message.reply_text("⚠️ أرسل رابط فيديو من فيسبوك فقط.")
        return

    await update.message.reply_text("⏳ جاري تحميل الفيديو...")

    video_path = await asyncio.to_thread(download_facebook_video, url)

    if video_path and os.path.exists(video_path):
        await update.message.reply_video(video=open(video_path, "rb"), caption="✅ تم التحميل بنجاح!")
        os.remove(video_path)
    else:
        await update.message.reply_text("❌ لم أستطع تحميل الفيديو، حاول برابط آخر أو تحقق أنه عام.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🚀 البوت يعمل الآن...")
    asyncio.run(app.bot.delete_webhook(drop_pending_updates=True))
    app.run_polling()

if __name__ == "__main__":
    main()
