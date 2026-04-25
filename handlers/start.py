from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура только с выбором платформ."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎵 TikTok")],
            [KeyboardButton(text="📸 Instagram Reels")],
            [KeyboardButton(text="▶️ YouTube Shorts")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="Выберите платформу"
    )

@router.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer(
        "👋 Привет! Я скачиваю видео из разных платформ без водяных знаков.\n\n"
        "Выберите платформу или используйте меню команд слева от поля ввода.",
        reply_markup=get_main_keyboard()
    )