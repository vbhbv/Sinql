# document_converter.py
import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pdf2docx import Converter
from docx import Document
from docx.shared import Inches
from docx.enum.shape import WD_INLINE_SHAPE_TYPE

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)

def _execute_pdf_to_docx(pdf_path, docx_path):
    """تحويل PDF إلى Word مع ضبط الهوامش القياسية"""
    try:
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None, pages=None)
        cv.close()
        
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
        logger.error(f"خطأ في تحويل PDF إلى Word: {str(e)}")
        return False

async def convert_pdf_to_docx(pdf_path, docx_path):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _execute_pdf_to_docx, pdf_path, docx_path)


def _execute_docx_to_pdf(docx_path, pdf_path):
    """
    نسخة احترافية مصححة لتحويل Word إلى PDF
    تتعامل مع الصور، الفقرات، والجداول لتجنب الانهيار (Crash)
    """
    try:
        import fitz  # PyMuPDF
        doc = Document(docx_path)
        pdf_doc = fitz.open()
        
        elements = []
        
        # 1. استخراج كافة الفقرات والعناوين النصية
        for p in doc.paragraphs:
            if p.text.strip():
                elements.append(('text', p.text))
                
        # 2. استخراج الجداول المكتوبة إن وجدت
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    elements.append(('table', row_text))
                    
        # 3. التصحيح الآمن: استخراج الصور بناءً على نوع الـ InlineShape الصحيح
        for inline_shape in doc.inline_shapes:
            if inline_shape.type == WD_INLINE_SHAPE_TYPE.PICTURE or inline_shape.type == WD_INLINE_SHAPE_TYPE.LINKED_PICTURE:
                elements.append(('image', "[تحتوي هذه الصفحة على صورة أو مخطوطة مضمنة]"))

        # حالة أمان لمنع إنشاء ملف فارغ تماماً
        if not elements:
            elements.append(('text', "[مستند نصي فارغ أو غير مدعوم بالتنسيق الحالي]"))

        page_text = ""
        line_count = 0
        
        for el_type, text in elements:
            if el_type == 'text':
                page_text += text + "\n\n"
            elif el_type == 'table':
                page_text += "📊 " + text + "\n\n"
            else:
                page_text += "🖼 " + text + "\n\n"
                
            # حساب تقريبي للمساحة المستهلكة في الأسطر
            line_count += (len(text) // 50) + 2
            
            # الانتقال لصفحة جديدة عند امتلاء الأسطر
            if line_count >= 24:
                page = pdf_doc.new_page(width=595, height=842)
                page.insert_text((50, 50), page_text, fontsize=11, fontname="helv")
                page_text = ""
                line_count = 0
                
        # كتابة النصوص المتبقية في الصفحة الأخيرة
        if page_text or len(pdf_doc) == 0:
            page = pdf_doc.new_page(width=595, height=842)
            page.insert_text((50, 50), page_text if page_text else "التحويل مكتمل بنجاح", fontsize=11, fontname="helv")
            
        pdf_doc.save(pdf_path)
        pdf_doc.close()
        return True
    except Exception as e:
        logger.error(f"خطأ قاتل أثناء تحويل Word إلى PDF: {str(e)}")
        return False

async def convert_docx_to_pdf(docx_path, pdf_path):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _execute_docx_to_pdf, docx_path, pdf_path)
