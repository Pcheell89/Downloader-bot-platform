import os
import asyncio
import logging
import aiohttp
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from config import MAX_TELEGRAM_FILE_SIZE, HEADERS
from downloaders import get_tiktok_video_info, get_instagram_video_info, download_youtube_shorts
from handlers.start import get_main_keyboard

router = Router()

class DownloadStates(StatesGroup):
    waiting_for_url = State()
    stopped = State()

PLATFORM_MAP = {
    "🎵 TikTok": "tiktok",
    "📸 Instagram Reels": "instagram",
    "▶️ YouTube Shorts": "youtube_shorts",
}

PLATFORM_NAMES = {
    "tiktok": "TikTok",
    "instagram": "Instagram Reels",
    "youtube_shorts": "YouTube Shorts",
}

DOWNLOAD_FUNCTIONS = {
    "tiktok": get_tiktok_video_info,
    "instagram": get_instagram_video_info,
}

def get_back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Назад")]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

@router.message(Command("stop"))
async def stop_command(message: types.Message, state: FSMContext):
    await state.set_state(DownloadStates.stopped)
    await message.answer(
        "⏸️ Бот остановлен. Для возобновления работы нажмите /start в меню команд.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(DownloadStates.stopped)
async def stopped_handler(message: types.Message):
    await message.reply(
        "🛑 Бот не принимает ссылки. Используйте команду /start в меню (слева от поля ввода), чтобы запустить заново."
    )

# ---------- Выбор платформы ----------

@router.message(F.text.in_(PLATFORM_MAP.keys()))
async def platform_selected(message: types.Message, state: FSMContext):
    platform_name = message.text
    platform = PLATFORM_MAP[platform_name]
    await state.update_data(platform=platform)
    await state.set_state(DownloadStates.waiting_for_url)
    await message.answer(
        f"📎 Отправьте ссылку на видео из <b>{platform_name}</b>.\n"
        "Для возврата нажмите кнопку <b>«🔙 Назад»</b>.",
        reply_markup=get_back_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "🔙 Назад")
async def go_back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Вы вернулись в главное меню. Выберите платформу:",
        reply_markup=get_main_keyboard()
    )

# ---------- Обработка ссылки ----------

