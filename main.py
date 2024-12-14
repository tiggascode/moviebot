import random
from telebot import types
import telebot
import requests
import schedule
import time
import threading
import sqlite3

# Telegram bot token
BOT_TOKEN = '8124228245:AAGUY4fdsc85AP6B4xxG6kJpBJtVgU4mCbA'
# TMDB API key
TMDB_API_KEY = '3bccfdc623e1638bf1f482f15b920b0a'

bot = telebot.TeleBot(BOT_TOKEN)

# Create a connection to the SQLite database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Create a table to store user data
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users
    (id INTEGER PRIMARY KEY, username TEXT, name Text, chat_id INTEGER, recommend_count INTEGER DEFAULT 0)
''')

def add_user(username, name, chat_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,))
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO users (username, name, chat_id) VALUES (?, ?, ?)', (username, name, chat_id,))
        conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.InlineKeyboardMarkup()
    recommend_button = types.InlineKeyboardButton(text='Recommend', callback_data='recommend')
    markup.add(recommend_button)
    bot.send_message(message.chat.id, "Welcome to MovieBot! Use /recommend to find your next favorite movie!", reply_markup=markup)
    add_user(message.from_user.username, message.from_user.first_name, message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == 'recommend')
def recommend_callback(call):
    bot.delete_message(call.message.chat.id, call.message.id)
    recommend_movie(call.message)

def recommend_movie(message):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE chat_id = ?', (message.chat.id,))
    user = cursor.fetchone()
    if user is None:
        cursor.execute('INSERT INTO users (chat_id, recommend_count) VALUES (?, 0)', (message.chat.id,))
    else:
        cursor.execute('UPDATE users SET recommend_count = recommend_count + 1 WHERE chat_id = ?', (message.chat.id,))
    conn.commit()
    conn.close()
    response = requests.get(f'https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}')
    if response.status_code == 200:
        movies = response.json()['results']
        random_index = random.randint(0, len(movies) - 1)
        random_movie = movies[random_index]
        title = random_movie['title']
        overview = random_movie['overview']
        rating = random_movie['vote_average']
        poster_path = random_movie['poster_path']
        poster_url = f'https://image.tmdb.org/t/p/w500{poster_path}'
        markup = types.InlineKeyboardMarkup()
        recommend_again_button = types.InlineKeyboardButton(text='Recommend Again', callback_data='recommend_again')
        markup.add(recommend_again_button)
        bot.send_photo(message.chat.id, poster_url, caption=f"{title}\n Rating: {rating}/10\n {overview}\nWould you like another recommendation?", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Sorry, couldn't fetch a movie at the moment.")

@bot.callback_query_handler(func=lambda call: call.data == 'recommend_again')
def recommend_again_callback(call):
    markup = types.InlineKeyboardMarkup()
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=markup)
    recommend_movie(call.message)

@bot.message_handler(commands=['recommend'])
def recommend_command(message):
    recommend_movie(message)

def get_users_from_db():
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users")
        users = cursor.fetchall()
        conn.close()
        return [user[0] for user in users]
    except Exception as e:
        print(f"Database error: {e}")
        return []

# Send messages to all users
def send_message_to_users():
    users = get_users_from_db()
    if users:
        for user_id in users:
            try:
                bot.send_message(user_id, "Its time to watch movie ")
                print(f"Message sent to {user_id}")
            except Exception as e:
                print(f"Error sending message to {user_id}: {e}")
    else:
        print("No users found to send messages.")

# Schedule the messages
def schedule_messages():
    schedule.every().day.at("16:37").do(send_message_to_users)

    while True:
        schedule.run_pending()
        time.sleep(1)

        # Start the bot

def start_bot_polling():
    bot.polling(none_stop=True)
if __name__ == "__main__":
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=schedule_messages)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    # Start the bot polling
    start_bot_polling()