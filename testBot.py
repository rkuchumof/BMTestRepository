import openai
from openai.error import APIConnectionError, RateLimitError, APIError
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import json
import re
import time
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Fetch the API key and admin user ID from environment variables
api_key = os.getenv('OPENAI_API_KEY')
admin_user_id = int(os.getenv('ADMIN_USER_ID'))
tg_token = os.getenv('TELEGRAM_TOKEN')

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

def clean_json_string(json_string):
    # Define a regular expression pattern to match invalid control characters
    control_chars = re.compile(r'[\x00-\x1f\x7f]|(\*\*)')  # Match control characters in the range \x00-\x1f and \x7f
    cleaned_string = control_chars.sub('', json_string)
    cleaned_text = cleaned_string.strip('```json').strip('```')
    return cleaned_text

# Function to extract intent from ChatGPT's response
def extract_intent(response_text):
    try:
        # Clean up the response text
        cleaned_text = clean_json_string(response_text)
        # Attempt to parse the response as JSON
        response_json = json.loads(cleaned_text)
        if 'intent' in response_json and 'response' in response_json:
            return response_json['intent'], response_json['response']
    except json.JSONDecodeError as e:
        logger.error(f"JSONDecodeError: {e}")
        logger.error(f"Response text: {response_text}")
        pass
    return 'Unclear Yet', response_text

def call_gpt_with_retries(messages, max_tokens=256, temperature=0.8, retries=10):
    for attempt in range(retries):
        try:
            # Get response from GPT-4
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response
        except RateLimitError as e:
            wait_time = int(e.headers.get("Retry-After", 5))
            logger.warning(f"Rate limit reached. Waiting for {wait_time} seconds before retrying...")
            time.sleep(wait_time)
        except APIConnectionError as e:
            logger.error(f"Connection error: {e}")
            time.sleep(5)  # Wait a bit before retrying
        except APIError as e:
            logger.error(f"API error: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            return None
    logger.error("Max retries reached. Please try again later.")
    return None

# Function to handle messages and interact with ChatGPT
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    user_id = update.message.from_user.id
    user_nickname = update.message.from_user.username

    # Initialize conversation history if not present
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    # Add user message to conversation history
    conversation_history[user_id].append({"role": "user", "content": user_message})

    # Log the user's question
    logger.info(f"User: {user_message}")

    # Show typing action while waiting for a response
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

    # Prepare the messages with context
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": company_info},
    ] + conversation_history[user_id] + [
        {"role": "user", "content": f"""Please respond to the following query and return a JSON object with two attributes: 'intent' and 'response'.
        The 'intent' should be either 'Rude', 'Unclear Yet', 'Job Seeker', 'Spammer', 'Potential Partner Who Left Contact Details for Communication' or 'Potential Client Who Left Contact Details for Communication'.\nQuery: {user_message}"""}
    ]

    response = call_gpt_with_retries(messages)

    if response is not None:
        response_text = response['choices'][0]['message']['content'].strip()

        # Extract the intent and the response text from ChatGPT's response
        intent, clean_response_text = extract_intent(response_text)

        # Add assistant message to conversation history
        conversation_history[user_id].append({"role": "assistant", "content": clean_response_text})

        # Log ChatGPT's answer and intent
        logger.info(f"ChatGPT response: {clean_response_text}")
        logger.info(f"Intent detected: {intent}")

        # Send the response in parts if it's too long
        max_message_length = 4096  # Telegram message limit
        for i in range(0, len(clean_response_text), max_message_length):
            await update.message.reply_text(clean_response_text[i:i + max_message_length])

        # Trigger actions based on the detected intent
        if intent in ['Potential Partner Who Left Contact Details for Communication', 'Potential Client Who Left Contact Details for Communication']:
            await send_conversation_to_admin(context, user_id, user_nickname, intent)
    else:
        await update.message.reply_text("Sorry, an error occurred while processing your request. Please try again later.")

# Function to send the conversation history to a specified user
async def send_conversation_to_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int, user_nickname: str, intent: str) -> None:
    conversation = conversation_history.get(user_id, [])
    conversation_text = '\n'.join([f"{msg['role']}: {msg['content']}" for msg in conversation])
    await context.bot.send_message(chat_id=admin_user_id, text=f"Conversation with @{user_nickname} ({intent}):\n\n{conversation_text}")
    logger.info(f"Triggered '{intent}' event. Sent conversation with user {user_id} (@{user_nickname}) to admin.")

# Function to handle errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f'Update {update} caused error {context.error}')

def main() -> None:
    application = Application.builder().token(tg_token).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.add_error_handler(error)

    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
