import telebot
import psycopg2
from psycopg2 import sql
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot token and admin settings
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Database connection
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

# Function to check points and user data
def get_user_data(user_id):
    cursor.execute("SELECT username, points, last_daily, ref_by FROM users WHERE user_id = %s", (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        return user_data
    return None

# Function to create user if not exists
def create_user(user_id, username, ref_by):
    cursor.execute("INSERT INTO users (user_id, username, points, last_daily, ref_by) VALUES (%s, %s, %s, %s, %s)",
                   (user_id, username, 0, datetime.datetime.now(), ref_by))
    conn.commit()

# Command to start the bot and show the UI
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    ref_id = message.text.split(' ')[1] if len(message.text.split()) > 1 else None
    username = message.from_user.username or message.from_user.first_name
    
    user_data = get_user_data(user_id)
    if not user_data:
        if ref_id:
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (ref_id,))
            ref_data = cursor.fetchone()
            ref_by = ref_data[0] if ref_data else None
        else:
            ref_by = None
        create_user(user_id, username, ref_by)
        user_data = (username, 0, None, ref_by)

    user_name, points, last_daily, ref_by = user_data
    ref_link = f"https://t.me/IGVaultBot?start={user_id}"

    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Check Points", callback_data="check_points"))
    markup.add(telebot.types.InlineKeyboardButton("Daily Reward", callback_data="daily_reward"))
    markup.add(telebot.types.InlineKeyboardButton("Redeem IG Account", callback_data="redeem_account"))
    markup.add(telebot.types.InlineKeyboardButton("Referral Link", url=ref_link))

    bot.send_message(message.chat.id, f"Welcome {user_name}!
Points: {points}
Referral Link: {ref_link}", reply_markup=markup)

# Command to handle daily reward
@bot.callback_query_handler(func=lambda call: call.data == 'daily_reward')
def daily_reward(call):
    user_id = call.from_user.id
    user_data = get_user_data(user_id)

    if user_data:
        username, points, last_daily, ref_by = user_data
        if last_daily and (datetime.datetime.now() - last_daily).days < 1:
            bot.answer_callback_query(call.id, "You have already received your daily reward!")
        else:
            new_points = points + 2
            cursor.execute("UPDATE users SET points = %s, last_daily = %s WHERE user_id = %s",
                           (new_points, datetime.datetime.now(), user_id))
            conn.commit()
            bot.answer_callback_query(call.id, f"You've received 2 points! Total: {new_points} points")
            bot.edit_message_text(f"Welcome {username}!
Points: {new_points}", call.message.chat.id, call.message.message_id)

# Command to handle redeeming an IG account
@bot.callback_query_handler(func=lambda call: call.data == 'redeem_account')
def redeem_account(call):
    user_id = call.from_user.id
    user_data = get_user_data(user_id)

    if user_data:
        username, points, last_daily, ref_by = user_data
        if points >= 15:
            cursor.execute("SELECT account_info FROM accounts LIMIT 1")
            account = cursor.fetchone()
            if account:
                account_info = account[0]
                cursor.execute("DELETE FROM accounts WHERE account_info = %s", (account_info,))
                conn.commit()
                new_points = points - 15
                cursor.execute("UPDATE users SET points = %s WHERE user_id = %s", (new_points, user_id))
                conn.commit()
                bot.answer_callback_query(call.id, f"You've redeemed an IG account! Info: {account_info}")
                bot.edit_message_text(f"Welcome {username}!
Points: {new_points}", call.message.chat.id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "No accounts available right now. More will be added soon!")

# Start the bot
bot.infinity_polling()
