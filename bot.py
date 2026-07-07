import os
import logging
import shutil
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
from docx import Document
from docx.shared import Inches

# استيراد دوال التحويل السريعة من الملف الفرعي
from document_converter import convert_pdf_to_docx, convert_docx_to_pdf

# إعداد السجلات (Logging) لمراقبة أداء البوت في ريلواي
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

from config import TOKEN

# المجلد المؤقت الخاص بالملفات والصور
DOWNLOAD_DIR = "temp_files"

def تنظيف_المجلد_المؤقت():
    """تصفير مجلد الملفات عند إقلاع البوت لضمان عدم تراكم أي مخلفات"""
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

تنظيف_المجلد_المؤقت()

def clean_filename(name):
    """تنظيف اسم الملف من أي رموز قد تسبب مشاكل في أنظمة التشغيل"""
    return re.sub(r'[\/*?:"<>|]', '', name).strip()

# 1. دالة الترحيب والقائمة الرئيسية
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

# 2. دالة التحكم في الأزرار التفاعلية وقائمة التنقل والتحويل
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    images = context.user_data.get('user_images', [])
    custom_name = context.user_data.get('custom_filename', f"converted_{user_id}")

    # التنقل إلى قسم الصور
    if query.data == "section_photos":
        context.user_data['current_mode'] = 'photos'
        await query.edit_message_text(
            "📸 **أنت الآن في قسم الصور.**\n\n"
            "من فضلك قم بإرسال الصور التي تريد تجميعها وتحويلها (صورة واحدة أو عدة صور معاً) وسأقوم بطلب الاسم منك فوراً واقترح عليك خيارات التحويل."
        )
        
    # التنقل إلى قسم المستندات
    elif query.data == "section_docs":
        keyboard = [
            [InlineKeyboardButton("إلى Word ⬅️ PDF تحويل", callback_data="pdf_to_word")],
            [InlineKeyboardButton("إلى PDF ⬅️ Word تحويل", callback_data="word_to_pdf")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "📄 **قسم تحويل المستندات**\n\nاختر نوع التحويل الذي تريده:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # العودة للقائمة الرئيسية
    elif query.data == "main_menu":
        context.user_data.clear()
        keyboard = [
            [InlineKeyboardButton("📸 قسم تحويل الصور", callback_data="section_photos")],
            [InlineKeyboardButton("📄 PDF 🔄 Word (تحويل المستندات)", callback_data="section_docs")]
        ]
        await query.edit_message_text(
            "الرجاء اختيار القسم الذي تريد العمل عليه من الأزرار بالأسفل:", 
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # تحديد نوع حركة المستند المطلوبة
    elif query.data in ["pdf_to_word", "word_to_pdf"]:
        context.user_data['doc_action'] = query.data
        if query.data == "pdf_to_word":
            await query.edit_message_text("⏳ ممتاز، أنا الآن بانتظار أن ترسل لي ملف الـ **PDF** لتحويله إلى Word...")
        else:
            await query.edit_message_text("⏳ ممتاز، أنا الآن بانتظار أن ترسل لي ملف الـ **Word (.docx)** لتحويله إلى PDF...")

    # تحويل الصور المجمعة إلى ملف PDF
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
                await query.message.reply_text("❌ حدث خطأ، لم نجد الصور على الخادم.")
        except Exception as e:
            await query.message.reply_text(f"❌ فشل إنشاء ملف PDF: {str(e)}")
        finally:
            clean_user_data(context, images, pdf_path)

    # تحويل الصور المجمعة إلى ملف Word (Docx) منسق الهوامش والأبعاد
    elif query.data == "to_docx":
        if not images:
            await query.edit_message_text("❌ لم يتم العثور على صور. أرسل الصور مجدداً.")
            return
        await query.edit_message_text("⏳ جاري إنشاء ملف Word المخصص وتنسيق الصور...")
        docx_path = os.path.join(DOWNLOAD_DIR, f"{custom_name}.docx")
        try:
            doc = Document()
            # ضبط الهوامش القياسية الآمنة لمنع تمدد الصور خارج الورقة
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
        
    # خيار مسح الصور والتصفير للبدء من جديد
    elif query.data == "clear":
        for img in images:
            if os.path.exists(img): os.remove(img)
        context.user_data.clear()
        await query.edit_message_text("🗑 تم مسح كل شيء بنجاح. يمكنك استخدام أمر /start للبدء من جديد.")

# 3. دالة الجدولة لطلب اسم ملف الصور بعد توقف الإرسال
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
        text=f"📥 تم استلام ({images_count}) صور بنجاح.\n\n✍️ **من فضلك أرسل الآن الاسم الذي تريده للملف النهائي (بدون صيغة):**"
    )

# 4. دالة استقبال وتخزين الصور
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    # توجيه أمني للتأكد من أن المستخدم اختار قسم الصور أولاً
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
        
        # تجميع الرسائل (Debounce) لقطع إرسال رسالة لكل صورة
        current_jobs = context.job_queue.get_jobs_by_name(f"menu_{user_id}")
        for job in current_jobs: 
            job.schedule_removal()
            
        context.job_queue.run_once(ask_for_filename, when=1.0, user_id=user_id, chat_id=chat_id, name=f"menu_{user_id}")
    except Exception as e:
        logger.error(f"Error handling photo: {str(e)}")

# 5. دالة استقبال النصوص (لتحديد الاسم أو التنبيه)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if context.user_data.get('waiting_for_name') and context.user_data.get('user_images'):
        filename = clean_filename(update.message.text)
        if not filename:
            await update.message.reply_text("⚠️ اسم غير صالح أو يحتوي على رموز ممنوعة، أرسل اسماً آخر:")
            return
            
        context.user_data['custom_filename'] = filename
        context.user_data['waiting_for_name'] = False
        
        # فصل الأزرار تماماً بناء على طلبك ليعمل كل زر بشكل مستقل
        keyboard = [
            [InlineKeyboardButton("📄 إنشاء ملف PDF الآن", callback_data="to_pdf")],
            [InlineKeyboardButton("📝 إنشاء ملف Word الآن", callback_data="to_docx")],
            [InlineKeyboardButton("❌ إلغاء والبدء من جديد", callback_data="clear")]
        ]
        await update.message.reply_text(
            f"✅ تم اعتماد الاسم المخصص: **{filename}**\nاضغط على الزر المطلوب لبدء الإنشاء فوراً:",
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("🤖 الرجاء استخدام الأزرار التفاعلية للتحكم بوظائف البوت والتنقل.")

# 6. دالة استقبال ومعالجة ملفات المستندات الواردة (PDF و Word) بالتناوب
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name
    doc_action = context.user_data.get('doc_action')

    if not doc_action:
        await update.message.reply_text("⚠️ من فضلك اختر نوع التحويل أولاً من زر المستندات في القائمة الرئيسية.")
        return

    # معالجة تحويل PDF إلى Word
    if doc_action == "pdf_to_word" and file_name.lower().endswith('.pdf'):
        wait_msg = await update.message.reply_text("⏳ جاري تحويل ملف الـ PDF إلى Word، يرجى الانتظار...")
        pdf_path = os.path.join(DOWNLOAD_DIR, f"{update.message.from_user.id}_{file_name}")
        docx_path = pdf_path.replace('.pdf', '.docx')
        
        try:
            file = await doc.get_file()
            await file.download_to_drive(pdf_path)
            
            success = await convert_pdf_to_docx(pdf_path, docx_path)
            if success and os.path.exists(docx_path):
                with open(docx_path, 'rb') as f:
                    await update.message.reply_document(document=f, filename=os.path.basename(docx_path))
            else:
                await update.message.reply_text("❌ عذراً، فشل تحويل ملف الـ PDF المختار.")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ أثناء المعالجة: {str(e)}")
        finally:
            await wait_msg.delete()
            if os.path.exists(pdf_path): os.remove(pdf_path)
            if os.path.exists(docx_path): os.remove(docx_path)
            context.user_data.clear()

    # معالجة تحويل Word إلى PDF المستقرة والجديدة
    elif doc_action == "word_to_pdf" and file_name.lower().endswith('.docx'):
        wait_msg = await update.message.reply_text("⏳ جاري تحويل ملف الـ Word إلى PDF المنسق، يرجى الانتظار...")
        docx_path = os.path.join(DOWNLOAD_DIR, f"{update.message.from_user.id}_{file_name}")
        pdf_path = docx_path.replace('.docx', '.pdf')
        
        try:
            file = await doc.get_file()
            await file.download_to_drive(docx_path)
            
            success = await convert_docx_to_pdf(docx_path, pdf_path)
            if success and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as f:
                    await update.message.reply_document(document=f, filename=os.path.basename(pdf_path))
            else:
                await update.message.reply_text("❌ عذراً، فشل معالجة وتحويل ملف الـ Word إلى PDF.")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ غير متوقع: {str(e)}")
        finally:
            await wait_msg.delete()
            if os.path.exists(docx_path): os.remove(docx_path)
            if os.path.exists(pdf_path): os.remove(pdf_path)
            context.user_data.clear()
    else:
        await update.message.reply_text("❌ صيغة الملف المرسل لا تتطابق مع الخيار الذي حددته من القائمة.")

def clean_user_data(context, images, result_file):
    """حذف فوري للصور والملفات بعد الانتهاء التام لحماية الخادم وتصفير الذاكرة"""
    for img in images:
        if os.path.exists(img): os.remove(img)
    if os.path.exists(result_file): os.remove(result_file)
    context.user_data.clear()

def main():
    app = Application.builder().token(TOKEN).build()
    
    # ربط جميع المعالجات والأحداث بالدوال
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("🤖 البوت تم تحديثه بالكامل ويعمل بنظام القوائم الذكية الآن...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
