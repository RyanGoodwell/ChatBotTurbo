from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import wikipedia
import logging
import random
from difflib import get_close_matches
from datetime import datetime

app = Flask(__name__)

# Initialize Flask-Limiter
limiter = Limiter(
    key_func=get_remote_address
)
limiter.init_app(app)

# Set Wikipedia language
wikipedia.set_lang("en")

# Logging
logging.basicConfig(filename='chat.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Last queries
last_queries = {}

# Basic responses
basic_responses = {
    "hello": [
        "Hello, nice to see you!",
        "Hey there! What's up?",
        "Greetings, human 👋"
    ],
    "how are you": [
        "Great! How about you?",
        "Super, thanks for asking!",
        "All good. How's your day going?"
    ],
    "bye": [
        "See you soon 👋",
        "Bye-bye!",
        "Don't forget to come back!"
    ],
    "who are you": [
        "I'm ChatBotTurbo.",
        "ChatBotTurbo at your service!",
        "I'm your personal Wikipedia guide 🤓"
    ],
    "what can you do": [
        "I can find interesting facts from Wikipedia and tell a few jokes!",
        "I can tell you what I know. Just ask!"
    ],
}

# Greeting phrases
greeting_keys = ["hello"]

# Determine basic response
def get_basic_response(text):
    normalized = text.strip().lower()
    closest = get_close_matches(normalized, basic_responses.keys(), n=1, cutoff=0.8)
    if closest:
        return closest[0], random.choice(basic_responses[closest[0]])
    return None, None

# KazPT mood
def get_mood():
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return "😴 A bit sleepy, but trying my best."
    elif 6 <= hour < 12:
        return "☀️ Good morning! Ready to answer."
    elif 12 <= hour < 18:
        return "🔋 Full of energy! Ask me anything."
    else:
        return "🌙 Evening is here, but I'm still around."

# "Live" flavor inserts
def random_flavor():
    phrases = [
        "🧠 That made me think...",
        "😅 Tricky question.",
        "🥙 I wouldn't mind a shawarma right now... but first, the answer:",
        None, None, None
    ]
    return random.choice(phrases)

# Logging
def log_interaction(user_input, bot_response):
    logging.info(f"User: {user_input} | Bot: {bot_response}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
@limiter.limit("10 per minute")
def search():
    user_input = request.json.get('query', '').strip()
    user_ip = get_remote_address()

    if not user_input:
        return jsonify({'response': "Please enter a question."})

    if last_queries.get(user_ip) == user_input:
        return jsonify({'response': "You've already asked this 😅. Maybe try something new?"})
    last_queries[user_ip] = user_input

    # Handle basic phrases
    matched_key, basic = get_basic_response(user_input)
    if basic:
        parts = []

        # mood only for greetings
        if matched_key in greeting_keys:
            parts.append(get_mood())

        flavor = random_flavor()
        if flavor:
            parts.append(flavor)

        parts.append(basic)
        response = "<br>".join(parts)

        log_interaction(user_input, response)
        return jsonify({'response': response})

    # Wikipedia search
    try:
        results = wikipedia.search(user_input)
        if results:
            page = wikipedia.page(results[0])
            summary = wikipedia.summary(page.title, sentences=3)
            mood = get_mood()
            flavor = random_flavor()
            parts = [mood]
            if flavor:
                parts.append(flavor)
            parts.append(f"<strong>{page.title}</strong><br>{summary}<br><a href='{page.url}' target='_blank'>Read more</a>")
            response = "<br>".join(parts)
            log_interaction(user_input, response)
            return jsonify({'response': response})
        else:
            wikipedia.set_lang("ru")
            results = wikipedia.search(user_input)
            if results:
                page = wikipedia.page(results[0])
                summary = wikipedia.summary(page.title, sentences=3)
                response = f"(🔁 Russian) <strong>{page.title}</strong><br>{summary}<br><a href='{page.url}' target='_blank'>Читать больше</a>"
                wikipedia.set_lang("en")
                log_interaction(user_input, response)
                return jsonify({'response': response})
            wikipedia.set_lang("en")
            return jsonify({'response': "I couldn't find anything for this query."})
    except wikipedia.exceptions.DisambiguationError:
        return jsonify({'response': "The query is too ambiguous. Please clarify."})
    except wikipedia.exceptions.PageError:
        return jsonify({'response': "There is no such page on Wikipedia."})
    except Exception as e:
        return jsonify({'response': f"Something went wrong: {str(e)}"})

if __name__ == '__main__':
    app.run(debug=True)
