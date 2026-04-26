import logging
import aiohttp
import yt_dlp
from config import HEADERS

async def get_instagram_video_info(url: str) -> dict | None:
    """Возвращает прямую ссылку на Instagram Reels в лучшем качестве со звуком."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            if not formats:
                logging.error("Instagram: нет доступных форматов")
                return None

            # Ищем лучший формат с видео и аудио
            best_combined = None
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    if (best_combined is None or
                        (f.get('height', 0) or 0) > (best_combined.get('height', 0) or 0) or
                        (f.get('tbr', 0) or 0) > (best_combined.get('tbr', 0) or 0)):
                        best_combined = f

            if not best_combined:
                best_combined = formats[-1]  # запасной вариант

            download_url = best_combined.get('url')
            if not download_url:
                logging.error("Instagram: не найден URL видео")
                return None

            file_size = best_combined.get('filesize') or best_combined.get('filesize_approx')
            if not file_size:
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.head(download_url, allow_redirects=True, timeout=10, headers=HEADERS) as resp:
                            if resp.status == 200:
                                cl = resp.headers.get("Content-Length")
                                if cl:
                                    file_size = int(cl)
                    except Exception as e:
                        logging.warning(f"Instagram: не удалось получить размер: {e}")

            return {
                "video_url": download_url,
                "video_id": info.get('id', 'ig_reel'),
                "file_size": file_size
            }
    except Exception as e:
        logging.error(f"Instagram yt-dlp ошибка: {e}")
        return None