@router.message(DownloadStates.waiting_for_url)
async def process_url(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    platform = user_data.get("platform")
    if not platform:
        await message.reply("Сначала выберите платформу через /start")
        await state.clear()
        return

    platform_name = PLATFORM_NAMES.get(platform, platform)
    url = message.text.strip()
    if url == "🔙 Назад":
        return

    domain_checks = {
        "tiktok": "tiktok.com",
        "instagram": "instagram.com",
        "youtube_shorts": "youtube.com/shorts",
    }
    expected = domain_checks.get(platform)
    if expected and expected not in url:
        await message.reply(f"❌ Ссылка должна содержать {expected}. Попробуйте ещё раз.")
        return

    status_msg = await message.reply("⏳ Ищу видео...")

    # ================== YouTube Shorts ==================
    if platform == "youtube_shorts":
        os.makedirs("downloads", exist_ok=True)
        await status_msg.edit_text("📥 Скачиваю и объединяю видео (до минуты)...")
        try:
            file_path = await asyncio.to_thread(download_youtube_shorts, url, "downloads")
        except Exception as e:
            await status_msg.edit_text(f"❌ Ошибка скачивания: {e}")
            return

        if not file_path:
            await status_msg.edit_text("❌ Не удалось скачать видео.")
            return

        actual_size = os.path.getsize(file_path)

        # Если файл > 50 МБ — даём прямую ссылку, так как Bot API не примет
        if actual_size > MAX_TELEGRAM_FILE_SIZE:
            os.remove(file_path)  # файл уже не нужен
            await status_msg.edit_text(
                f"📁 Видео {actual_size / (1024 * 1024):.1f} МБ — превышает лимит Telegram (50 МБ).\n\n"
                f"🔗 Прямая ссылка для скачивания:\n{download_url}\n\n"
                "Ссылка временная, скачайте в ближайшее время.",
                disable_web_page_preview=False
            )
            await message.answer(
                f"📎 Отправьте ещё ссылку на {platform_name} или нажмите «🔙 Назад».",
                reply_markup=get_back_keyboard()
            )
            return

        await status_msg.edit_text("📤 Отправляю видео...")
        try:
            video_file = FSInputFile(file_path)
            await message.reply_video(video=video_file, caption="✅ Готово!")
        except Exception as e:
            await message.reply(f"❌ Ошибка при отправке видео: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

        await status_msg.delete()
        await message.answer(
            f"📎 Отправьте ещё ссылку на {platform_name} или нажмите «🔙 Назад».",
            reply_markup=get_back_keyboard()
        )
        return

    # ================== TikTok / Instagram ==================
    download_func = DOWNLOAD_FUNCTIONS.get(platform)
    if not download_func:
        await status_msg.edit_text("❌ Платформа не поддерживается.")
        await state.clear()
        return

    info = await download_func(url)
    if not info:
        await status_msg.edit_text("❌ Не удалось получить видео. Проверьте ссылку или приватность.")
        return

    download_url = info["video_url"]
    video_id = info["video_id"]
    file_size = info.get("file_size")

    # Если заранее известен размер и он > 50 МБ — сразу даём ссылку, не скачивая
    if file_size and file_size > MAX_TELEGRAM_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        await status_msg.edit_text(
            f"📁 Видео {size_mb:.1f} МБ — превышает лимит Telegram (50 МБ).\n\n"
            f"🔗 Прямая ссылка для скачивания:\n{download_url}\n\n"
            "Ссылка временная, скачайте в ближайшее время.",
            disable_web_page_preview=False
        )
        await message.answer(
            f"📎 Отправьте ещё ссылку на {platform_name} или нажмите «🔙 Назад».",
            reply_markup=get_back_keyboard()
        )
        return

    # Иначе скачиваем
    os.makedirs("downloads", exist_ok=True)
    file_path = os.path.join("downloads", f"{platform}_{video_id}.mp4")

    await status_msg.edit_text("📥 Скачиваю видео...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, timeout=120, headers=HEADERS) as resp:
                if resp.status != 200:
                    await status_msg.edit_text(f"❌ Ошибка при скачивании: HTTP {resp.status}")
                    return
                with open(file_path, 'wb') as f:
                    f.write(await resp.read())
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка скачивания: {e}")
        return

    actual_size = os.path.getsize(file_path)

    # Если фактический размер превысил 50 МБ — удаляем файл и даём ссылку
    if actual_size > MAX_TELEGRAM_FILE_SIZE:
        os.remove(file_path)
        await status_msg.edit_text(
            f"📁 Скачанный файл {actual_size / (1024 * 1024):.1f} МБ превышает 50 МБ.\n\n"
            f"🔗 Прямая ссылка для скачивания:\n{download_url}\n\n"
            "Ссылка временная, скачайте в ближайшее время.",
            disable_web_page_preview=False
        )
        await message.answer(
            f"📎 Отправьте ещё ссылку на {platform_name} или нажмите «🔙 Назад».",
            reply_markup=get_back_keyboard()
        )
        return

    # Отправляем как видео (≤ 50 МБ)
    await status_msg.edit_text("📤 Отправляю видео...")
    try:
        video_file = FSInputFile(file_path)
        await message.reply_video(video=video_file, caption="✅ Готово!")
    except Exception as e:
        await message.reply(f"❌ Ошибка при отправке видео: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    await status_msg.delete()
    await message.answer(
        f"📎 Отправьте ещё ссылку на {platform_name} или нажмите «🔙 Назад».",
        reply_markup=get_back_keyboard()
    )