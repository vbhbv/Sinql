import os
import logging
import shutil
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
from docx import Document
from docx.shared import Inches

# استيراد دالة التحويل من الملف الجديد الذي أنشأناه
from document_converter import convert_pdf_to_docx

# إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

from config import TOKEN

DOWNLOAD_DIR = "temp_files"

def تنظيف_المجلد_المؤقت():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

تنظيف_المجلد_المؤقت()

def clean_filename(name):
    return re.sub(r'[\/*?:"<>|]', '', name).strip()

# 1. دالة الـ Start وتجهيز الأزرار الرئيسية منفصلة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("📸 قسم تحويل الصور", callback_data="section_photos")],
        [InlineKeyboardButton("📄 PDF 🔄 Word (تحويل المستندات)", callback_data="section_docs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 أهلاً بك في بوت أدوات الملفات المتكامل!\n\n"
        "الرجاء اختيار القسم الذي تريد العمل عليه من الأزرار بالأسفل:",
        reply_markup=reply_markup
    )

# دالة التحكم في الأزرار التفاعلية وقائمة التنقل
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    images = context.user_data.get('user_images', [])
    custom_name = context.user_data.get('custom_filename', f"converted_{user_id}")

    # التنقل بين الأقسام الرئيسية
    if query.data == "section_photos":
        context.user_data['current_mode'] = 'photos'
        await query.edit_message_text("📸 **أنت الآن في قسم الصور.**\n\nمن فضلك قم بإرسال الصور التي تريد تجميعها وتحويلها (صورة واحدة أو عدة صور معاً) وسأقوم بطلب الاسم منك فوراً.")
        
    elif query.data == "section_docs":
        keyboard = [
            [InlineKeyboardButton("إلى Word ⬅️ PDF تحويل", callback_data="pdf_to_word")],
            [InlineKeyboardButton("إلى PDF ⬅️ Word تحويل", callback_data="word_to_pdf")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]
        await query.edit_message_text("📄 **قسم تحويل المستندات**\n\nاختر نوع التحويل الذي تريده:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "main_menu":
        context.user_data.clear()
        keyboard = [
            [InlineKeyboardButton("📸 قسم تحويل الصور", callback_data="section_photos")],
            [InlineKeyboardButton("📄 PDF 🔄 Word (تحويل المستندات)", callback_data="section_docs")]
        ]
        await query.edit_message_text("الرجاء اختيار القسم الذي تريد العمل عليه من الأزرار بالأسفل:", reply_markup=InlineKeyboardMarkup(keyboard))

    # تحديد نوع تحويل المستندات
    elif query.data in ["pdf_to_word", "word_to_pdf"]:
        context.user_data['doc_action'] = query.data
        if query.data == "pdf_to_word":
            await query.edit_message_text("⏳ ممتاز، أنا الآن بانتظار أن ترسل لي ملف الـ **PDF** لتحويله إلى Word...")
        else:
            await query.edit_message_text("⏳ ممتاز، أنا الآن بانتظار أن ترسل لي ملف الـ **Word (.docx)** لتحويله إلى PDF...")

    # معالجة تجميع الصور المنفصلة بناء على ضغط الزر
    elif query.data == "to_pdf":
        if not images:
            await query.edit_message_text("❌ لم يتم العثور على صور. أرسل الصور مجدداً.")
            return
        await query.edit_message_text("⏳ جاري إنشاء ملف PDF المخصص وتجميع الصور...")
        pdf_path = os.path.join(DOWNLOAD_DIR, f"{custom_name}.pdf")
        try:
            img_list = [Image.open(img).convert('RGB') for img in images if os.path.exists(img)]
            if img_list:
                img_list[0].save(pdf_path, save_all=True, append_images=img_list[1:])
                with open(pdf_path, 'rb') as f:
                    await query.message.reply_document(document=f, filename=f"{custom_name}.pdf")
            else:
                await query.message.reply_text("❌ حدث خطأ، لم نجد الصور.")
        except Exception as e:
            await query.message.reply_text(f"❌ فشل إنشاء ملف PDF: {str(e)}")
        finally:
            clean_user_data(context, images, pdf_path)

    elif query.data == "to_docx":
        if not images:
            await query.edit_message_text("❌ لم يتم العثور على صور. أرسل الصور مجدداً.")
            return
        await query.edit_message_text("⏳ جاري إنشاء ملف Word المخصص وتنسيق الصور...")
        docx_path = os.path.join(DOWNLOAD_DIR, f"{custom_name}.docx")
        try:
            doc = Document()
            for section in doc.sections:
                section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Inches(0.5)
            for img_path in images:
                if os.path.exists(img_path):
                    doc.add_picture(img_path, width=Inches(6.5))
            doc.save(docx_path)
            with open(docx_path, 'rb') as f:
                await query.message.reply_document(document=f, filename=f"{custom_name}.docx")
        except Exception as e:
            await query.message.reply_text(f"❌ فشل إنشاء ملف Word: {str(e)}")
        finally:
            clean_user_data(context, images, docx_path)
        
    elif query.data == "clear":
        for img in images:
            if os.path.exists(img): os.remove(img)
        context.user_data.clear()
        await query.edit_message_text("🗑 تم مسح كل شيء. يمكنك استخدام أمر /start للبدء من جديد.")

# دالة الجدولة لطلب اسم ملف الصور
async def ask_for_filename(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.user_id
    chat_id = job.chat_id
    user_data = context.application.user_data.get(user_id, {})
    images_count = len(user_data.get('user_images', []))
    
    if images_count == 0: return
    user_data['waiting_for_name'] = True
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"📥 تم استلام ({images_count}) صور.\n✍️ **من فضلك أرسل الآن الاسم الذي تريده للملف (بدون صيغة):**"
    )

# استقبال الصور
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    # إجبار المستخدم على الدخول لقسم الصور أولاً لمنع التشتت
    if context.user_data.get('current_mode') != 'photos':
        await update.message.reply_text("⚠️ يرجى الضغط على زر '📸 قسم تحويل الصور' من القائمة الرئيسية أولاً قبل إرسال الصور.")
        return

    try:
        if 'user_images' not in context.user_data:
            context.user_data['user_images'] = []
        context.user_data['waiting_for_name'] = False
        
        photo_file = await update.message.photo[-1].get_file()
        file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{len(context.user_data['user_images'])}.jpg")
        await photo_file.download_to_drive(file_path)
        context.user_data['user_images'].append(file_path)
        
        current_jobs = context.job_queue.get_jobs_by_name(f"menu_{user_id}")
        for job in current_jobs: job.schedule_removal()
            
        context.job_queue.run_once(ask_for_filename, when=1.0, user_id=user_id, chat_id=chat_id, name=f"menu_{user_id}")
    except Exception as e:
        logger.error(f"Error handling photo: {str(e)}")

# استقبال النصوص لأسماء الملفات
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if context.user_data.get('waiting_for_name') and context.user_data.get('user_images'):
        filename = clean_filename(update.message.text)
        if not filename:
            await update.message.reply_text("⚠️ اسم غير صالح، أرسل اسماً آخر:")
            return
            
        context.user_data['custom_filename'] = filename
        context.user_data['waiting_for_name'] = False
        
        # تقديم أزرار منفصلة تماماً ليفعل كل زر عمله بشكل مستقل
        keyboard = [
            [InlineKeyboardButton("📄 إنشاء ملف PDF الآن", callback_data="to_pdf")],
            [InlineKeyboardButton("📝 إنشاء ملف Word الآن", callback_data="to_docx")],
            [InlineKeyboardButton("❌ إلغاء والبدء من جديد", callback_data="clear")]
        ]
        await update.message.reply_text(
            f"✅ تم اعتماد الاسم: **{filename}**\nاضغط على الزر الذي تريده للبدء فوراً:",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("🤖 الرجاء استخدام الأزرار التفاعلية للتنقل بين وظائف البوت المتاحة.")

# معالجة ملفات المستندات الواردة (PDF أو Word) من خلال استدعاء الملف الجديد
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name
    doc_action = context.user_data.get('doc_action')

    if not doc_action:
        await update.message.reply_text("⚠️ من فضلك اختر نوع التحويل أولاً من زر المستندات في القائمة الرئيسية.")
        return

    if doc_action == "pdf_to_word" and file_name.lower().endswith('.pdf'):
        wait_msg = await update.message.reply_text("⏳ جاري تحويل ملف الـ PDF إلى Word، يرجى الانتظار...")
        pdf_path = os.path.join(DOWNLOAD_DIR, f"{update.message.from_user.id}_{file_name}")
        docx_path = pdf_path.replace('.pdf', '.docx')
        
        try:
            file = await doc.get_file()
            await file.download_to_drive(pdf_path)
            
            # استدعاء الدالة من الملف الجديد الخاص بنا
            success = await convert_pdf_to_docx(pdf_path, docx_path)
            if success and os.path.exists(docx_path):
                with open(docx_path, 'rb') as f:
                    await update.message.reply_document(document=f, filename=os.path.basename(docx_path))
            else:
                await update.message.reply_text("❌ عذراً، فشل تحويل الملف البرمجي.")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")
        finally:
            await wait_msg.delete()
            if os.path.exists(pdf_path): os.remove(pdf_path)
            if os.path.exists(docx_path): os.remove(docx_path)
            context.user_data.clear()

    elif doc_action == "word_to_pdf" and file_name.lower().endswith('.docx'):
        await update.message.reply_text("⚠️ ميزة تحويل Word إلى PDF تتطلب حزم سطر أوامر LibreOffice إضافية على السيرفر، الميزة قيد التطوير حالياً في السيرفر.")
    else:
        await update.message.reply_text("❌ صيغة الملف المرسل لا تتوافق مع الخيار الذي حددته سابقاً.")

def clean_user_data(context, images, result_file):
    for img in images:
        if os.path.exists(img): os.remove(img)
    if os.path.exists(result_file): os.remove(result_file)
    context.user_data.clear()

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("🤖 تم ربط الملف الجديد وفصل العمليات والأزرار بنجاح...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
