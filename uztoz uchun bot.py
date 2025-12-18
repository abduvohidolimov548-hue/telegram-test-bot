from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import json, os

# ================== SOZLAMALAR ==================
TOKEN = "8404980845:AAE_TgRgmGQN3XmtoTlUbXdqKyMdiDm8h-w"
ADMIN_ID = 6581120108
CHANNEL_USERNAME = "@Urgut_IM_Math"   # MAJBURIY KANAL (PUBLIC)

TEST_FILE = "tests.json"
RESULT_FILE = "results.json"

user_state = {}
user_data = {}

# ================== YORDAMCHI FUNKSIYALAR ==================
def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def parse_answers(text):
    text = text.upper().replace("-", "").replace(",", " ")
    parts = text.split()
    res = {}
    for p in parts:
        q = "".join(filter(str.isdigit, p))
        a = "".join(filter(str.isalpha, p))
        if q and a:
            res[q] = a
    return res

# ================== /START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Kanalga o‘tish", url="https://t.me/Urgut_IM_Math")],
        [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]
    ]
    await update.message.reply_text(
        "❗ Botdan foydalanish uchun kanalga obuna bo‘ling:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== /ADMIN ==================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Yangi test qo‘shish", callback_data="admin_add")],
        [InlineKeyboardButton("📊 Testlarim", callback_data="admin_results")]
    ]
    await update.message.reply_text(
        "🛠 ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== CALLBACK ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    tests = load_json(TEST_FILE)
    results = load_json(RESULT_FILE)

    # ===== KANAL TEKSHIRISH =====
    if query.data == "check_sub":
        try:
            member = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
            if member.status in ["member", "administrator", "creator"]:
                user_state[uid] = "wait_test_code"
                return await query.message.reply_text("🆔 Test kodini kiriting:")
            else:
                raise Exception
        except:
            return await query.message.reply_text(
                "❗ Avval kanalga obuna bo‘ling va yana tekshirib ko‘ring."
            )

    # ===== ADMIN =====
    if uid != ADMIN_ID:
        return

    if query.data == "admin_add":
        user_state[uid] = "admin_test_code"
        return await query.message.reply_text("🆔 Test kodini kiriting:")

    if query.data == "admin_results":
        if not results:
            return await query.message.reply_text("📭 Natijalar yo‘q")

        keyboard = [
            [InlineKeyboardButton(code, callback_data=f"show_{code}")]
            for code in results.keys()
        ]
        return await query.message.reply_text(
            "📊 Testlar ro‘yxati:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    if query.data.startswith("show_"):
        code = query.data.replace("show_", "")
        data = results.get(code, [])
        data.sort(key=lambda x: x["correct"], reverse=True)

        text = f"📊 NATIJALAR — {code}\n\n"
        for i, u in enumerate(data, 1):
            text += (
                f"{i}) {u['name']}\n"
                f"📞 {u['phone']}\n"
                f"✅ {u['correct']} | ❌ {u['wrong']} | ➖ {u['unanswered']}\n\n"
            )

        return await query.message.reply_text(text[:4096])

# ================== MESSAGE ==================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    text = update.message.text.strip()

    tests = load_json(TEST_FILE)
    results = load_json(RESULT_FILE)

    # ===== ADMIN TEST QO‘SHISH =====
    if user_state.get(uid) == "admin_test_code" and uid == ADMIN_ID:
        user_data[uid] = {"test_code": text}
        user_state[uid] = "admin_answers"
        return await update.message.reply_text("✅ To‘g‘ri javoblarni kiriting:\n1A 2B 3C 4D")

    if user_state.get(uid) == "admin_answers" and uid == ADMIN_ID:
        tests[user_data[uid]["test_code"]] = parse_answers(text)
        save_json(TEST_FILE, tests)
        user_state.pop(uid)
        return await update.message.reply_text("✅ Test saqlandi")

    # ===== USER FLOW =====
    if user_state.get(uid) == "wait_test_code":
        if text not in tests:
            return await update.message.reply_text("❌ Bunday test kodi topilmadi")
        user_data[uid] = {"test_code": text}
        user_state[uid] = "wait_name"
        return await update.message.reply_text("👤 Ism va familiyangiz:")

    if user_state.get(uid) == "wait_name":
        user_data[uid]["name"] = text
        user_state[uid] = "wait_phone"
        return await update.message.reply_text("📞 Telefon raqamingiz:")

    if user_state.get(uid) == "wait_phone":
        user_data[uid]["phone"] = text
        user_state[uid] = "wait_answers"
        return await update.message.reply_text("📝 Test javoblarini kiriting:\n1A 2B 3C 4D")

    if user_state.get(uid) == "wait_answers":
        correct_answers = tests[user_data[uid]["test_code"]]
        user_answers = parse_answers(text)

        correct = wrong = 0
        for q, a in correct_answers.items():
            if q in user_answers:
                if user_answers[q] == a:
                    correct += 1
                else:
                    wrong += 1

        unanswered = len(correct_answers) - (correct + wrong)

        results.setdefault(user_data[uid]["test_code"], []).append({
            "name": user_data[uid]["name"],
            "phone": user_data[uid]["phone"],
            "correct": correct,
            "wrong": wrong,
            "unanswered": unanswered
        })

        save_json(RESULT_FILE, results)
        user_state.pop(uid)

        return await update.message.reply_text(
            f"📊 NATIJA\n\n"
            f"✅ To‘g‘ri: {correct}\n"
            f"❌ Noto‘g‘ri: {wrong}\n"
            f"➖ Belgilanmagan: {unanswered}"
        )

# ================== RUN ==================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🤖 Bot ishga tushdi")
    app.run_polling()

if __name__ == "__main__":
    main()
