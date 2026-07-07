# document_converter.py
import os
import logging
import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pdf2docx import Converter

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)

def _execute_pdf_to_docx(pdf_path, docx_path):
    """تحويل من PDF إلى Word بدقة عالية وبدون التأثير على أداء البوت"""
    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None, pages=None)
        cv.close()
        return True
    except Exception as e:
        logger.error(f"خطأ أثناء تحويل PDF إلى Word: {str(e)}")
        return False

async def convert_pdf_to_docx(pdf_path, docx_path):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _execute_pdf_to_docx, pdf_path, docx_path)


def _execute_docx_to_pdf(docx_path, pdf_path):
    """
    تحويل احترافي حقيقي 100% يحافظ على الألوان، الأغلفة، التنسيق، والخطوط العربية.
    يعتمد على استدعاء الحزم الخفيفة للسيرفر لتفادي الصفحات البيضاء أو النصوص المبعثرة.
    """
    try:
        # محاولة استخدام أداة النظام المباشرة المتوفرة في بيئات Linux السحابية (soffice / libreoffice)
        # والتي تقوم بعمل "طباعة افتراضية للمستند كـ PDF" للحفاظ على شكله الأصلي تماماً
        output_dir = os.path.dirname(pdf_path)
        
        # أمر التحويل الصامت بدون واجهة رسومية (خفيف جداً ومستقر)
        cmd = [
            'soffice', 
            '--headless', 
            '--convert-to', 'pdf', 
            '--outdir', output_dir, 
            docx_path
        ]
        
        # تشغيل الأمر ومراقبة النتيجة
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
        
        # افتراضياً soffice ينتج ملف بنفس اسم الوورد ولكن بامتداد pdf
        default_generated_pdf = docx_path.replace('.docx', '.pdf')
        
        if os.path.exists(default_generated_pdf):
            # إذا كان الاسم المطلوب مختلفاً، نقوم بإعادة تسميته ليطابق المسار المحدد
            if default_generated_pdf != pdf_path:
                os.rename(default_generated_pdf, pdf_path)
            return True
            
        logger.error(f"فشل التحويل عبر النظام. مخرجات الخطأ: {result.stderr.decode('utf-8', errors='ignore')}")
        return False
        
    except Exception as e:
        logger.error(f"خطأ معماري أثناء تحويل Word إلى PDF: {str(e)}")
        return False

async def convert_docx_to_pdf(docx_path, pdf_path):
    """دالة غير حاظرة (Async) لتحويل المستند بأعلى سرعة متوفرة"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _execute_docx_to_pdf, docx_path, pdf_path)
