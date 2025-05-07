from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import imageio
import requests
import tempfile
import os

app = Flask(__name__)

@app.route('/add_text_to_gif', methods=['GET'])
def add_text_to_gif():
    gif_url = request.args.get('url')
    text = request.args.get('text')

    if not gif_url or not text:
        return {'error': 'url and text query params required'}, 400

    # دریافت فایل گیف از URL
    response = requests.get(gif_url)
    if response.status_code != 200:
        return {'error': 'Failed to download gif'}, 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as temp_gif:
        temp_gif.write(response.content)
        gif_path = temp_gif.name

    frames = imageio.mimread(gif_path)
    os.unlink(gif_path)

    # فونت فارسی
    font_path = os.path.join("fonts", "Shabnam.ttf")
    font = ImageFont.truetype(font_path, 28)

    new_frames = []
    for frame in frames:
        image = Image.fromarray(frame)
        draw = ImageDraw.Draw(image)
        draw.text((10, 10), text, font=font, fill="white")
        new_frames.append(image)

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".gif").name
    new_frames[0].save(
        output_path,
        save_all=True,
        append_images=new_frames[1:],
        duration=100,
        loop=0,
        disposal=2
    )

    return send_file(output_path, mimetype='image/gif', as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True)
