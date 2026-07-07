import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
from docx import Document
from pdf2docx import Converter

# إعداد السجلات (Logging) لمعرفة حالة البوت والأخطاء إن وجدت
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

from config import TOKEN

# مجلد مؤقت لحفظ الصور والملفات المرفوعة والمحولة
DOWNLOAD_DIR = "temp_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# دالة الترحيب /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت تحويل الملفات المتكامل!\n\n"
        "📸 **لتحويل الصور إلى ملف:** أرسل لي صورة (أو عدة صور تلو الأخرى).\n"
        "📄 **لتحويل المستندات:** أرسل لي ملف PDF لتحويله مباشرة إلى Word."
    )

# دالة استقبال ومعالجة الصور
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    user_id = update.message.from_user.id
    
    if 'user_images' not in context.user_data:
        context.user_data['user_images'] = []
        
    # تحديد مسار فريد للصورة المستلمة
    file_path = os.path.join(DOWNLOAD_DIR, f"{user_id}_{len(context.user_data['user_images'])}.jpg")
    await photo_file.download_to_drive(file_path)
    context.user_data['user_images'].append(file_path)
    
    # بناء أزرار الخيارات التفاعلية للمستخدم
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

# دالة استقبال ومعالجة المستندات (PDF إلى Word)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    file_name = doc.file_name
    
    if file_name.lower().endswith('.pdf'):
        wait_msg = await update.message.reply_text("⏳ جاري تحميل ملف PDF ومعالجته، يرجى الانتظار...")
        pdf_path = os.path.join(DOWNLOAD_DIR, f"{update.message.from_user.id}_{file_name}")
        docx_path = pdf_path.replace('.pdf', '.docx')
        
        file = await doc.get_file()
        await file.download_to_drive(pdf_path)
        
        try:
            # بدء عملية التحويل البرمجية
            cv = Converter(pdf_path)
            cv.convert(docx_path, start=0, end=None)
            cv.close()
            
            # إرسال ملف الـ Word الناتج للمستخدم
            await update.message.reply_document(document=open(docx_path, 'rb'), filename=os.path.basename(docx_path))
            await wait_msg.delete()
        except Exception as e:
            await update.message.reply_text(f"❌ عذراً، حدث خطأ أثناء تحويل ملف PDF: {str(e)}")
        finally:
            # مسح الملفات المؤقتة من الخادم فوراً لحفظ المساحة
            if os.path.exists(pdf_path): os.remove(pdf_path)
            if os.path.exists(docx_path): os.remove(docx_path)
            
    elif file_name.lower().endswith('.docx'):
        await update.message.reply_text("⚠️ ملاحظة: التحويل من Word إلى PDF يتطلب برامج مكتبية (مثل LibreOffice) على السيرفر، يرجى إرسال ملفات PDF لتحويلها إلى Word أو إرسال صور.")
    else:
        await update.message.reply_text("❌ صيغة الملف غير مدعومة. أرسل صوراً أو ملفات PDF فقط.")

# دالة التحكم في الأزرار التفاعلية (Callback Query)
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
        
        # فتح الصور وتحويلها لصيغة متوافقة ثم حفظها كـ PDF واحد
        img_list = [Image.open(img).convert('RGB') for img in images]
        img_list[0].save(pdf_path, save_all=True, append_images=img_list[1:])
        
        await query.message.reply_document(document=open(pdf_path, 'rb'), filename="📸_Images.pdf")
        clean_user_data(context, images, pdf_path)

    elif query.data == "to_docx":
        await query.edit_message_text("⏳ جاري إنشاء ملف Word وإدراج الصور...")
        docx_path = os.path.join(DOWNLOAD_DIR, f"converted_{user_id}.docx")
        
        # إنشاء مستند Word وإضافة الصور داخله بشكل متتالي
        doc = Document()
        for img in images:
            doc.add_picture(img)
        doc.save(docx_path)
        
        await query.message.reply_document(document=open(docx_path, 'rb'), filename="📝_Images.docx")
        clean_user_data(context, images, docx_path)
        
    elif query.data == "clear":
        for img in images:
            if os.path.exists(img): os.remove(img)
        context.user_data['user_images'] = []
        await query.edit_message_text("🗑 تم مسح جميع الصور المحفوظة بنجاح. يمكنك إرسال صور جديدة الآن.")

# دالة تنظيف ومسح مخلفات الصور بعد إرسال الملف النهائي
def clean_user_data(context, images, result_file):
    for img in images:
        if os.path.exists(img): os.remove(img)
    if os.path.exists(result_file): os.remove(result_file)
    context.user_data['user_images'] = []

# تشغيل البوت وربطه
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("🤖 البوت يعمل الآن بنجاح وبانتظار الملفات...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
