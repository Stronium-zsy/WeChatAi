import os
import pdfplumber
import pytesseract
from ebooklib import epub
from PIL import Image
from pytesseract import Output


def convert_pdf_to_txt(pdf_path, txt_path):
    """将PDF转换为TXT并保存到指定路径"""
    with pdfplumber.open(pdf_path) as pdf:
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            for page in pdf.pages:
                txt_file.write(page.extract_text())


def convert_epub_to_txt(epub_path, txt_path):
    """将EPUB转换为TXT并保存到指定路径"""
    book = epub.read_epub(epub_path)
    with open(txt_path, 'w', encoding='utf-8') as txt_file:
        for item in book.get_items():
            if item.get_type() == epub.EpubHtml:
                content = item.content.decode('utf-8')
                txt_file.write(content)


def extract_text_from_image(image_path, txt_path):
    """从图片中提取文字，支持中文和英文"""
    img = Image.open(image_path)
    # 使用Tesseract OCR识别中文和英文
    text = pytesseract.image_to_string(img, lang='eng+chi_sim')
    with open(txt_path, 'w', encoding='utf-8') as txt_file:
        txt_file.write(text)


def process_directory(directory, output_directory):
    """遍历目录并将所有PDF/EPUB/图片文件转换为TXT文件"""
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_name, file_extension = os.path.splitext(file)

            output_txt_path = os.path.join(output_directory, file_name + '.txt')

            if file_extension.lower() == '.pdf':
                print(f'Converting PDF: {file_path} to {output_txt_path}')
                convert_pdf_to_txt(file_path, output_txt_path)

            elif file_extension.lower() == '.epub':
                print(f'Converting EPUB: {file_path} to {output_txt_path}')
                convert_epub_to_txt(file_path, output_txt_path)

            elif file_extension.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                print(f'Extracting text from image: {file_path} to {output_txt_path}')
                extract_text_from_image(file_path, output_txt_path)


if __name__ == "__main__":
    input_directory = "E:\\PycharmProjects\\WechatAi\\“味”使用的资源"  # 修改为你的目标目录路径
    output_directory = "E:\\PycharmProjects\\WechatAi\\output"  # 修改为保存转换结果的目录

    process_directory(input_directory, output_directory)
