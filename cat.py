import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# Состояния для ConversationHandler
GET_IMAGE, GET_TEXTS, SELECT_STYLE = range(3)

TOKEN = "Хыхыхы"

# Улучшенная клавиатура для главного меню
main_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🎨 Создать мем")],
        [KeyboardButton("ℹ️ Помощь")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие..."
)

# Стили для мемов с эмодзи
STYLES = {
    "🎭 Классика": "classic",
    "🌚 Тёмный": "dark",
    "🌀 Размытый": "blur",
    "🔃 Инвертированный": "invert",
    "📜 Сепия": "sepia",
    "🧊 Пиксельный": "pixel",
    "🖍 Контур": "contour",
    "🌈 Радуга": "rainbow",
    "👻 Призрак": "ghost"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤖 Привет! Я бот для создания мемов с кучей крутых функций!\n"
        "Выбери действие:",
        reply_markup=main_keyboard
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📌 Как использовать бота:\n"
        "1. Нажми '🎨 Создать мем' или отправь /create\n"
        "2. Отправь изображение\n"
        "3. Выбери стиль мема\n"
        "4. Отправь два текста через пробел (верхний и нижний)\n\n"
        "Пример: 'Верхний Текст Нижний Текст'\n\n"
        "🎨 Доступные стили:\n"
        + "\n".join([f"• {style}" for style in STYLES.keys()]),
        reply_markup=main_keyboard,
        parse_mode="Markdown"
    )

async def create_meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📸 Отправь мне картинку для мема",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🚫 Отмена")]], resize_keyboard=True)
    )
    return GET_IMAGE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🚫 Действие отменено",
        reply_markup=main_keyboard
    )
    return ConversationHandler.END

