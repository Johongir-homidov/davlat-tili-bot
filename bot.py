"""
Davlat Tili va Umumiy Bilimlar - Telegram Test Boti
Har bir sessiya: 50 ta savol, 1 soat vaqt
Kategoria tanlash menyusi bilan.
"""

import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from questions import QUESTIONS
from config import BOT_TOKEN

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Konstantlar ──────────────────────────────────────────────────────────
QUESTIONS_PER_TEST = 50      # har bir testda 50 ta savol
TEST_DURATION_SEC = 3600     # 1 soat = 3600 sekund
WARN_REMAINING_SEC = 600     # 10 daqiqa qolganda ogohlantirish

# ─── Foydalanuvchi holati ─────────────────────────────────────────────────
# user_sessions[user_id] = {
#   "questions": [...],     # tasodifiy tanlangan 50 ta savol
#   "current": 0,           # joriy savol indeksi
#   "score": 0,             # to'g'ri javoblar soni
#   "start_time": datetime, # test boshlash vaqti
#   "answers": [],          # foydalanuvchi javoblari
#   "msg_id": int,          # oxirgi savol xabari id
#   "warned": bool,         # 10 daqiqa ogohlantirilganmi
#   "category": str,        # tanlangan kategoriya
# }
user_sessions: Dict[int, Dict[str, Any]] = {}


# ─── Kategoriyalar (3 ta asosiy bo'lim) ──────────────────────────────────

# Davlat tili bo'limiga tegishli kategoriyalar
DAVLAT_TILI_CATS = {
    "Adabiyot va madaniyat", "Falsafa va siyosat", "Fan va texnika",
    "Frazeologiya", "Ijtimoiy fanlar", "Ish yuritish", "Leksikologiya",
    "Orfografiya", "Pedagogika", "Qonunchilik", "Tarix", "Uslubiyat"
}

MILLIY_QONUNCHILIK_CAT = "Milliy qonunchilik argos bazasidagi savollar"
AKT_CAT = "Axborot-kommunikatsiya texnologiyalari"
AKT_KOMP_CAT = "AKT (Kompyuter savodxonlik)"
MILLIY2_CAT = "Milliy qonunchilik 2"


def get_questions_by_category(category: str) -> list:
    """Belgilangan kategoriya bo'yicha savollarni qaytaradi."""
    if category == "davlat_tili":
        return [q for q in QUESTIONS if q.get("category", "") in DAVLAT_TILI_CATS]
    elif category == "milliy_qonunchilik":
        return [q for q in QUESTIONS if q.get("category", "") == MILLIY_QONUNCHILIK_CAT]
    elif category == "milliy2":
        return [q for q in QUESTIONS if q.get("category", "") == MILLIY2_CAT]
    elif category == "akt":
        return [q for q in QUESTIONS if q.get("category", "") == AKT_CAT]
    elif category == "akt_komp":
        return [q for q in QUESTIONS if q.get("category", "") == AKT_KOMP_CAT]
    return QUESTIONS


def build_category_keyboard() -> InlineKeyboardMarkup:
    """5 ta asosiy bo'lim tugmalari."""
    dt_count = len(get_questions_by_category("davlat_tili"))
    mq_count = len(get_questions_by_category("milliy_qonunchilik"))
    mq2_count = len(get_questions_by_category("milliy2"))
    akt_count = len(get_questions_by_category("akt"))
    komp_count = len(get_questions_by_category("akt_komp"))
    buttons = [
        [InlineKeyboardButton(f"📝 Davlat tili ({dt_count} ta)", callback_data="cat_davlat_tili")],
        [InlineKeyboardButton(f"⚖️ Milliy qonunchilik ({mq_count} ta)", callback_data="cat_milliy_qonunchilik")],
        [InlineKeyboardButton(f"📚 Milliy qonunchilik 2 ({mq2_count} ta)", callback_data="cat_milliy2")],
        [InlineKeyboardButton(f"💻 Axborot-kommunikatsiya texnologiyalari ({akt_count} ta)", callback_data="cat_akt")],
        [InlineKeyboardButton(f"🖥️ AKT - Kompyuter savodxonlik ({komp_count} ta)", callback_data="cat_akt_komp")],
    ]
    return InlineKeyboardMarkup(buttons)


def build_count_keyboard(category: str) -> InlineKeyboardMarkup:
    """Savol soni tanlash klaviaturasi."""
    buttons = [
        [
            InlineKeyboardButton("🔟 20 ta savol", callback_data=f"cnt_{category}_20"),
            InlineKeyboardButton("📋 50 ta savol", callback_data=f"cnt_{category}_50"),
        ],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_cats")],
    ]
    return InlineKeyboardMarkup(buttons)


