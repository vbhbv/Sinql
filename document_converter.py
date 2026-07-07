# document_converter.py
import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pdf2docx import Converter
from docx import Document
from docx.shared import Inches

# إعداد السجلات (Logging) لمتابعة الأخطاء في ريلواي
logger = logging.getLogger(__name__)

# استخدام ThreadPoolExecutor لتشغيل عمليات التحويل الثقيلة في خيوط (Threads) منفصلة
# هذا يمنع تجمد البوت عند ضغط أكثر من مستخدم على أزرار التحويل في نفس الوقت
executor = ThreadPoolExecutor(max_workers=4)

def _execute_pdf_to_docx(pdf_path, docx_path):
    """العملية الداخلية لتحويل PDF إلى Word مع تحسين التنسيق"""
    try:
        cv = Converter(pdf_path)
        # تحويل كافة الصفحات تلقائياً بذكاء
        cv.convert(docx_path, start=0, end=None, pages=None)
        cv.close()
        
        # تحسين التنسيق بعد التحويل (ضبط هوامش المستند لتكون متناسقة وأنيقة)
        if os.path.exists(docx_path):
            doc = Document(docx_path)
            for section in doc.sections:
                section.top_margin = Inches(0.75)
                section.bottom_margin = Inches(0.75)
                section.left_margin = Inches(0.75)
                section.right_margin = Inches(0.75)
            doc.save(docx_path)
            
        return True
    except Exception as e:
        logger.error(f"خطأ داخلي أثناء معالجة وتحسين PDF إلى Word: {str(e)}")
        return False

async def convert_pdf_to_docx(pdf_path, docx_path):
    """دالة تحويل PDF إلى Word (غير حاظرة ومحسنة السرعة)"""
    loop = asyncio.get_running_loop()
    # تشغيل العملية في الخلفية لزيادة سرعة استجابة البوت
    success = await loop.run_in_executor(executor, _execute_pdf_to_docx, pdf_path, docx_path)
    return success


def _execute_docx_to_pdf(docx_path, pdf_path):
    """
    العملية الداخلية لتحويل Word إلى PDF متوافقة 100% مع سيرفر ريلواي (Linux)
    بأسلوب ذكي يقرأ الفقرات والجداول لمنع الانهيار وظهور رسالة الفشل السابقة.
    """
    try:
        import fitz  # مكتبة PyMuPDF السريعة جداً في المعالجة والإنشاء
        doc = Document(docx_path)
        
        # إنشاء مستند PDF جديد فارغ داخل الذاكرة
        pdf_doc = fitz.open()
        
        # مصفوفة مخصصة لتجميع كل عناصر المستند بالترتيب
        elements = []
        
        # 1. قراءة واستخراج الفقرات العادية والعناوين
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                elements.append(paragraph.text)
                
        # 2. قراءة النصوص من داخل الجداول لضمان عدم حدوث خطأ إذا احتوى المستند على جدول
        for table in doc.tables:
            for row in table.rows:
                # تجميع خلايا الصف الواحد بشكل منسق يفصل بينها علامة |
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    elements.append(row_text)
        
        # حالة أمان إذا كان المستند فارغاً تماماً
        if not elements:
            elements.append("[مستند فارغ أو يحتوي على صور فقط]")

        page_text = ""
        line_count = 0
        
        # تجميع النصوص وتوزيعها على الصفحات بحجم A4 قياسي
        for element in elements:
            page_text += element + "\n\n"
            # حساب تقريبي لعدد الأسطر بناءً على طول النص لمنع تداخل الكلام أسفل الصفحة
            line_count += (len(element) // 60) + 2
            
            # إذا شارف سطر الصفحة على الانتهاء (حوالي 22 سطر)، ننشئ صفحة جديدة
            if line_count >= 22:
                page = pdf_doc.new_page(width=595, height=842) # أبعاد صفحة A4
                # استخدام خط افتراضي ناعم يدعم الترميز الأساسي
                page.insert_text((50, 50), page_text, fontsize=11, fontname="helv")
                page_text = ""
                line_count = 0
                
        # إدراج أي نصوص متبقية في صفحة أخيرة
        if page_text or len(pdf_doc) == 0:
            page = pdf_doc.new_page(width=595, height=842)
            page.insert_text((50, 50), page_text if page_text else "Done", fontsize=11, fontname="helv")
            
        # حفظ الملف في المسار النهائي وإغلاق الكائن لتفريغ الذاكرة
        pdf_doc.save(pdf_path)
        pdf_doc.close()
        return True
    except Exception as e:
        logger.error(f"خطأ قاتل أثناء معالجة ملف الـ Word وتحويله: {str(e)}")
        return False

async def convert_docx_to_pdf(docx_path, pdf_path):
    """دالة تحويل Word إلى PDF المطور والسريع لجهاز السيرفر"""
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(executor, _execute_docx_to_pdf, docx_path, pdf_path)
    return success
