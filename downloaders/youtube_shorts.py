import os
import logging
import yt_dlp

def download_youtube_shorts(url: str, output_dir: str) -> str | None:
    """
    Синхронно скачивает YouTube Shorts в наилучшем качестве со звуком.
    Возвращает путь к готовому файлу или None при ошибке.
    """
    try:
        import subprocess
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        ffmpeg_available = True
    except (FileNotFoundError, subprocess.CalledProcessError):
        ffmpeg_available = False

    if ffmpeg_available:
        ydl_format = 'bestvideo[height<=1440]+bestaudio/best[height<=1440]'
    else:
        ydl_format = 'best'

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': ydl_format,
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if ffmpeg_available:
                base, _ = os.path.splitext(filename)
                filename = base + '.mp4'
            if not os.path.exists(filename):
                logging.error(f"YouTube Shorts: файл {filename} не найден после скачивания")
                return None
            return filename
    except Exception as e:
        logging.error(f"YouTube Shorts ошибка скачивания: {e}")
        return None