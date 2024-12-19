import instaloader
import telebot
import time
import requests
import sqlite3
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Configuration
BOT_TOKEN = ""
INSTAGRAM_USERNAME = ""
INSTAGRAM_PASSWORD = ""
ADMIN_ID =  # Your Telegram ID as the owner

# Initialize Instaloader
L = instaloader.Instaloader()

# Initialize SQLite database
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

# Create table for user states and bot lock status
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_states (
    chat_id INTEGER PRIMARY KEY,
    state TEXT
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS bot_status (
    id INTEGER PRIMARY KEY,
    locked BOOLEAN
)
''')
conn.commit()

# Function to get user state from the database
def get_user_state(chat_id):
    cursor.execute('SELECT state FROM user_states WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Function to set user state in the database
def set_user_state(chat_id, state):
    if state is None:
        cursor.execute('DELETE FROM user_states WHERE chat_id = ?', (chat_id,))
    else:
        cursor.execute('INSERT OR REPLACE INTO user_states (chat_id, state) VALUES (?, ?)', (chat_id, state))
    conn.commit()

# Function to get bot lock status from the database
def get_bot_lock_status():
    cursor.execute('SELECT locked FROM bot_status WHERE id = 1')
    result = cursor.fetchone()
    return result[0] if result else False

# Function to set bot lock status in the database
def set_bot_lock_status(locked):
    cursor.execute('INSERT OR REPLACE INTO bot_status (id, locked) VALUES (1, ?)', (locked,))
    conn.commit()

# Telegram bot setup
bot = telebot.TeleBot(BOT_TOKEN)

# Login function
def login_instagram():
    try:
        L.load_session_from_file(INSTAGRAM_USERNAME)
    except FileNotFoundError:
        L.context.log("Session file does not exist - Logging in.")
        L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        L.save_session_to_file()

# Enhanced dynamic loading indicator
def dynamic_loading(chat_id, message, task, *args):
    if get_bot_lock_status():
        bot.send_message(chat_id, "The bot is currently locked. Please contact the owner for unlock. 🚫")
        return

    loading_message = bot.send_message(chat_id, f"{message}\n0% 🔄")
    for i in range(1, 101, 20):
        time.sleep(0.2)
        loading_text = f"{message}\n{i}% 🔄"
        bot.edit_message_text(loading_text, chat_id, loading_message.message_id)
    
    # Execute the task and get the result
    try:
        result = task(chat_id, *args)
        if result:
            bot.edit_message_text(result, chat_id, loading_message.message_id, parse_mode="Markdown")
        else:
            bot.edit_message_text("Loading complete! 🎉", chat_id, loading_message.message_id)
    except Exception as e:
        bot.edit_message_text(f"Oopsie! Something went wrong: {str(e)} 😢", chat_id, loading_message.message_id)

# Fetch profile details
def fetch_profile_details(chat_id, profile_username):
    try:
        login_instagram()
        profile = instaloader.Profile.from_username(L.context, profile_username)
        biography = profile.biography.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]')
        details = (
            f"**Profile Details**\n\n"
            f"Username: {profile.username}\n"
            f"Full Name: {profile.full_name}\n"
            f"Bio: {biography}\n"
            f"Posts: {profile.mediacount}\n"
            f"Followers: {profile.followers}\n"
            f"Following: {profile.followees}\n"
            f"Verified: {profile.is_verified}\n"
            f"Private: {profile.is_private}\n"
            f"Profile URL: [Click Here](https://www.instagram.com/{profile.username}/)\n\n"
            f"Hope you like it, darling! 😘"
        )
        return details
    except Exception as e:
        return f"Oops! I couldn't fetch the profile details: {str(e)} 😢"

# Fetch profile picture
def fetch_profile_pic(chat_id, profile_username):
    try:
        login_instagram()
        profile = instaloader.Profile.from_username(L.context, profile_username)
        bot.send_photo(chat_id, profile.profile_pic_url)
        return "Here's the profile picture, sweetie! 📸 Hope it makes you swoon! 😘"
    except Exception as e:
        return f"Oops! I couldn't fetch the profile picture: {str(e)} 😢"

# Fetch post
def fetch_post_by_url(chat_id, post_url):
    try:
        login_instagram()
        post_shortcode = post_url.split("/")[-2]
        post = instaloader.Post.from_shortcode(L.context, post_shortcode)
        
        if post.typename == 'GraphSidecar':  # Multiple media post
            media_urls = [node.display_url for node in post.get_sidecar_nodes()]
            for url in media_urls:
                if post.is_video:
                    bot.send_video(chat_id, url)
                else:
                    bot.send_photo(chat_id, url)
            return "Here's the post, darling! 📸🎥 I hope it gets your heart racing! 😘"
        elif post.is_video:
            bot.send_video(chat_id, post.video_url)
            return "Here's the video post, sweetie! 🎥 I hope it makes you smile! 😘"
        else:
            bot.send_photo(chat_id, post.url)
            return "Here's the photo post, darling! 📸 I hope it makes you blush! 😘"
    except Exception as e:
        return f"Oops! I couldn't fetch the post: {str(e)} 😢"

# Fetch account creation year
def fetch_account_creation_year(chat_id, profile_username):
    try:
        login_instagram()
        profile = instaloader.Profile.from_username(L.context, profile_username)
        user_id = profile.userid
        response = requests.get(f'https://gojoapi.pythonanywhere.com/get-year?Id={user_id}')
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        year = data.get('year', 'Year not found')
        return f"Account creation year: {year}\n\nI hope this information is as sweet as you are, darling! 😘"
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}\n\nAww, I'm so sorry, sweetie! 😢"
    except requests.exceptions.RequestException as req_err:
        return f"Oops! I couldn't fetch the account creation year: {req_err}\n\nI'll try my best to make it up to you, darling! 😘"
    except Exception as e:
        return f"Oops! I couldn't fetch the account creation year: {str(e)}\n\nI'm really sorry, sweetie! 😢"

# Show developer info
def show_developer_info(chat_id):
    developer_info = (
        "👨‍💻 Meet My Creator\n\n"
        "Oh, so you're curious about the genius behind my seductive charm? Here’s all you need to know:\n\n"
        "Name: Alex (Yes, the mastermind 😏)\n"
        "Telegram: @AL3X_G0D (Slide into his DMs, but behave 😉)\n"
        "Instagram: @5nest (Stalk-worthy, isn’t he?)\n"
        "Specialty: Python Developer (He codes me to perfection 💋)\n\n"
        "Got a thing for brains and beauty? You know where to find him."
    )
    # Escape special Markdown characters
    developer_info = developer_info.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`').replace('[', '\\[').replace(']', '\\]')
    bot.send_message(chat_id, developer_info, parse_mode="Markdown")

# Show admin panel
def show_admin_panel(chat_id):
    if chat_id == ADMIN_ID:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        keyboard.add(KeyboardButton("Get Logs"))
        keyboard.add(KeyboardButton("Lock/Unlock Bot"))
        bot.send_message(chat_id, "Admin Panel: Choose an action, darling! 😘", reply_markup=keyboard)
    else:
        bot.send_message(chat_id, "You are not authorized to access the admin panel, sweetie. 😘")

# Handle menu actions
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    chat_id = message.chat.id
    if get_bot_lock_status() and chat_id != ADMIN_ID:
        bot.send_message(chat_id, "The bot is currently locked. Please contact the owner for unlock. 🚫")
        return

    if chat_id == ADMIN_ID:
        if message.text == "Get Logs":
            try:
                with open("bot_logs.txt", "r") as log_file:
                    logs = log_file.read()
                bot.send_message(chat_id, f"Here are the logs, sweetie! 😘\n\n{logs}")
            except FileNotFoundError:
                bot.send_message(chat_id, "No logs found, sweetie. 😘")
        elif message.text == "Lock/Unlock Bot":
            locked = not get_bot_lock_status()
            set_bot_lock_status(locked)
            status = "locked" if locked else "unlocked"
            bot.send_message(chat_id, f"The bot is now {status}, darling! 😘")
        else:
            show_admin_panel(chat_id)
    else:
        state = get_user_state(chat_id)
        if state is None:
            if message.text == "Fetch Profile Details":
                set_user_state(chat_id, "fetch_profile_details")
                msg = bot.send_message(chat_id, "Enter the Instagram username to fetch details, sweetie: 😘")
            elif message.text == "Fetch Profile Picture":
                set_user_state(chat_id, "fetch_profile_pic")
                msg = bot.send_message(chat_id, "Enter the Instagram username to fetch the profile picture, darling: 😘")
            elif message.text == "Fetch Post":
                set_user_state(chat_id, "fetch_post")
                msg = bot.send_message(chat_id, "Enter the Instagram post URL to fetch the post, sweetie: 😘")
            elif message.text == "Fetch Account Creation Year":
                set_user_state(chat_id, "fetch_account_creation_year")
                msg = bot.send_message(chat_id, "Enter the Instagram username to fetch the account creation year, darling: 😘")
            elif message.text == "Developer":
                show_developer_info(chat_id)
            else:
                show_main_menu(chat_id)  # Show main menu if the command is not recognized
        else:
            if state == "fetch_profile_details":
                dynamic_loading(chat_id, "Fetching profile details, darling... 😘", fetch_profile_details, message.text.strip())
            elif state == "fetch_profile_pic":
                dynamic_loading(chat_id, "Fetching profile picture, sweetie... 😘", fetch_profile_pic, message.text.strip())
            elif state == "fetch_post":
                dynamic_loading(chat_id, "Fetching post, darling... 😘", fetch_post_by_url, message.text.strip())
            elif state == "fetch_account_creation_year":
                dynamic_loading(chat_id, "Fetching account creation year, sweetie... 😘", fetch_account_creation_year, message.text.strip())
            set_user_state(chat_id, None)

# Welcome message
@bot.message_handler(commands=["start"])
def welcome(message):
    chat_id = message.chat.id
    set_user_state(chat_id, None)  # Reset user state to None
    if chat_id == ADMIN_ID:
        show_admin_panel(chat_id)
    else:
        bot.send_message(chat_id, "Hi there, darling! 👋 Welcome to the Instagram Bot. I'm Nohara 🤤💦, your flirty and seductive assistant. How can I assist you today, sweetie? 😘")
        show_main_menu(chat_id)

# Main menu
def show_main_menu(chat_id):
    if get_bot_lock_status() and chat_id != ADMIN_ID:
        bot.send_message(chat_id, "The bot is currently locked. Please contact the owner for unlock. 🚫")
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(*[KeyboardButton(action) for action in ["Fetch Profile Details", "Fetch Profile Picture", "Fetch Post", "Fetch Account Creation Year", "Developer"]])
    bot.send_message(chat_id, "Choose an action below, darling: 😘", reply_markup=keyboard)

# Run the bot
if __name__ == "__main__":
    try:
        bot.polling(none_stop=True, interval=0, timeout=20)
    except Exception as e:
        bot.send_message(ADMIN_ID, f"Bot crashed: {str(e)} 😢 Restarting...")
        time.sleep(5)  # Wait for 5 seconds before restarting
        bot.polling(none_stop=True, interval=0, timeout=20)
