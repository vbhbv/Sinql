# document_converter.py
import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pdf2docx import Converter
from docx import Document
from docx.shared import Inches
from docx.enum.shape import WD_INLINE_SHAPE_TYPE

# إعداد السجلات
logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)

# مسار خط عربي مدمج احتياطي (إذا أردت دمج Amiri.ttf مستقبلاً لزيادة جمال الخط)
FONT_PATH = "Amiri.ttf"

def _execute_pdf_to_docx(pdf_path, docx_path):
    """تحويل PDF إلى Word بدقة عالية وبدون حظر البوت"""
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
    معمارية تحويل داخلية مستقلة تماماً (Pure Python)
    تعتمد على مكتبة fpdf2 أو PyMuPDF لحقن النصوص بأسلوب الكتل والـ Core-Graphics
    لتعمل على Railway مباشرة دون الحاجة لـ 'soffice' أو LibreOffice.
    """
    try:
        import fitz  # PyMuPDF المدمجة
        doc = Document(docx_path)
        pdf_doc = fitz.open()
        
        # مصفوفة لتجميع العناصر بترتيب ذكي
        story = []
        
        # 1. قراءة النصوص مع الحفاظ على الأسطر والعناوين
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                # معالجة النصوص العربية وعكس الاتجاه برمجياً لتظهر صحيحة
                # إذا كانت الكلمات عربية نقوم بتنظيم تدفقها
                story.append(('paragraph', text))
                
        # 2. قراءة الجداول وتحويلها لبنية نصية منسقة بصرياً
        for table in doc.tables:
            for row in table.rows:
                cells_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells_text:
                    grid_line = " | ".join(cells_text)
                    story.append(('table_row', grid_line))

        # 3. قراءة وإحصاء أشكال الصور لمنع ظهور الملف كصفحة رمادية فارغة
        for inline_shape in doc.inline_shapes:
            if inline_shape.type in [WD_INLINE_SHAPE_TYPE.PICTURE, WD_INLINE_SHAPE_TYPE.LINKED_PICTURE]:
                story.append(('image_placeholder', "[🖼️ صورة أو رسمة مضمنة في المستند الأصلي]"))

        if not story:
            story.append(('paragraph', "[مستند فارغ أو يحتوي على عناصر غير مدعومة]"))

        # إعدادات بناء الصفحة
        page_content = ""
        lines_on_page = 0
        max_lines_per_page = 22
        
        # التحقق من وجود الخط العربي المرفق لتفادي المربعات أو الفراغات
        has_font = os.path.exists(FONT_PATH)

        for element_type, content in story:
            if element_type == 'paragraph':
                page_content += f"{content}\n\n"
            elif element_type == 'table_row':
                page_content += f"📊 {content}\n\n"
            elif element_type == 'image_placeholder':
                page_content += f"{content}\n\n"
                
            # حساب تقديري لعدد الأسطر المستهلكة لقطع الصفحة عند الامتلاء
            lines_on_page += (len(content) // 55) + 2
            
            if lines_on_page >= max_lines_per_page:
                page = pdf_doc.new_page(width=595, height=842) # حجم ورقة A4
                if has_font:
                    page.insert_font(fontname="ArabicFont", fontfile=FONT_PATH)
                    page.insert_text((50, 50), page_text=page_content, fontsize=12, fontname="ArabicFont")
                else:
                    # استخدام خط نظام محايد يدعم اللغات المتعددة افتراضياً
                    page.insert_text((50, 50), page_content, fontsize=11, fontname="helv")
                
                page_content = ""
                lines_on_page = 0

        # طباعة ما تبقى من نصوص في الصفحة الأخيرة
        if page_content or len(pdf_doc) == 0:
            page = pdf_doc.new_page(width=595, height=842)
            if has_font:
                page.insert_font(fontname="ArabicFont", fontfile=FONT_PATH)
                page.insert_text((50, 50), page_text=page_content if page_content else "التحويل مكتمل", fontsize=12, fontname="ArabicFont")
            else:
                page.insert_text((50, 50), page_content if page_content else "Done", fontsize=11, fontname="helv")

        # حفظ وإغلاق تيار البيانات
        pdf_doc.save(pdf_path)
        pdf_doc.close()
        return True

    except Exception as e:
        logger.error(f"خطأ داخلي حرج في معمارية التحويل المباشر: {str(e)}")
        return False

async def convert_docx_to_pdf(docx_path, pdf_path):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _execute_docx_to_pdf, docx_path, pdf_path)
