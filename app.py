from flask import Flask, request, send_file
import requests
import os
import logging
import tempfile
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import subprocess

app = Flask(__name__)

# تنظیم لاگ‌گیری
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route('/add_text_to_video', methods=['GET'])
def add_text_to_video():
    try:
        video_url = request.args.get('url')
        text = request.args.get('text')
        
        logger.info(f"Received request with URL: {video_url}, Text: {text}")
        
        if not video_url or not text:
            logger.error("Missing URL or text parameter")
            return {"error": "Missing URL or text parameter"}, 400

        # دانلود ویدئو
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_video:
            temp_video_path = temp_video.name
        logger.info(f"Downloading video to: {temp_video_path}")
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(video_url, headers=headers, stream=True)
        logger.info(f"Download status: {response.status_code}, content-type: {response.headers.get('content-type')}")
        
        if response.status_code != 200:
            logger.error(f"Failed to download video: {response.status_code}")
            return {"error": f"Failed to download video: {response.status_code}"}, 400
            
        with open(temp_video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        file_size = os.path.getsize(temp_video_path)
        logger.info(f"Video saved to: {temp_video_path}, size: {file_size} bytes")
        
        if file_size == 0:
            logger.error("Downloaded video is empty")
            return {"error": "Downloaded video is empty"}, 400

        # بررسی ساختار ویدئو با ffprobe
        try:
            ffprobe_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'json', temp_video_path
            ]
            ffprobe_result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
            logger.info(f"ffprobe output: {ffprobe_result.stdout}")
            if ffprobe_result.returncode != 0:
                logger.error(f"ffprobe error: {ffprobe_result.stderr}")
                return {"error": f"Invalid video format: {ffprobe_result.stderr}"}, 400
        except Exception as e:
            logger.error(f"ffprobe failed: {str(e)}")
            return {"error": f"ffprobe failed: {str(e)}"}, 400

        # تعمیر ویدئو با ffmpeg
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_fixed:
            temp_fixed_path = temp_fixed.name
        ffmpeg_cmd = [
            'ffmpeg', '-i', temp_video_path, '-c:v', 'libx264',
            '-c:a', 'aac', '-y', temp_fixed_path
        ]
        try:
            ffmpeg_result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            logger.info(f"ffmpeg fix output: {ffmpeg_result.stdout}")
            if ffmpeg_result.returncode != 0:
                logger.error(f"ffmpeg fix error: {ffmpeg_result.stderr}")
                return {"error": f"ffmpeg fix error: {ffmpeg_result.stderr}"}, 400
        except Exception as e:
            logger.error(f"ffmpeg fix failed: {str(e)}")
            return {"error": f"ffmpeg fix failed: {str(e)}"}, 400
        logger.info(f"Fixed video saved to: {temp_fixed_path}")

        # بارگذاری ویدئو با moviepy
        try:
            video = VideoFileClip(temp_fixed_path)
            logger.info(f"Video loaded: duration={video.duration}, size={video.size}")
        except Exception as e:
            logger.error(f"moviepy load error: {str(e)}")
            return {"error": f"moviepy load error: {str(e)}"}, 400

        # ایجاد متن
        try:
            text_clip = TextClip(
                text, fontsize=50, color='white', stroke_color='black',
                stroke_width=2, font='Vazirmatn'
            ).set_duration(video.duration).set_position(('center', 'bottom'))
            logger.info("Text clip created")
        except Exception as e:
            logger.error(f"Text clip creation error: {str(e)}")
            return {"error": f"Text clip creation error: {str(e)}"}, 400

        # ترکیب ویدئو و متن
        try:
            final_video = CompositeVideoClip([video, text_clip])
            logger.info("Video and text composited")
        except Exception as e:
            logger.error(f"Composite error: {str(e)}")
            return {"error": f"Composite error: {str(e)}"}, 400

        # ذخیره ویدئو نهایی
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_output:
            output_path = temp_output.name
        try:
            final_video.write_videofile(
                output_path, codec='libx264', audio_codec='aac',
                bitrate='500k', fps=24, logger=None
            )
            logger.info(f"Video written to: {output_path}, size: {os.path.getsize(output_path)} bytes")
        except Exception as e:
            logger.error(f"Write video error: {str(e)}")
            return {"error": f"Write video error: {str(e)}"}, 400
        finally:
            video.close()
            final_video.close()

        # ارسال فایل
        try:
            response = send_file(output_path, mimetype='video/mp4')
            logger.info("Video sent to client")
            return response
        except Exception as e:
            logger.error(f"Send file error: {str(e)}")
            return {"error": f"Send file error: {str(e)}"}, 400
        finally:
            # پاکسازی فایل‌های موقت
            for path in [temp_video_path, temp_fixed_path, output_path]:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        logger.info(f"Deleted temp file: {path}")
                except Exception as e:
                    logger.error(f"Error deleting temp file {path}: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
