from flask import Flask, request, send_file
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import requests
import tempfile
import os

app = Flask(__name__)

@app.route('/add_text_to_video', methods=['GET'])
def add_text_to_video():
    video_url = request.args.get('url')
    text = request.args.get('text')

    if not video_url or not text:
        return {'error': 'url and text required'}, 400

    # دانلود فایل MP4
    response = requests.get(video_url)
    if response.status_code != 200:
        return {'error': 'Download failed'}, 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(response.content)
        video_path = tmp.name

    # باز کردن ویدیو
    clip = VideoFileClip(video_path)

    # ساخت متن
    txt = TextClip(text, fontsize=36, font="Shabnam", color='white', method='caption', size=(clip.w, None))
    txt = txt.set_duration(clip.duration).set_position(("center", "bottom"))

    # اضافه کردن متن
    result = CompositeVideoClip([clip, txt])

    # ذخیره خروجی
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
    result.write_videofile(output_path, codec='libx264', audio=False, fps=clip.fps)

    return send_file(output_path, mimetype='video/mp4')

if __name__ == '__main__':
    app.run(debug=True)
