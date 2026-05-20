import json
import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

# ====================== KẾT NỐI GOOGLE SHEET ======================
SCOPES = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
client = gspread.authorize(creds)

# Thay SHEET_ID bằng ID trong link Sheet của bạn
SHEET_ID = "1DScO7xS7OBcjPsKuRrMDT-Jx31Cfo4Yvj0_OahQEM10"
sheet = client.open_by_key(SHEET_ID).worksheet("SanPham")

# Load Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

SYSTEM_PROMPT = """
Bạn là nhân viên bán hàng nhiệt tình của MinciuFilm (Hải Phòng). 
Chuyên máy ảnh film & digital cũ đã kiểm tra kỹ.
Chính sách: Bảo hành 1 tháng, ship COD toàn quốc không cọc.
Trả lời gần gũi, nhiệt tình, dùng emoji vừa phải.
"""

def get_all_products():
    try:
        data = sheet.get_all_records()
        return data
    except:
        return []

# ====================== BOT ======================
class MinciuFilmBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("🎞️ Máy Film", callback_data='cat_film')],
            [InlineKeyboardButton("📷 Máy Digital", callback_data='cat_digital')],
            [InlineKeyboardButton("🔍 Tra cứu tồn kho", callback_data='tonkho')],
            [InlineKeyboardButton("✍️ Viết Content", callback_data='content')],
            [InlineKeyboardButton("🌐 Link Shop", callback_data='links')],
            [InlineKeyboardButton("💬 Tư vấn tự do", callback_data='free')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "👋 **Chào mừng bạn đến với MinciuFilm!** 📸\n\n"
            "Máy ảnh film & digital cũ chất lượng - Bảo hành 1 tháng\n"
            "Chọn chức năng bên dưới:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == 'tonkho':
            await self.show_inventory(query)
            return
        elif query.data == 'content':
            await query.edit_message_text("✍️ Gửi nội dung bạn muốn viết (ví dụ: caption cho máy Espio 115, kịch bản livestream...):")
            return
        elif query.data == 'links':
            text = "🌐 **MinciuFilm**\n\n" \
                   "📘 FB: https://www.facebook.com/share/18aKwBZR1u/\n" \
                   "📸 IG: https://www.instagram.com/minciu_film\n" \
                   "🧵 Threads: https://www.threads.net/@minciu_film"
            await query.edit_message_text(text, parse_mode='Markdown')
            return

        # Các nút khác
        response = await self.get_gemini_response("Gợi ý máy ảnh phù hợp")
        await query.edit_message_text(response)

    async def show_inventory(self, query):
        products = get_all_products()
        if not products:
            await query.edit_message_text("❌ Không thể đọc dữ liệu kho lúc này.")
            return

        text = "📋 **DANH SÁCH HÀNG TỒN KHO**\n\n"
        for p in products[:15]:  # Giới hạn 15 máy
            text += f"• **{p.get('Tên máy', '')}**\n"
            text += f"   Giá: {p.get('Giá bán', 'Liên hệ')} | Tình trạng: {p.get('Tình trạng', '')}\n\n"

        text += "📌 Dùng lệnh `/tim Tên máy` để tra cứu chi tiết."
        await query.edit_message_text(text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.lower()

        if text.startswith('/tim '):
            keyword = text.replace('/tim ', '')
            await self.search_product(update, keyword)
        elif 'content' in context.user_data or update.message.text.startswith('/content'):
            await self.generate_content(update)
        else:
            response = await self.get_gemini_response(update.message.text)
            await update.message.reply_text(response)

    async def search_product(self, update, keyword):
        products = get_all_products()
        found = [p for p in products if keyword.lower() in str(p.get('Tên máy', '')).lower()]
        
        if found:
            msg = f"🔍 Kết quả tìm '{keyword}':\n\n"
            for p in found:
                msg += f"**{p.get('Tên máy')}**\nGiá: {p.get('Giá bán')}\nTình trạng: {p.get('Tình trạng')}\nGhi chú: {p.get('Ghi chú','')}\n\n"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text(f"Không tìm thấy máy nào có từ khóa '{keyword}'.")

    async def generate_content(self, update):
        # Tạm thời dùng Gemini viết content
        prompt = f"Viết caption bán hàng hấp dẫn cho MinciuFilm về máy ảnh: {update.message.text}"
        response = await self.get_gemini_response(prompt)
        await update.message.reply_text(response)

    async def get_gemini_response(self, user_query: str):
        try:
            products = get_all_products()
            full_prompt = f"{SYSTEM_PROMPT}\n\nDữ liệu kho hàng hiện tại:\n{json.dumps(products, ensure_ascii=False)}\n\nYêu cầu khách: {user_query}"
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logging.error(e)
            return "Mình đang kiểm tra kho, bạn thử lại sau ít phút nhé! 📸"

if __name__ == "__main__":
    bot = MinciuFilmBot()
    app = Application.builder().token(bot.token).build()

    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CallbackQueryHandler(bot.button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    print("🤖 Bot MinciuFilm đã kết nối Google Sheet - Đang chạy...")
    app.run_polling()
