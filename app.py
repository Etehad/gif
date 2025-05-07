from flask import Flask, request, send_file, after_this_request
import moviepy
import logging
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import requests
import tempfile
import os

# تنظیم لاگ برای دیباگ
logging.basicConfig(level=logging.DEBUG)

print("MoviePy version:", moviepy.__version__)

app = Flask(__name__)

@app.route('/add_text_to_video', methods=['GET'])
def add_text_to_video():
    video_url = request.args.get('url')
    text = request.args.get('text')

    if not video_url or not text:
        return {'error': 'url and text required'}, 400

    # دانلود و ذخیره فایل ویدیو
    try:
        response = requests.get(video_url)
        if response.status_code != 200:
            return {'error': 'Download failed'}, 400
    except Exception as e:
        logging.error(f"Download error: {e}")
        return {'error': 'Download failed'}, 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(response.content)
        video_path = tmp.name

    # خروجی
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    output_path = output_file.name
    output_file.close()

    try:
        clip = VideoFileClip(video_path)
        txt = TextClip(text, fontsize=36, font="/gif/fonts/Shabnam.ttf", color='white', method='caption', size=(clip.w, None))
        txt = txt.set_duration(clip.duration).set_position(("center", "bottom"))
        result = CompositeVideoClip([clip, txt])
        fps = clip.fps if hasattr(clip, "fps") and clip.fps else 24
        result.write_videofile(output_path, codec='libx264', audio=False, fps=fps)
    except Exception as e:
        logging.error(f"Video processing error: {e}")
        return {'error': str(e)}, 500

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
        return response

    return send_file(output_path, mimetype='video/mp4')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
