import openai
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Fetch the API key from environment variables
api_key = os.getenv('OPENAI_API_KEY')
admin_user_id = os.getenv('ADMIN_USER_ID')

# Check if the API key is fetched correctly
if not api_key:
    raise ValueError("API key not found. Ensure that the .env file contains the OPENAI_API_KEY variable.")

# Initialize OpenAI client
openai.api_key = api_key

# Function to read company information from a file
def read_company_info(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Path to the company information file
company_info_path = 'company_info.txt'

# Read company information
company_info = read_company_info(company_info_path)

# Dictionary to store conversation history for each user
conversation_history = {}

# Function to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    conversation_history[user_id] = []  # Initialize conversation history for the user
    await update.message.reply_text('Здравствуйте! Чем могу вам помочь?')

# Function to check if the response indicates a rude conversation or readiness for a call
def check_intent(response_text):
    rude_intents = ['rude', 'insult', 'offensive']
    call_intents = ['call me', 'ready to talk', 'schedule a call']

    if any(intent in response_text.lower() for intent in rude_intents):
        return 'rude'
    elif any(intent in response_text.lower() for intent in call_intents):
        return 'call'
    return None

# Function to send the conversation history to a specified user
async def send_conversation_to_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    conversation = conversation_history.get(user_id, [])
    conversation_text = '\n'.join([f"{msg['role']}: {msg['content']}" for msg in conversation])
    await context.bot.send_message(chat_id=admin_user_id, text=f"Conversation with user {user_id}:\n\n{conversation_text}")

# Function to handle messages and interact with ChatGPT
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user_id = update.message.from_user.id

    # Initialize conversation history if not present
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Add user message to conversation history
    conversation_history[user_id].append({"role": "user", "content": user_message})

    # Log the user's question
    print(f"User: {user_message}")

    # Show typing action while waiting for a response
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

    # Prepare the messages with context
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": company_info},
    ] + conversation_history[user_id]

    # Get response from GPT-4 Turbo
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=messages,
        max_tokens=1024,  # Increase max tokens to handle larger responses
    )

    response_text = response['choices'][0]['message']['content'].strip()

    # Add assistant message to conversation history
    conversation_history[user_id].append({"role": "assistant", "content": response_text})

    # Log ChatGPT's answer
    print(f"ChatGPT: {response_text}")

    # Send the response in parts if it's too long
    max_message_length = 4096  # Telegram message limit
    for i in range(0, len(response_text), max_message_length):
        await update.message.reply_text(response_text[i:i + max_message_length])

    # Check the intent of the response
    intent = check_intent(response_text)
    if intent in ['rude', 'call']:
        await send_conversation_to_admin(context, user_id)

# Function to handle errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f'Update {update} caused error {context.error}')

def main() -> None:
    # Replace 'YOUR_TOKEN_HERE' with your bot's token
    application = Application.builder().token('7140630049:AAEyzfBWT18-pOjJizsKMyvzDhNbhZhrt0E').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.add_error_handler(error)

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