# ─── Yordamchi funksiyalar ────────────────────────────────────────────────

def format_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def build_question_keyboard(options: list, q_idx: int) -> InlineKeyboardMarkup:
    """Savolga javob tugmachalari."""
    buttons = []
    labels = ["🅐", "🅑", "🅒", "🅓"]
    for i, opt in enumerate(options):
        label = labels[i] if i < len(labels) else f"{i+1}."
        buttons.append([InlineKeyboardButton(
            f"{label} {opt}", callback_data=f"ans_{q_idx}_{i}"
        )])
    return InlineKeyboardMarkup(buttons)


def build_question_text(session: dict) -> str:
    """Savol matnini formatlash."""
    idx = session["current"]
    total = len(session["questions"])
    q = session["questions"][idx]

    elapsed = (datetime.now() - session["start_time"]).seconds
    remaining = max(0, TEST_DURATION_SEC - elapsed)
    time_str = format_time(remaining)

    category = q.get("category", "Umumiy")
    return (
        f"⏱ *{time_str}* qoldi  |  📊 *{idx+1}/{total}*\n"
        f"🏷 _{category}_\n\n"
        f"*{idx+1}. {q['question']}*"
    )


# ─── Buyruqlar ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Salom, *{user.first_name}*!\n\n"
        "🎓 *Davlat tili va Umumiy bilimlar* test boti.\n\n"
        "📌 *Qoidalar:*\n"
        f"• Har bir testda *{QUESTIONS_PER_TEST} ta* savol\n"
        "• Vaqt: *1 soat* (60 daqiqa)\n"
        "• Har bir savolga *faqat bir marta* javob beriladi\n"
        "• Test oxirida baho e'lon qilinadi\n\n"
        "⬇️ Boshlash uchun /test buyrug'ini yuboring."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Yordam*\n\n"
        "/start — Botni ishga tushirish\n"
        "/test  — Yangi test boshlash\n"
        "/status — Joriy test holati\n"
        "/stop  — Testni to'xtatish\n"
        "/help  — Ushbu yordam\n\n"
        f"📝 Har bir test *{QUESTIONS_PER_TEST} ta* savoldan iborat.\n"
        "⏰ Vaqt *1 soat* (3600 sekund).\n"
        "✅ Tugagach natija ko'rsatiladi."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Avvalgi sessiyani to'xtatish
    if user_id in user_sessions:
        old = user_sessions[user_id]
        await update.message.reply_text(
            "⚠️ Avvalgi test to'xtatildi."
        )
        # Timer ni bekor qilish
        if "timer_job" in old and old["timer_job"]:
            try:
                old["timer_job"].schedule_removal()
            except Exception:
                pass
        user_sessions.pop(user_id, None)

    # Kategoriya tanlash menyusini ko'rsatish
    keyboard = build_category_keyboard()
    await update.message.reply_text(
        "📚 *Qaysi bo'lim bo'yicha test topshirmoqchisiz?*\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def start_test_with_category(chat_id: int, user_id: int, category: str, context: ContextTypes.DEFAULT_TYPE, query=None, q_count: int = None):
    """Tanlangan kategoriya bo'yicha testni boshlash."""
    if q_count is None:
        q_count = QUESTIONS_PER_TEST
    pool = get_questions_by_category(category)
    if not pool:
        text = "❌ Bu bo'limda savollar topilmadi."
        if query:
            await query.edit_message_text(text)
        else:
            await context.bot.send_message(chat_id=chat_id, text=text)
        return

    selected = random.sample(pool, min(q_count, len(pool)))
    cat_names = {
        "davlat_tili": "Davlat tili",
        "milliy_qonunchilik": "Milliy qonunchilik",
        "milliy2": "Milliy qonunchilik 2",
        "akt": "Axborot-kommunikatsiya texnologiyalari",
        "akt_komp": "AKT (Kompyuter savodxonlik)",
    }
    cat_name = cat_names.get(category, category)

    session = {
        "questions": selected,
        "current": 0,
        "score": 0,
        "start_time": datetime.now(),
        "answers": [],
        "msg_id": None,
        "warned": False,
        "timer_job": None,
        "category": cat_name,
    }
    user_sessions[user_id] = session

    start_text = (
        f"🚀 *Test boshlandi!*\n\n"
        f"📚 Bo'lim: *{cat_name}*\n"
        f"📋 Savollar soni: *{len(selected)}*\n"
        f"⏰ Vaqt: *1 soat*\n\n"
        "Har bir savolga to'g'ri javobni bosing."
    )

    if query:
        await query.edit_message_text(start_text, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=chat_id, text=start_text, parse_mode="Markdown")

    # Taymer: 1 soatdan keyin avtomatik tugatish
    job = context.job_queue.run_once(
        auto_end_test,
        TEST_DURATION_SEC,
        data={"user_id": user_id, "chat_id": chat_id},
        name=f"timer_{user_id}",
    )
    session["timer_job"] = job

    # 10 daqiqa qolganida ogohlantirish
    context.job_queue.run_once(
        warn_time,
        TEST_DURATION_SEC - WARN_REMAINING_SEC,
        data={"user_id": user_id, "chat_id": chat_id},
        name=f"warn_{user_id}",
    )

    # Birinchi savolni yuborish
    await send_question(chat_id, user_id, context)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Faol test yo'q. /test bilan boshlang.")
        return

    s = user_sessions[user_id]
    elapsed = (datetime.now() - s["start_time"]).seconds
    remaining = max(0, TEST_DURATION_SEC - elapsed)
    answered = s["current"]
    total = len(s["questions"])
    correct = s["score"]

    text = (
        f"📊 *Test holati*\n\n"
        f"⏱ Qolgan vaqt: *{format_time(remaining)}*\n"
        f"✅ Javob berildi: *{answered}/{total}*\n"
        f"🎯 To'g'ri: *{correct}*\n"
        f"❌ Noto'g'ri: *{answered - correct}*"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions:
        await update.message.reply_text("❌ Faol test yo'q.")
        return
    await finish_test(update.effective_chat.id, user_id, context, stopped=True)
    await update.message.reply_text("🛑 Test to'xtatildi.")


# ─── Kategoriya tanlash callback ─────────────────────────────────────────

async def handle_category_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # Orqaga qaytish
    if data == "back_to_cats":
        keyboard = build_category_keyboard()
        await query.edit_message_text(
            "📚 *Qaysi bo'lim bo'yicha test topshirmoqchisiz?*\n\nQuyidagi bo'limlardan birini tanlang:",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return

    # Savol soni tanlanganda
    if data.startswith("cnt_"):
        # cnt_{category}_{count}
        parts = data[4:].rsplit("_", 1)
        category = parts[0]
        count = int(parts[1])
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        await start_test_with_category(chat_id, user_id, category, context, query=query, q_count=count)
        return

    # Bo'lim tanlanganda — savol soni klaviaturasini ko'rsat
    category = data[4:]  # len("cat_") == 4
    cat_display = {
        "davlat_tili": "Davlat tili",
        "milliy_qonunchilik": "Milliy qonunchilik",
        "milliy2": "Milliy qonunchilik 2",
        "akt": "Axborot-kommunikatsiya texnologiyalari",
        "akt_komp": "AKT (Kompyuter savodxonlik)",
    }
    name = cat_display.get(category, category)
    pool_size = len(get_questions_by_category(category))
    keyboard = build_count_keyboard(category)
    await query.edit_message_text(
        f"✅ *{name}* bo'limi tanlandi.\n\n"
        f"📦 Jami savollar: *{pool_size} ta*\n\n"
        "📋 *Nechta savol topshirmoqchisiz?*",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ─── Savol yuborish ───────────────────────────────────────────────────────

async def send_question(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    session = user_sessions.get(user_id)
    if not session:
        return

    idx = session["current"]
    total = len(session["questions"])

    if idx >= total:
        await finish_test(chat_id, user_id, context)
        return

    q = session["questions"][idx]
    text = build_question_text(session)
    keyboard = build_question_keyboard(q["options"], idx)

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    session["msg_id"] = msg.message_id


# ─── Callback: javob qabul qilish ─────────────────────────────────────────

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data  # "ans_{q_idx}_{choice}"

    if user_id not in user_sessions:
        await query.edit_message_text("❌ Faol test topilmadi. /test bilan boshlang.")
        return

    session = user_sessions[user_id]

    parts = data.split("_")
    if len(parts) != 3 or parts[0] != "ans":
        return

    q_idx = int(parts[1])
    choice = int(parts[2])

    # Faqat joriy savol uchun javob qabul qilinadi
    if q_idx != session["current"]:
        await query.answer("⚠️ Bu savolga allaqachon javob berilgan!", show_alert=True)
        return

    q = session["questions"][q_idx]
    correct = q["correct"]
    is_correct = (choice == correct)

    if is_correct:
        session["score"] += 1
        result_emoji = "✅"
        result_text = "To'g'ri!"
    else:
        result_emoji = "❌"
        correct_text = q["options"][correct]
        result_text = f"Noto'g'ri! To'g'ri javob: *{correct_text}*"

    session["answers"].append({
        "q_idx": q_idx,
        "choice": choice,
        "correct": is_correct,
    })

    # Savolni natija bilan yangilash
    options_text = ""
    labels = ["🅐", "🅑", "🅒", "🅓"]
    for i, opt in enumerate(q["options"]):
        if i == correct:
            mark = "✅"
        elif i == choice and not is_correct:
            mark = "❌"
        else:
            mark = "◻️"
        lbl = labels[i] if i < len(labels) else f"{i+1}."
        options_text += f"\n{mark} {lbl} {opt}"

    answered_count = q_idx + 1
    total = len(session["questions"])
    score_now = session["score"]

    updated_text = (
        f"*{answered_count}/{total}. {q['question']}*\n"
        f"{options_text}\n\n"
        f"{result_emoji} {result_text}\n\n"
        f"🎯 Hozircha: {score_now}/{answered_count}"
    )

    try:
        await query.edit_message_text(updated_text, parse_mode="Markdown")
    except Exception:
        pass

    session["current"] += 1

    # Keyingi savolni yuborish
    await asyncio.sleep(0.5)
    if session["current"] < total:
        await send_question(query.message.chat_id, user_id, context)
    else:
        await finish_test(query.message.chat_id, user_id, context)


# ─── Test tugash ──────────────────────────────────────────────────────────

async def finish_test(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE, stopped=False):
    session = user_sessions.pop(user_id, None)
    if not session:
        return

    # Timerni bekor qilish
    if session.get("timer_job"):
        try:
            session["timer_job"].schedule_removal()
        except Exception:
            pass
    # Ogohlantirish jobini bekor qilish
    current_jobs = context.job_queue.get_jobs_by_name(f"warn_{user_id}")
    for job in current_jobs:
        job.schedule_removal()

    total = len(session["questions"])
    score = session["score"]
    answered = session["current"]
    elapsed = (datetime.now() - session["start_time"]).seconds

    # Baho hisoblash
    if answered > 0:
        percent = round(score / answered * 100)
    else:
        percent = 0

    if percent >= 86:
        grade = "⭐⭐⭐⭐⭐ A'lo (5)"
        color = "🟢"
    elif percent >= 71:
        grade = "⭐⭐⭐⭐ Yaxshi (4)"
        color = "🔵"
    elif percent >= 56:
        grade = "⭐⭐⭐ Qoniqarli (3)"
        color = "🟡"
    else:
        grade = "⭐ Qoniqarsiz (2)"
        color = "🔴"

    if stopped:
        header = "🛑 *Test to'xtatildi*"
    else:
        header = "🏁 *Test yakunlandi!*"

    text = (
        f"{header}\n\n"
        f"📋 Jami savollar: *{total}*\n"
        f"✅ Javob berildi: *{answered}*\n"
        f"🎯 To'g'ri javoblar: *{score}*\n"
        f"❌ Noto'g'ri javoblar: *{answered - score}*\n"
        f"📊 Foiz: *{percent}%*\n"
        f"⏱ Sarflangan vaqt: *{format_time(elapsed)}*\n\n"
        f"{color} *Baho: {grade}*\n\n"
        "Yangi test boshlash uchun /test ni bosing."
    )

    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")


# ─── Avtomatik tugatish (timer) ───────────────────────────────────────────

async def auto_end_test(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data["user_id"]
    chat_id = job.data["chat_id"]

    if user_id in user_sessions:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ *Vaqt tugadi!* Test avtomatik yakunlanmoqda...",
            parse_mode="Markdown",
        )
        await finish_test(chat_id, user_id, context)


async def warn_time(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data["user_id"]
    chat_id = job.data["chat_id"]

    if user_id in user_sessions:
        s = user_sessions[user_id]
        remaining_q = len(s["questions"]) - s["current"]
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"⚠️ *Diqqat!* Testga *10 daqiqa* qoldi!\n"
                f"📋 Qolgan savollar: *{remaining_q}*"
            ),
            parse_mode="Markdown",
        )


# ─── Asosiy ishga tushurish ───────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Buyruqlar
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("test", cmd_test))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stop", cmd_stop))

    # Callback
    app.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^ans_"))
    app.add_handler(CallbackQueryHandler(handle_category_select, pattern=r"^cat_"))
    app.add_handler(CallbackQueryHandler(handle_category_select, pattern=r"^cnt_"))
    app.add_handler(CallbackQueryHandler(handle_category_select, pattern=r"^back_to_cats$"))

    # Bot komandalar menyusi
    async def post_init(app):
        await app.bot.set_my_commands([
            BotCommand("start", "Botni ishga tushirish"),
            BotCommand("test", "Yangi test boshlash (50 savol, 1 soat)"),
            BotCommand("status", "Joriy test holati"),
            BotCommand("stop", "Testni to'xtatish"),
            BotCommand("help", "Yordam"),
        ])

    app.post_init = post_init

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
