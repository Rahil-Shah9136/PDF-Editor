"""
PDF Editor - Flask Backend
Handles PDF rendering and saving with white masks + text overlays.
"""

import os
import json
import base64
import io
from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Store current PDF path in memory (simple single-user app)
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

    # Get page count using PyMuPDF
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(filepath)
        page_count = len(doc)
        doc.close()
        return jsonify({'success': True, 'page_count': page_count, 'filename': file.filename})
    except ImportError:
        return jsonify({'error': 'PyMuPDF not installed. Please run: pip install pymupdf'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/render_page/<int:page_num>')
def render_page(page_num):
    """Render a PDF page as a high-quality PNG image."""
    global current_pdf_path
    if not current_pdf_path or not os.path.exists(current_pdf_path):
        return jsonify({'error': 'No PDF loaded'}), 400

    try:
        import fitz
        doc = fitz.open(current_pdf_path)

        if page_num < 0 or page_num >= len(doc):
            return jsonify({'error': 'Invalid page number'}), 400

        page = doc[page_num]

        # Render at 2x scale for high quality (150 DPI equivalent display)
        # This keeps quality high without being too slow
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Get original page dimensions (in PDF points, 1 point = 1/72 inch)
        page_rect = page.rect
        original_width = page_rect.width
        original_height = page_rect.height

        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')

        doc.close()
        return jsonify({
            'image': img_b64,
            'width': pix.width,
            'height': pix.height,
            'original_width': original_width,
            'original_height': original_height,
            'zoom': zoom
        })
    except ImportError:
        return jsonify({'error': 'PyMuPDF not installed. Run: pip install pymupdf'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/save', methods=['POST'])
def save_pdf():
    """
    Save the PDF with all masks and text overlays applied directly to PDF.
    Masks = white rectangles drawn on PDF canvas.
    Text = text annotations drawn on PDF canvas.
    This preserves PDF structure and quality perfectly.
    """
    global current_pdf_path
    if not current_pdf_path or not os.path.exists(current_pdf_path):
        return jsonify({'error': 'No PDF loaded'}), 400

    data = request.json
    edits = data.get('edits', {})  # {page_num: [{type, ...props}]}

    try:
        import fitz

        doc = fitz.open(current_pdf_path)

        for page_num_str, page_edits in edits.items():
            page_num = int(page_num_str)
            if page_num < 0 or page_num >= len(doc):
                continue

            page = doc[page_num]
            page_rect = page.rect
            pdf_width = page_rect.width
            pdf_height = page_rect.height

            # The frontend renders pages at zoom factor 2x
            # We need to know the rendered image dimensions to convert coordinates
            # Frontend sends us the rendered dimensions
            render_info = data.get('render_info', {}).get(str(page_num), {})
            render_width = render_info.get('width', pdf_width * 2)
            render_height = render_info.get('height', pdf_height * 2)

            # Scale factors: convert pixel coords back to PDF points
            scale_x = pdf_width / render_width
            scale_y = pdf_height / render_height

            for edit in page_edits:
                edit_type = edit.get('type')

                if edit_type == 'mask':
                    # Draw a white filled rectangle to cover content
                    x = edit['x'] * scale_x
                    y = edit['y'] * scale_y
                    w = edit['width'] * scale_x
                    h = edit['height'] * scale_y
                    rect = fitz.Rect(x, y, x + w, y + h)

                    # Draw white rectangle with white border (clean mask)
                    shape = page.new_shape()
                    shape.draw_rect(rect)
                    shape.finish(
                        fill=(1, 1, 1),    # White fill
                        color=(1, 1, 1),   # White border
                        width=0
                    )
                    shape.commit()

                elif edit_type == 'text':
                    # Insert text at the specified position
                    x = edit['x'] * scale_x
                    y = edit['y'] * scale_y
                    text_content = edit.get('text', '')
                    font_size = edit.get('fontSize', 12) * scale_y
                    font_color_hex = edit.get('color', '#000000')

                    # Convert hex color to RGB 0-1 range
                    r, g, b = hex_to_rgb(font_color_hex)

                    # Insert text — y in PDF is from bottom, so we flip
                    # fitz uses top-left origin like screen, so direct use is fine
                    page.insert_text(
                        (x, y + font_size),  # baseline position
                        text_content,
                        fontsize=font_size,
                        color=(r, g, b),
                        fontname="helv"  # Helvetica - universally available
                    )

        # Save to output folder
        original_name = os.path.basename(current_pdf_path)
        name_no_ext = os.path.splitext(original_name)[0]
        output_filename = f"{name_no_ext}_edited.pdf"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        # Save with garbage collection to keep file size minimal
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()

        return jsonify({'success': True, 'filename': output_filename})

    except ImportError:
        return jsonify({'error': 'PyMuPDF not installed. Run: pip install pymupdf'}), 500
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500


@app.route('/download/<filename>')
def download(filename):
    """Download the saved PDF."""
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True)


def hex_to_rgb(hex_color):
    """Convert #RRGGBB to (r, g, b) in 0.0-1.0 range."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return r, g, b


if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)