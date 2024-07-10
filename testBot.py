import openai
from telegram import Update, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import json
import re
import time

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
        print(f"JSONDecodeError: {e}")
        print(f"Response text: {response_text}")
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
        except openai.error.RateLimitError as e:
            wait_time = int(e.headers.get("Retry-After", 5))
            print(f"Rate limit reached. Waiting for {wait_time} seconds before retrying...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    print("Max retries reached. Please try again later.")
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
    conversation_history[user_id].append({"role": "user"
