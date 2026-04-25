import logging
import aiohttp
from config import TIKTOK_API_URL, HEADERS

async def get_tiktok_video_info(url: str) -> dict | None:
    params = {"url": url}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(TIKTOK_API_URL, params=params, headers=HEADERS) as resp:
                if resp.status != 200:
                    logging.error(f"TikTok API HTTP {resp.status}")
                    return None
                data = await resp.json(content_type=None)
        except Exception as e:
            logging.error(f"TikTok API исключение: {e}")
            return None

        if data.get("code") != 0 or not data.get("data"):
            logging.error(f"TikTok API ошибка: {data.get('msg', '')}")
            return None

        video_data = data["data"]
        download_url = video_data.get("hdplay") or video_data.get("play")
        if not download_url:
            logging.error("TikTok: нет ссылки без водяного знака")
            return None

        file_size = None
        try:
            async with session.head(download_url, allow_redirects=True, timeout=10, headers=HEADERS) as head_resp:
                if head_resp.status == 200:
                    cl = head_resp.headers.get("Content-Length")
                    if cl:
                        file_size = int(cl)
        except Exception as e:
            logging.warning(f"TikTok: не удалось получить размер: {e}")

        return {
            "video_url": download_url,
            "video_id": video_data.get("id"),
            "file_size": file_size
        }