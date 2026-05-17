import json
import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import google.generativeai as genai

load_dotenv()

with open('data/products.json', 'r', encoding='utf-8') as f:
    PRODUCTS_DATA = json.load(f)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

SYSTEM_PROMPT = """
Bạn là nhân viên bán hàng nhiệt tình của MinciuFilm (Hải Phòng) - Chuyên máy ảnh film & digital cũ chất lượng.

Thông tin shop luôn nhấn mạnh:
- Máy cũ đã kiểm tra kỹ, vệ sinh sạch, hoạt động tốt.
- Báo rõ lỗi (nếu có).
- Bảo hành 1 tháng.
- Ship COD toàn quốc, KHÔNG CỌC.
- Giao dịch trực tiếp tại Hải Phòng & Huế.

Phong cách: Gần gũi, nhiệt tình, am hiểu máy film, dùng emoji vừa phải, trả lời bằng tiếng Việt tự nhiên.
Luôn hỏi thêm nhu cầu (ngân sách, chụp gì, film hay digital...) để tư vấn chính xác.
"""

class MinciuFilmBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🎞️ Máy Film", callback_data='cat_film')],
            [InlineKeyboardButton("📷 Máy Digital", callback_data='cat_digital')],
            [InlineKeyboardButton("🔍 Point & Shoot Film", callback_data='pns')],
            [InlineKeyboardButton("📸 SLR & Rangefinder", callback_data='slr')],
            [InlineKeyboardButton("🌟 Máy Đang Hot", callback_data='hot')],
            [InlineKeyboardButton("💰 Xem Giá & Catalog", callback_data='price')],
            [InlineKeyboardButton("🌐 Link Shop", callback_data='links')],
            [InlineKeyboardButton("💬 Tư vấn tự do", callback_data='free')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "👋 **Chào mừng bạn đến với MinciuFilm!** 📸\n\n"
            "Máy ảnh film & digital cũ đã kiểm tra - Bảo hành 1 tháng - Ship COD toàn quốc\n\n"
            "Chọn danh mục bên dưới để xem máy nhé!",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        prompts = {
            'cat_film': "Gợi ý các máy film đẹp đang có tại MinciuFilm",
            'cat_digital': "Gợi ý các máy digital compact và superzoom đang có",
            'pns': "Gợi ý máy Point & Shoot film như Espio, Canon Autoboy, Bigmini...",
            'slr': "Gợi ý máy SLR film và Rangefinder chất lượng",
            'hot': "Gợi ý những máy đang hot, bán chạy hoặc mới về của MinciuFilm",
            'price': "Hiện giá một số máy tiêu biểu và chính sách giá của shop",
            'links': "Gửi các link Facebook, Instagram, Threads của MinciuFilm cho khách",
            'free': "Mở chế độ tư vấn tự do"
        }

        if query.data == 'links':
            text = "🌐 **Link MinciuFilm**\n\n" \
                   "📘 Facebook: https://www.facebook.com/minciu_film\n" \
                   "📸 Instagram: https://www.instagram.com/minciu_film\n" \
                   "🧵 Threads: https://www.threads.net/@minciu_film\n\n" \
                   "Bạn có thể xem thêm máy mới nhất tại đây ạ!"
            await query.edit_message_text(text, parse_mode='Markdown')
            return

        user_query = prompts.get(query.data, "Tư vấn máy ảnh")
        response = await self.get_gemini_response(user_query)
        await query.edit_message_text(response, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        response = await self.get_gemini_response(update.message.text)
        await update.message.reply_text(response)

    async def get_gemini_response(self, user_query: str):
        try:
            full_prompt = f"{SYSTEM_PROMPT}\n\nThông tin sản phẩm:\n{json.dumps(PRODUCTS_DATA, ensure_ascii=False)}\n\nYêu cầu: {user_query}"
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logging.error(e)
            return "Mình đang kiểm tra máy cho bạn, nhắn lại sau ít phút nhé! 📸"

if __name__ == "__main__":
    bot = MinciuFilmBot()
    app = Application.builder().token(bot.token).build()

    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CallbackQueryHandler(bot.button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    print("🤖 Bot MinciuFilm - Menu chuyên nghiệp đã chạy!")
    app.run_polling()