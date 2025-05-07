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

    response = requests.get(gif_url)
    if response.status_code != 200:
        return {'error': 'Failed to download gif'}, 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=".gif") as temp_gif:
        temp_gif.write(response.content)
        gif_path = temp_gif.name

    reader = imageio.get_reader(gif_path)
    meta = reader.get_meta_data()
    fps = meta.get("duration", 100)
    os.unlink(gif_path)

    font_path = os.path.join("fonts", "Shabnam.ttf")
    font_size = 28
    font = ImageFont.truetype(font_path, font_size)

    frames = []
    for frame in reader:
        im = Image.fromarray(frame.convert("RGB"))

        text_height = font.getbbox(text)[3] + 20
        new_im = Image.new("RGB", (im.width, im.height + text_height), (0, 0, 0))
        new_im.paste(im, (0, 0))

        draw = ImageDraw.Draw(new_im)
        w = draw.textlength(text, font=font)
        draw.text(((im.width - w) / 2, im.height + 10), text, font=font, fill="white")

        frames.append(new_im)

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".gif").name
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=fps,
        loop=0
    )

    return send_file(output_path, mimetype='image/gif', as_attachment=False)

if __name__ == '__main__':
    app.run(debug=True)
