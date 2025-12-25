import os, json, time, asyncio, threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from aiohttp import web

# ================= SOZLAMALAR =================
TOKEN = "8404980845:AAE_TgRgmGQN3XmtoTlUbXdqKyMdiDm8h-w"
CHANNEL = "@Urgut_IM_Math"
ADMINS = [6581120108]

TEST_FILE = "tests.json"
RESULT_FILE = "results.json"

# ================= FAYLLAR =================
if not os.path.exists(TEST_FILE):
    with open(TEST_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(RESULT_FILE):
    with open(RESULT_FILE, "w") as f:
        json.dump({}, f)

def load_tests():
    with open(TEST_FILE) as f:
        return json.load(f)

def save_tests(data):
    with open(TEST_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_results():
    with open(RESULT_FILE) as f:
        return json.load(f)

def save_results(data):
    with open(RESULT_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ================= TELEGRAM HANDLERLARI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📢 Kanalga o‘tish", url=f"https://t.me/{CHANNEL[1:]}")],
        [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]
    ]
    await update.message.reply_text("Botdan foydalanish uchun kanalga obuna bo‘ling 👇",
                                    reply_markup=InlineKeyboardMarkup(kb))

async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        m = await context.bot.get_chat_member(CHANNEL, q.from_user.id)
        if m.status in ("member", "administrator", "creator"):
            kb = [[InlineKeyboardButton("📝 Test ishlash", callback_data="enter_test")]]
            await q.message.reply_text("✅ Obuna tasdiqlandi", reply_markup=InlineKeyboardMarkup(kb))
        else:
            raise Exception
    except:
        await q.message.reply_text("❗ Avval kanalga obuna bo‘ling")

async def enter_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data["step"] = "test_code"
    await update.callback_query.message.reply_text("🔢 Test kodini kiriting:")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        return await update.message.reply_text("⛔ Ruxsat yo‘q")
    kb = [
        [InlineKeyboardButton("➕ Test yaratish", callback_data="create_test")],
        [InlineKeyboardButton("❌ Test o‘chirish", callback_data="delete_test")],
        [InlineKeyboardButton("📊 Natijalar", callback_data="view_results")]
    ]
    await update.message.reply_text("🛠 ADMIN PANEL", reply_markup=InlineKeyboardMarkup(kb))

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tests = load_tests()
    if q.data == "create_test":
        context.user_data["step"] = "new_code"
        await q.message.reply_text("🆕 Test kodini kiriting:")
        return
    if q.data == "delete_test":
        if not tests:
            return await q.message.reply_text("❌ Test yo‘q")
        kb = [[InlineKeyboardButton(k, callback_data=f"del_{k}")] for k in tests]
        await q.message.reply_text("🗑 O‘chiriladigan test:", reply_markup=InlineKeyboardMarkup(kb))
        return
    if q.data.startswith("del_"):
        code = q.data[4:]
        tests.pop(code, None)
        save_tests(tests)
        await q.message.reply_text(f"❌ {code} o‘chirildi")
        return
    if q.data == "view_results":
        results = load_results()
        if not results:
            return await q.message.reply_text("📭 Natijalar yo‘q")
        kb = [[InlineKeyboardButton(k, callback_data=f"res_{k}")] for k in results]
        await q.message.reply_text("📂 Testlar:", reply_markup=InlineKeyboardMarkup(kb))
        return
    if q.data.startswith("res_"):
        code = q.data[4:]
        res = load_results().get(code, [])
        res = sorted(res, key=lambda x: x["correct"], reverse=True)
        txt = f"📊 {code} natijalari:\n\n"
        for i, r in enumerate(res, 1):
            txt += f"{i}) {r['name']} | {r['phone']}\n"
            txt += f"✅{r['correct']} ❌{r['wrong']} ⚪{r['empty']}\n\n"
        await q.message.reply_text(txt)

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    step = context.user_data.get("step")

    # ===== ADMIN TEST YARATISH =====
    if step == "new_code":
        context.user_data["code"] = text
        context.user_data["step"] = "new_answers"
        await update.message.reply_text("✍️ To‘g‘ri javoblar (A B C D):")
        return
    if step == "new_answers":
        context.user_data["answers"] = text.split()
        context.user_data["step"] = "new_time"
        await update.message.reply_text("⏱ Test vaqti (daqiqa):")
        return
    if step == "new_time":
        try:
            duration = int(text)
        except:
            return await update.message.reply_text("❌ Iltimos, son kiriting")
        end_time = int(time.time()) + duration * 60
        tests = load_tests()
        tests[context.user_data["code"]] = {
            "answers": context.user_data["answers"],
            "end_time": end_time
        }
        save_tests(tests)
        await update.message.reply_text("✅ Test yaratildi va timer boshlandi")
        # Timer tugagach avtomatik natija chiqarish
        asyncio.create_task(auto_publish_result(context, context.user_data["code"], end_time))
        context.user_data.clear()
        return

    # ===== USER TEST =====
    if step == "test_code":
        tests = load_tests()
        if text not in tests:
            return await update.message.reply_text("❌ Bunday test yo‘q")
        if time.time() > tests[text]["end_time"]:
            return await update.message.reply_text("⛔ Bu test vaqti tugagan")
        context.user_data["test"] = text
        context.user_data["step"] = "name"
        await update.message.reply_text("👤 Ism Familiya:")
        return
    if step == "name":
        context.user_data["name"] = update.message.text
        context.user_data["step"] = "phone"
        await update.message.reply_text("📞 Telefon:")
        return
    if step == "phone":
        context.user_data["phone"] = update.message.text
        context.user_data["step"] = "answers"
        await update.message.reply_text("✍️ Javoblar (A B C ...):")
        return
    if step == "answers":
        tests = load_tests()
        correct_ans = tests[context.user_data["test"]]["answers"]
        user_ans = text.split()
        correct = wrong = empty = 0
        for i in range(len(correct_ans)):
            if i >= len(user_ans):
                empty += 1
            elif user_ans[i] == correct_ans[i]:
                correct += 1
            else:
                wrong += 1
        results = load_results()
        results.setdefault(context.user_data["test"], []).append({
            "name": context.user_data["name"],
            "phone": context.user_data["phone"],
            "correct": correct,
            "wrong": wrong,
            "empty": empty
        })
        save_results(results)
        await update.message.reply_text("✅ Javob qabul qilindi. Natijalar test tugagach e’lon qilinadi.")
        context.user_data.clear()

# ================= AUTOMATIC RESULT PUBLISH =================
async def auto_publish_result(context: ContextTypes.DEFAULT_TYPE, code: str, end_time: int):
    await asyncio.sleep(max(0, end_time - time.time()))
    results = load_results().get(code, [])
    if not results:
        return
    results = sorted(results, key=lambda x: x["correct"], reverse=True)
    txt = f"📊 {code} test natijalari:\n\n"
    for i, r in enumerate(results, 1):
        txt += f"{i}) {r['name']} | {r['phone']}\n"
        txt += f"✅{r['correct']} ❌{r['wrong']} ⚪{r['empty']}\n\n"
    try:
        await context.bot.send_message(CHANNEL, txt)
    except:
        pass

# ================= HTTP SERVER =================
async def handle_root(request):
    return web.Response(text="Bot is running!")

async def start_http_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP server running on port {port}")

def run_http_server_thread():
    asyncio.run(start_http_server())

# ================= MAIN =================
def main():
    bot_app = ApplicationBuilder().token(TOKEN).build()

    # Handlerlar
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("admin", admin))
    bot_app.add_handler(CallbackQueryHandler(check_sub, pattern="check_sub"))
    bot_app.add_handler(CallbackQueryHandler(enter_test, pattern="enter_test"))
    bot_app.add_handler(CallbackQueryHandler(admin_buttons))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    # HTTP serverni alohida threadda ishga tushiramiz
    threading.Thread(target=run_http_server_thread, daemon=True).start()

    # Telegram bot polling
    bot_app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