def apply_style(image, style):
    if style == "dark":
        return ImageOps.autocontrast(image.convert('L'))
    elif style == "blur":
        return image.filter(ImageFilter.GaussianBlur(3))
    elif style == "invert":
        return ImageOps.invert(image)
    elif style == "sepia":
        sepia = []
        r, g, b = (239, 224, 185)
        for i in range(256):
            sepia.extend((r*i//255, g*i//255, b*i//255))
        return image.convert("L").convert("RGB", palette=Image.ADAPTIVE, colors=256).point(sepia)
    elif style == "pixel":
        return image.resize((image.width//10, image.height//10)).resize((image.width, image.height))
    elif style == "contour":
        return image.filter(ImageFilter.CONTOUR)
    elif style == "rainbow":
        # Создаем радужный эффект
        width, height = image.size
        rainbow = Image.new('RGB', (width, height))
        for y in range(height):
            hue = int(255 * y / height)
            for x in range(width):
                rainbow.putpixel((x, y), (hue, 255, 255))
        rainbow = rainbow.convert('RGB')
        return Image.blend(image.convert('RGB'), rainbow, 0.3)
    elif style == "ghost":
        # Эффект призрака (полупрозрачный + размытие)
        ghost = image.convert('RGBA')
        ghost.putalpha(128)
        ghost = ghost.filter(ImageFilter.GaussianBlur(2))
        return ghost
    else:  # classic
        return image

def create_meme(image_path, top_text, bottom_text, style="classic", output_path="meme.jpg"):
    try:
        image = Image.open(image_path)
        image = apply_style(image, style)
        
        # Конвертируем обратно в RGB, если изображение в RGBA (например, после эффекта "призрак")
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])  # 3 - это альфа-канал
            image = background
        
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("impact.ttf", size=min(image.width // 10, 40))
        except:
            font = ImageFont.load_default()

        def get_text_width(text):
            return draw.textlength(text, font=font)

        def draw_text(text, y):
            text_width = get_text_width(text)
            x = (image.width - text_width) / 2
            
            # Обводка текста с эффектом
            for dx, dy in [(-2,-2), (-2,2), (2,-2), (2,2), (0,0)]:
                color = "black" if (dx, dy) != (0,0) else "white"
                if style == "rainbow":
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                draw.text((x+dx, y+dy), text, font=font, fill=color)

        # Верхний текст
        if top_text:
            draw_text(top_text, 10)
        
        # Нижний текст
        if bottom_text:
            draw_text(bottom_text, image.height - 50 - font.size)
        
        image.save(output_path)
        return True
    except Exception as e:
        print(f"Error creating meme: {e}")
        return False

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo = await update.message.photo[-1].get_file()
    await photo.download_to_drive("temp_meme.jpg")
    context.user_data['image_path'] = "temp_meme.jpg"
    
    # Разбиваем кнопки стилей на несколько строк по 3 в каждой
    style_buttons = list(STYLES.keys())
    keyboard_layout = [
        style_buttons[i:i+3] for i in range(0, len(style_buttons), 3)
    ]
    keyboard_layout.append([KeyboardButton("🚫 Отмена")])  # Добавляем кнопку отмены
    
    await update.message.reply_text(
        "✅ Отлично! Теперь выбери стиль для мема:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard_layout,
            resize_keyboard=True,
            input_field_placeholder="Выберите стиль..."
        )
    )
    
    return SELECT_STYLE

async def handle_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    style_name = update.message.text
    if style_name not in STYLES:
        await update.message.reply_text("Пожалуйста, выбери стиль из предложенных вариантов")
        return SELECT_STYLE
    
    context.user_data['style'] = STYLES[style_name]
    
    await update.message.reply_text(
        "📝 Теперь отправь два текста через пробел (верхний и нижний)\n"
        "Пример: 'Верхний Текст Нижний Текст'",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🚫 Отмена")]], resize_keyboard=True)
    )
    
    return GET_TEXTS

async def handle_texts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if 'image_path' not in context.user_data:
        await update.message.reply_text("Сначала отправь картинку!")
        return GET_IMAGE
    
    texts = update.message.text.split(maxsplit=1)
    if len(texts) < 2:
        await update.message.reply_text("Нужно два текста через пробел! Пример: 'Верхний Нижний'")
        return GET_TEXTS
    
    top_text, bottom_text = texts[0], texts[1]
    style = context.user_data.get('style', 'classic')
    image_path = context.user_data['image_path']
    
    if create_meme(image_path, top_text, bottom_text, style, "result.jpg"):
        await update.message.reply_photo(
            photo=open("result.jpg", "rb"),
            caption="🎉 Вот твой мем!",
            reply_markup=main_keyboard
        )
    else:
        await update.message.reply_text(
            "😢 Ошибка при создании мема",
            reply_markup=main_keyboard
        )
    
    # Очистка временных файлов
    for file in ["temp_meme.jpg", "result.jpg"]:
        if os.path.exists(file):
            os.remove(file)
    
    context.user_data.clear()
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('create', create_meme_command),
            MessageHandler(filters.Regex('^🎨 Создать мем$'), create_meme_command)
        ],
        states={
            GET_IMAGE: [
                MessageHandler(filters.PHOTO, handle_photo),
                MessageHandler(filters.Regex('^🚫 Отмена$'), cancel)
            ],
            SELECT_STYLE: [
                MessageHandler(filters.TEXT & ~filters.Regex('^🚫 Отмена$'), handle_style),
                MessageHandler(filters.Regex('^🚫 Отмена$'), cancel)
            ],
            GET_TEXTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_texts),
                MessageHandler(filters.Regex('^🚫 Отмена$'), cancel)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    
    # Обработчик текстовых сообщений вне диалога
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_outside_conversation))
    
    app.run_polling()

async def handle_text_outside_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "ℹ️ Помощь":
        await help_command(update, context)
    elif text == "🎨 Создать мем":
        await create_meme_command(update, context)
    else:
        await update.message.reply_text(
            "🤖 Я не понимаю эту команду. Используй кнопки или /help для справки.",
            reply_markup=main_keyboard
        )

if __name__ == "__main__":
    main()
