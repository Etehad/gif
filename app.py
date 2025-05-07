import logging
import subprocess
from flask import Flask, request, send_file, after_this_request
import moviepy
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import requests
import tempfile
import os

logging.basicConfig(level=logging.DEBUG)
logging.info(f"MoviePy version: {moviepy.__version__}")

app = Flask(__name__)

@app.route('/add_text_to_video', methods=['GET'])
def add_text_to_video():
    video_url = request.args.get('url')
    text = request.args.get('text')
    logging.info(f"Processing request: url={video_url}, text={text}")

    if not video_url or not text:
        logging.error("Missing url or text")
        return {'error': 'url and text required'}, 400

    try:
        # دانلود فایل با stream
        response = requests.get(video_url, stream=True)
        logging.info(f"Download status: {response.status_code}, content-type: {response.headers.get('content-type')}")
        if response.status_code != 200:
            logging.error("Download failed")
            return {'error': 'Download failed'}, 400
        if 'video/mp4' not in response.headers.get('content-type', ''):
            logging.error("Invalid content type")
            return {'error': 'Invalid content type, expected video/mp4'}, 400

        # ذخیره فایل
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            video_path = tmp.name
            logging.info(f"Video saved to: {video_path}, size: {os.path.getsize(video_path)} bytes")

        # بازسازی فایل با ffmpeg برای رفع مشکل moov atom
        fixed_video_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
        try:
            subprocess.run([
                'ffmpeg', '-i', video_path, '-c:v', 'copy', '-c:a', 'copy', '-map', '0', '-movflags', 'faststart', fixed_video_path
            ], check=True, capture_output=True)
            logging.info(f"Fixed video saved to: {fixed_video_path}")
            video_path = fixed_video_path
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg error: {e.stderr.decode()}")
            return {'error': f"FFmpeg error: {e.stderr.decode()}"}, 500

        # خروجی
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        output_path = output_file.name
        output_file.close()
        logging.info(f"Output path: {output_path}")

        # پردازش ویدیو
        clip = VideoFileClip(video_path)
        logging.info(f"Video loaded: duration={clip.duration}, fps={clip.fps}")
        txt = TextClip(text, fontsize=36, font="/app/fonts/Shabnam.ttf", color='white', method='caption', size=(clip.w, None))
        txt = txt.set_duration(clip.duration).set_position(("center", "bottom"))
        result = CompositeVideoClip([clip, txt])
        fps = clip.fps if hasattr(clip, "fps") and clip.fps else 24
        result.write_videofile(output_path, codec='libx264', audio=False, fps=fps, bitrate="500k")
        logging.info(f"Video written to: {output_path}")

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
                if os.path.exists(fixed_video_path):
                    os.remove(fixed_video_path)
                if os.path.exists(output_path):
                    os.remove(output_path)
                logging.info("Temporary files cleaned up")
            except Exception as e:
                logging.error(f"Cleanup error: {e}")
            return response

        logging.info(f"Sending file: {output_path}")
        return send_file(output_path, mimetype='video/mp4')

    except Exception as e:
        logging.error(f"Processing error: {str(e)}")
        return {'error': str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
