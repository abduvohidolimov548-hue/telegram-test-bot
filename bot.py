from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import json
import os

# ================== SOZLAMALAR ==================
TOKEN = "8404980845:AAE_TgRgmGQN3XmtoTlUbXdqKyMdiDm8h-w"

ADMINS = [
    6581120108,      # 1-admin
    5504394361       # 2-admin (o'zgartiring)
]

CHANNEL_USERNAME = "@Urgut_IM_Math"
DATA_FILE = "tests.json"

user_state = {}

# ================== FAYL FUNKSIYALARI ==================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ================== /start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Kanalga o‘tish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]
    ]
    await update.message.reply_text(
        "Botdan foydalanish uchun kanalga obuna bo‘ling:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== /admin ==================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        return await update.message.reply_text("⛔ Siz admin emassiz")

    keyboard = [
        [InlineKeyboardButton("➕ Test qo‘shish", callback_data="add_test")],
        [InlineKeyboardButton("📊 Natijalarni ko‘rish", callback_data="results")]
    ]
    await update.message.reply_text("🛠 Admin panel", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== CALLBACK ==================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = load_data()

    # --------- KANAL TEKSHIRISH ---------
    if query.data == "check_sub":
        try:
            member = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
            if member.status in ["member", "administrator", "creator"]:
                keyboard = [
                    [InlineKeyboardButton("📝 Test ishlash", callback_data="start_test")]
                ]
                await query.message.reply_text("Asosiy menyu", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                raise Exception
        except:
            await query.message.reply_text("❗ Avval kanalga obuna bo‘ling")

    # --------- USER ---------
    elif query.data == "start_test":
        user_state[uid] = {"step": "test_code"}
        await query.message.reply_text("📌 Test kodini kiriting:")

    # --------- ADMIN ---------
    elif query.data == "add_test" and uid in ADMINS:
        user_state[uid] = {"step": "admin_code"}
        await query.message.reply_text("🧪 Yangi test kodini kiriting:")

    elif query.data == "results" and uid in ADMINS:
        if not data:
            return await query.message.reply_text("❗ Hozircha natijalar yo‘q")

        text = "📊 TEST NATIJALARI:\n\n"
        for tcode, tdata in data.items():
            text += f"🧪 Test: {tcode}\n"
            results = sorted(
                tdata.get("results", []),
                key=lambda x: x["correct"],
                reverse=True
            )
            for r in results:
                text += (
                    f"• {r['name']} | "
                    f"✅ {r['correct']}  "
                    f"❌ {r['wrong']}  "
                    f"⚪ {r['blank']}\n"
                )
            text += "\n"

        await query.message.reply_text(text)

# ================== MESSAGE ==================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text_raw = update.message.text.strip()
    text = text_raw.upper()
    data = load_data()

    if uid not in user_state:
        return

    step = user_state[uid]["step"]

    # --------- ADMIN TEST QO‘SHISH ---------
    if uid in ADMINS and step == "admin_code":
        user_state[uid] = {"step": "admin_answers", "code": text}
        await update.message.reply_text("✍️ To‘g‘ri javoblar (masalan: 1A 2C 3B 4D)")
        return

    if uid in ADMINS and step == "admin_answers":
        answers = {}
        for p in text.split():
            q = ''.join(filter(str.isdigit, p))
            a = ''.join(filter(str.isalpha, p))
            answers[q] = a

        data[user_state[uid]["code"]] = {
            "answers": answers,
            "results": []
        }
        save_data(data)
        user_state.pop(uid)

        await update.message.reply_text("✅ Test muvaffaqiyatli saqlandi")
        return

    # --------- USER TEST ---------
    if step == "test_code":
        if text not in data:
            return await update.message.reply_text("❌ Bunday test kodi topilmadi")
        user_state[uid] = {"step": "name", "code": text}
        await update.message.reply_text("👤 Ism va familiyangizni kiriting:")
        return

    if step == "name":
        user_state[uid]["name"] = text_raw
        user_state[uid]["step"] = "answers"
        await update.message.reply_text("📝 Javoblaringizni kiriting (1A 2C 3B ...)")
        return

    if step == "answers":
        test = data[user_state[uid]["code"]]["answers"]
        user_ans = {}

        for p in text.split():
            q = ''.join(filter(str.isdigit, p))
            a = ''.join(filter(str.isalpha, p))
            user_ans[q] = a

        correct = wrong = blank = 0
        for q, a in test.items():
            if q not in user_ans:
                blank += 1
            elif user_ans[q] == a:
                correct += 1
            else:
                wrong += 1

        data[user_state[uid]["code"]]["results"].append({
            "name": user_state[uid]["name"],
            "correct": correct,
            "wrong": wrong,
            "blank": blank
        })
        save_data(data)
        user_state.pop(uid)

        await update.message.reply_text(
            f"📊 NATIJA:\n"
            f"✅ To‘g‘ri: {correct}\n"
            f"❌ Noto‘g‘ri: {wrong}\n"
            f"⚪ Belgilanmagan: {blank}"
        )

# ================== RUN ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
