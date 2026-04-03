import os
import json
import base64
import io
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

current_pdf_path = None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_pdf():
    global current_pdf_path
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Please upload a PDF file'}), 400
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    current_pdf_path = filepath
    try:
        import fitz
        doc = fitz.open(filepath)
        page_count = len(doc)
        doc.close()
        return jsonify({'success': True, 'page_count': page_count, 'filename': file.filename})
    except ImportError:
        return jsonify({'error': 'PyMuPDF not installed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/render_page/<int:page_num>')
def render_page(page_num):
    global current_pdf_path
    if not current_pdf_path or not os.path.exists(current_pdf_path):
        return jsonify({'error': 'No PDF loaded'}), 400
    try:
        import fitz
        doc = fitz.open(current_pdf_path)
        if page_num < 0 or page_num >= len(doc):
            return jsonify({'error': 'Invalid page number'}), 400
        page = doc[page_num]
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        page_rect = page.rect
        img_b64 = base64.b64encode(pix.tobytes("png")).decode('utf-8')
        doc.close()
        return jsonify({
            'image': img_b64,
            'width': pix.width,
            'height': pix.height,
            'original_width': page_rect.width,
            'original_height': page_rect.height,
            'zoom': zoom
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def apply_edits_to_doc(doc, edits, render_info):
    """Apply masks and text edits directly onto PDF pages."""
    import fitz
    for page_num_str, page_edits in edits.items():
        page_num = int(page_num_str)
        if page_num < 0 or page_num >= len(doc):
            continue
        page = doc[page_num]
        page_rect = page.rect
        pdf_width = page_rect.width
        pdf_height = page_rect.height
        ri = render_info.get(str(page_num), {})
        render_width = ri.get('width', pdf_width * 2)
        render_height = ri.get('height', pdf_height * 2)
        scale_x = pdf_width / render_width
        scale_y = pdf_height / render_height

        for edit in page_edits:
            edit_type = edit.get('type')
            if edit_type == 'mask':
                x = edit['x'] * scale_x
                y = edit['y'] * scale_y
                w = edit['width'] * scale_x
                h = edit['height'] * scale_y
                rect = fitz.Rect(x, y, x + w, y + h)
                shape = page.new_shape()
                shape.draw_rect(rect)
                shape.finish(fill=(1, 1, 1), color=(1, 1, 1), width=0)
                shape.commit()
            elif edit_type == 'text':
                x = edit['x'] * scale_x
                y = edit['y'] * scale_y
                text_content = edit.get('text', '')
                font_size = edit.get('fontSize', 12) * scale_y
                bold = edit.get('bold', False)
                r, g, b = hex_to_rgb(edit.get('color', '#000000'))
                fontname = "hebo" if bold else "helv"
                page.insert_text(
                    (x, y + font_size),
                    text_content,
                    fontsize=font_size,
                    color=(r, g, b),
                    fontname=fontname
                )
    return doc


@app.route('/save', methods=['POST'])
def save_pdf():
    global current_pdf_path
    if not current_pdf_path or not os.path.exists(current_pdf_path):
        return jsonify({'error': 'No PDF loaded'}), 400
    data = request.json
    edits = data.get('edits', {})
    render_info = data.get('render_info', {})
    try:
        import fitz
        doc = fitz.open(current_pdf_path)
        doc = apply_edits_to_doc(doc, edits, render_info)
        original_name = os.path.basename(current_pdf_path)
        name_no_ext = os.path.splitext(original_name)[0]
        output_filename = f"{name_no_ext}_edited.pdf"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        return jsonify({'success': True, 'filename': output_filename})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/apply_scan', methods=['POST'])
def apply_scan():
    """Apply edits first, then B&W scan effect on top."""
    global current_pdf_path
    if not current_pdf_path or not os.path.exists(current_pdf_path):
        return jsonify({'error': 'No PDF loaded'}), 400
    data = request.json
    edits = data.get('edits', {})
    render_info = data.get('render_info', {})
    try:
        import fitz

        # Step 1 — Apply masks and text onto PDF first
        doc = fitz.open(current_pdf_path)
        doc = apply_edits_to_doc(doc, edits, render_info)

        # Step 2 — Save to a temp buffer
        temp_buf = io.BytesIO()
        doc.save(temp_buf, garbage=4, deflate=True)
        doc.close()
        temp_buf.seek(0)

        # Step 3 — Reopen and apply B&W scan effect page by page
        doc2 = fitz.open(stream=temp_buf, filetype="pdf")
        output_doc = fitz.open()

        for page_num in range(len(doc2)):
            page = doc2[page_num]
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            # PIL processing — B&W scan effect
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = img.convert('L')
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = img.filter(ImageFilter.SHARPEN)
            img = img.filter(ImageFilter.GaussianBlur(0.3))
            arr = np.array(img, dtype=np.int16)
            noise = np.random.normal(0, 3, arr.shape).astype(np.int16)
            arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
            img = Image.fromarray(arr).convert('RGB')

            page_rect = page.rect
            new_page = output_doc.new_page(
                width=page_rect.width,
                height=page_rect.height
            )
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            new_page.insert_image(page_rect, stream=buf.read())

        doc2.close()

        name_no_ext = os.path.splitext(os.path.basename(current_pdf_path))[0]
        output_filename = f"{name_no_ext}_scanned.pdf"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        output_doc.save(output_path, garbage=4, deflate=True)
        output_doc.close()

        return jsonify({'success': True, 'filename': output_filename})

    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/download/<filename>')
def download(filename):
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True)


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return (int(hex_color[0:2], 16) / 255.0,
            int(hex_color[2:4], 16) / 255.0,
            int(hex_color[4:6], 16) / 255.0)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
