# document_converter.py
import os
import logging
from pdf2docx import Converter

logger = logging.getLogger(__name__)

async def convert_pdf_to_docx(pdf_path, docx_path):
    """تحويل ملف PDF إلى Word"""
    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()
        return True
    except Exception as e:
        logger.error(f"خطأ أثناء تحويل PDF إلى Word: {str(e)}")
        return False

async def convert_docx_to_pdf(docx_path, pdf_path):
    """
    تحويل Word إلى PDF
    ملاحظة: في بيئات Linux (مثل Railway)، مكتبة docx2pdf تحتاج إلى LibreOffice أو برامج مكتبية غير متوفرة افتراضياً.
    لذلك سنستخدم مكتبة مُصغرة أو نُعطي رسالة للمستخدم لتجنب انهيار السيرفر.
    """
    try:
        # إذا كنت تريد تفعيل تحويل الوورد بالكامل مستقبلاً، يتطلب تثبيت حزم LibreOffice على سيرفر ريلواي.
        # حالياً سنرجع False مع توجيه برميجي آمن لعدم انهيار البوت
        return False
    except Exception as e:
        logger.error(f"خطأ أثناء تحويل Word إلى PDF: {str(e)}")
        return False
