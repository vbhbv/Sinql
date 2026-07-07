import os
import logging
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
from docx import Document
from docx.shared import Inches
from pdf2docx import Converter

# إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

from config import TOKEN

# مجلد مؤقت لحفظ الصور والملفات
DOWNLOAD_DIR = "temp_files"

def تنظيف_المجلد_المؤقت():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

تنظيف_المجلد_المؤقت()

# دالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت تحويل الملفات المتكامل!\n\n"
        "📸 **لتحويل الصور إلى ملف:** أرسل لي صورة (أو عدة صور تلو الأخرى).\n"
        "📄 **لتحويل المستندات:** أرسل لي ملف PDF لتحويله مباشرة إلى Word."
    )

# دالة استقبال ومعالجة الصور
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo_file = await update.message.photo[-1].get_file()
        user_id = update.message.from_user.id
        
        if 'user_images' not in context.user_data:
            context.user_data['user_images'] = []
            
        file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{len(context.user_data['user_images'])}.jpg")
        await photo_file.download_to_drive(file_path)
        context.user_data['user_images'].append(file_path)
        
        keyboard = [
            [
                InlineKeyboardButton("📄 تحويل إلى PDF", callback_data="to_pdf"),
                InlineKeyboardButton("📝 تحويل إلى Word (Docx)", callback_data="to_docx")
            ],
            [InlineKeyboardButton("❌ مسح الصور والبدء من جديد", callback_data="clear")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📥 تم استلام وحفظ الصورة رقم ({len(context.user_data['user_images'])}).\n"
            "الرجاء اختيار الصيغة التي تريد تحويل الصور إليها:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error handling photo: {str(e)}")

# دالة استقبال ومعالجة المستندات (PDF إلى Word)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name
    
    if file_name.lower().endswith('.pdf'):
        wait_msg = await update.message.reply_text("⏳ جاري تحميل ملف PDF ومعالجته، يرجى الانتظار...")
        pdf_path = os.path.join(DOWNLOAD_DIR, f"{update.message.from_user.id}_{file_name}")
        docx_path = pdf_path.replace('.pdf', '.docx')
        
        try:
            file = await doc.get_file()
            await file.download_to_drive(pdf_path)
            
            cv = Converter(pdf_path)
            cv.convert(docx_path, start=0, end=None)
            cv.close()
            
            with open(docx_path, 'rb') as f:
                await update.message.reply_document(document=f, filename=os.path.basename(docx_path))
            await wait_msg.delete()
        except Exception as e:
            logger.error(f"Error converting PDF: {str(e)}")
            await update.message.reply_text(f"❌ عذراً، حدث خطأ أثناء تحويل ملف PDF: {str(e)}")
        finally:
            if os.path.exists(pdf_path): os.remove(pdf_path)
            if os.path.exists(docx_path): os.remove(docx_path)
            
    elif file_name.lower().endswith('.docx'):
        await update.message.reply_text("⚠️ ملاحظة: التحويل من Word إلى PDF يتطلب برامج مكتبية إضافية، يرجى إرسال ملفات PDF لتحويلها إلى Word أو إرسال صور.")
    else:
        await update.message.reply_text("❌ صيغة الملف غير مدعومة. أرسل صوراً أو ملفات PDF فقط.")

# دالة التحكم في الأزرار التفاعلية
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    images = context.user_data.get('user_images', [])
    
    if not images and query.data != "clear":
        await query.edit_message_text("❌ لم يتم العثور على صور محفوظة. يرجى إعادة إرسال الصور أولاً.")
        return

    if query.data == "to_pdf":
        await query.edit_message_text("⏳ جاري إنشاء ملف PDF وتجميع الصور...")
        pdf_path = os.path.join(DOWNLOAD_DIR, f"converted_{user_id}.pdf")
        
        try:
            img_list = [Image.open(img).convert('RGB') for img in images if os.path.exists(img)]
            if img_list:
                img_list[0].save(pdf_path, save_all=True, append_images=img_list[1:])
                with open(pdf_path, 'rb') as f:
                    await query.message.reply_document(document=f, filename="📸_Images.pdf")
            else:
                await query.message.reply_text("❌ حدث خطأ، لم نجد الصور على السيرفر.")
        except Exception as e:
            logger.error(f"Error creating PDF: {str(e)}")
            await query.message.reply_text(f"❌ فشل إنشاء ملف PDF: {str(e)}")
        finally:
            clean_user_data(context, images, pdf_path)

    elif query.data == "to_docx":
        await query.edit_message_text("⏳ جاري إنشاء ملف Word وتنسيق الصور...")
        docx_path = os.path.join(DOWNLOAD_DIR, f"converted_{user_id}.docx")
        
        try:
            doc = Document()
            
            # ضبط حواف الصفحة الافتراضية لملف الوورد (Margins) لتكون مناسبة
            sections = doc.sections
            for section in sections:
                section.top_margin = Inches(0.5)
                section.bottom_margin = Inches(0.5)
                section.left_margin = Inches(0.5)
                section.right_margin = Inches(0.5)

            for img_path in images:
                if os.path.exists(img_path):
                    # إجبار الصورة على اتخاذ عرض ثابت ومناسب داخل صفحة الوورد (6.5 إنش)
                    # هذا يمنع تمدد الصورة خارج حدود الصفحة ويجعلها منسقة بالكامل
                    doc.add_picture(img_path, width=Inches(6.5))
                    
            doc.save(docx_path)
            
            with open(docx_path, 'rb') as f:
                await query.message.reply_document(document=f, filename="📝_Images.docx")
        except Exception as e:
            logger.error(f"Error creating DOCX: {str(e)}")
            await query.message.reply_text(f"❌ فشل إنشاء ملف Word: {str(e)}")
        finally:
            clean_user_data(context, images, docx_path)
        
    elif query.data == "clear":
        for img in images:
            if os.path.exists(img): os.remove(img)
        context.user_data['user_images'] = []
        await query.edit_message_text("🗑 تم مسح جميع الصور المحفوظة بنجاح. يمكنك إرسال صور جديدة الآن.")

def clean_user_data(context, images, result_file):
    for img in images:
        if os.path.exists(img): os.remove(img)
    if os.path.exists(result_file): os.remove(result_file)
    context.user_data['user_images'] = []

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("🤖 يتم الآن تهيئة البوت وطرد الجلسات المتضاربة...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
