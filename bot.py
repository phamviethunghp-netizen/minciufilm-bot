import json
import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import google.generativeai as genai

load_dotenv()

# Load dữ liệu sản phẩm
with open('data/products.json', 'r', encoding='utf-8') as f:
    PRODUCTS_DATA = json.load(f)

# Cấu hình Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

SYSTEM_PROMPT = """
Bạn là chuyên gia bán hàng máy ảnh của MinciuFilm - Shop máy ảnh chính hãng uy tín tại Việt Nam.
Tone giọng: Chuyên nghiệp, nhiệt huyết, gần gũi, am hiểu nhiếp ảnh.
Luôn ưu tiên lợi ích cho khách hàng, nhấn mạnh chất lượng, bảo hành, giá trị sử dụng lâu dài.
Trả lời bằng tiếng Việt, lịch sự và thuyết phục.
"""

class MinciuFilmBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📸 Fullframe", callback_data='category_fullframe')],
            [InlineKeyboardButton("📷 APS-C", callback_data='category_apsc')],
            [InlineKeyboardButton("🔭 Lens", callback_data='category_lens')],
            [InlineKeyboardButton("🛠️ Phụ kiện", callback_data='category_accessory')],
            [InlineKeyboardButton("💬 Tư vấn tự do", callback_data='free_chat')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 *Chào mừng bạn đến với MinciuFilm!* 📸\n\n"
            "Mình là bot tư vấn máy ảnh chính hãng.\n"
            "Vui lòng chọn danh mục hoặc chat trực tiếp:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == 'free_chat':
            await query.edit_message_text("💬 Bạn muốn tư vấn gì? Hãy chat trực tiếp nhé!")
            return

        category = query.data.split('_')[1]
        response = await self.get_gemini_response(f"Gợi ý các máy {category} tốt nhất hiện nay cho shop MinciuFilm")
        await query.edit_message_text(response)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        response = await self.get_gemini_response(user_text)
        await update.message.reply_text(response)

    async def get_gemini_response(self, user_query: str):
        try:
            full_prompt = f"{SYSTEM_PROMPT}\n\nDữ liệu sản phẩm:\n{json.dumps(PRODUCTS_DATA, ensure_ascii=False)}\n\nYêu cầu: {user_query}"
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logging.error(e)
            return "Mình đang hơi bận, bạn thử hỏi lại hoặc inbox shop nhé ạ! 📸"

if __name__ == "__main__":
    bot = MinciuFilmBot()
    app = Application.builder().token(bot.token).build()

    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CallbackQueryHandler(bot.button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    print("🤖 Bot MinciuFilm với Menu đã chạy...")
    app.run_polling()