from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random
import asyncio

# Թեմատիկ հարցեր էմոջիներով
quiz_questions = [
    {
        "category": "💻 Technology",
        "question": "What does CPU stand for?",
        "options": ["Central Processing Unit", "Computer Power User", "Central Program Unit"],
        "answer": 0,
        "explanation": "CPU is the brain of the computer where most calculations take place."
    },
    {
        "category": "🔒 Security",
        "question": "Which port is used for HTTPS?",
        "options": ["80", "21", "443"],
        "answer": 2,
        "explanation": "Port 443 is used for secure HTTPS communication."
    },
    {
        "category": "🤖 AI",
        "question": "What language is mostly used for AI?",
        "options": ["Python", "C#", "HTML"],
        "answer": 0,
        "explanation": "Python is widely used in AI due to its rich libraries and simplicity."
    },
    {
        "category": "🌍 Geography",
        "question": "What is the capital of France?",
        "options": ["Paris", "Berlin", "Madrid"],
        "answer": 0,
        "explanation": "Paris is the capital and largest city of France."
    },
    {
        "category": "📚 Literature",
        "question": "Who wrote 'Romeo and Juliet'?",
        "options": ["William Shakespeare", "Charles Dickens", "Leo Tolstoy"],
        "answer": 0,
        "explanation": "'Romeo and Juliet' is a famous tragedy written by Shakespeare."
    },
]

# Ավելացնենք sample հարցեր 100 հատ (պատահական է)
for i in range(6, 106):
    quiz_questions.append({
        "category": "❓ Random",
        "question": f"Sample Question {i}?",
        "options": ["Option A", "Option B", "Option C"],
        "answer": random.randint(0, 2),
        "explanation": "This is a sample question explanation."
    })

MAX_QUESTIONS_PER_QUIZ = 5

# user_id → dict with keys: asked_questions, score, question_number, current_question
user_quiz_state = {}

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Initialize quiz state
    user_quiz_state[user_id] = {
        "asked_questions": [],
        "score": 0,
        "question_number": 0,
    }
    await send_quiz_question(update, context, user_id)

async def send_quiz_question(update_or_query, context, user_id):
    state = user_quiz_state.get(user_id)
    if not state:
        # No quiz started
        if hasattr(update_or_query, "message"):
            await update_or_query.message.reply_text("❌ Please start the quiz with /quiz command.")
        else:
            await update_or_query.edit_message_text("❌ Please start the quiz with /quiz command.")
        return

    if state["question_number"] >= MAX_QUESTIONS_PER_QUIZ:
        # Quiz finished
        total_score = state["score"]
        del user_quiz_state[user_id]
        final_text = (
            f"🏆 *Quiz finished!*\n\n"
            f"Your score: *{total_score}/{MAX_QUESTIONS_PER_QUIZ}*\n\n"
            f"Thanks for playing! 🎉"
        )
        if hasattr(update_or_query, "message"):
            await update_or_query.message.reply_text(final_text, parse_mode="Markdown")
        else:
            await update_or_query.edit_message_text(final_text, parse_mode="Markdown")
        return

    # Choose a new question not asked yet
    remaining_questions = [q for q in quiz_questions if q not in state["asked_questions"]]
    if not remaining_questions:
        state["asked_questions"] = []
        remaining_questions = quiz_questions[:]

    question = random.choice(remaining_questions)
    state["current_question"] = question
    state["asked_questions"].append(question)
    state["question_number"] += 1

    buttons = [
        [InlineKeyboardButton(f"{opt} {emoji}", callback_data=f"quiz_answer:{i}")]
        for i, (opt, emoji) in enumerate(zip(question["options"], ["🅰️", "🅱️", "🆎"]))  # nice letter emojis
    ]

    text = (
        f"{question['category']}  |  "
        f"Question {state['question_number']}/{MAX_QUESTIONS_PER_QUIZ}\n\n"
        f"🧠 *{question['question']}*"
    )

    markup = InlineKeyboardMarkup(buttons)

    if hasattr(update_or_query, "message"):
        await update_or_query.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
    else:
        await update_or_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)

async def quiz_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    try:
        data = query.data.split(":")
        if len(data) != 2:
            return

        selected = int(data[1])
        state = user_quiz_state.get(user_id)
        if not state or "current_question" not in state:
            await query.edit_message_text("❌ No active quiz.")
            return

        question = state["current_question"]

        # Initialize user data if not exists
        if user_id not in context.bot_data:
            context.bot_data[user_id] = {"balance": 100}
        
        # Get current balance
        balance = context.bot_data[user_id].get("balance", 100)

        if selected == question["answer"]:
            balance += 10
            context.bot_data[user_id]["balance"] = balance
            state["score"] += 1
            result_text = (
                f"✅ Correct! +10 coins\n"
                f"💰 Balance: {balance}\n\n"
                f"💡 _{question.get('explanation', '')}_"
            )
        else:
            correct = question["options"][question["answer"]]
            result_text = (
                f"❌ Wrong. Correct answer: *{correct}*\n\n"
                f"💡 _{question.get('explanation', '')}_"
            )

        await query.edit_message_text(result_text, parse_mode="Markdown")

        await asyncio.sleep(2)

        # Send next question or finish quiz
        await send_quiz_question(query, context, user_id)
    except Exception as e:
        print(f"Error in quiz_answer_handler: {e}")
        await query.edit_message_text("❌ An error occurred. Please try again.")