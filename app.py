from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import random
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secure secret key for session handling

users_file = "users.json"  # A file to store the users and their passwords
dictionary_file = "english_to_bangla_dictionary.json"

# Load existing users from the file if it exists
if os.path.exists(users_file):
    with open(users_file, "r", encoding="utf-8") as f:
        users_data = json.load(f)
else:
    users_data = {}

# Load the dictionary
if os.path.exists(dictionary_file):
    with open(dictionary_file, "r", encoding="utf-8") as file:
        eng_to_bangla_dict = json.load(file)
else:
    eng_to_bangla_dict = []


# Helper function to save users' data to a file
def save_users_data():
    with open(users_file, "w", encoding="utf-8") as f:
        json.dump(users_data, f)


# Helper function to get a random word
def get_random_word(username):
    never_repeat_file = f"{username}_never_repeat.json"

    # Load the user's never_repeat list
    if os.path.exists(never_repeat_file):
        with open(never_repeat_file, "r", encoding="utf-8") as f:
            never_repeat = json.load(f)
    else:
        never_repeat = []

    # Filter out words that have been already attempted or marked as "never_repeat"
    available_words = [entry for entry in eng_to_bangla_dict if entry["en"] not in never_repeat]

    # If there are no available words, return None
    return random.choice(available_words) if available_words else None


@app.route('/')
def index():
    username = session.get('username', None)  # Get the username from the session
    return render_template('index.html', username=username)


@app.route('/create_user', methods=['POST'])
def create_user():
    username = request.form.get('username')  # Get the username from the form
    password = request.form.get('password')  # Get the password from the form

    if username and password:
        if username not in users_data:
            users_data[username] = password  # Store the username and password
            save_users_data()  # Save the updated users data to the file
            session['username'] = username  # Store the username in the session
            session['score'] = 0  # Initialize score to 0
            session['attempted'] = 0  # Initialize attempted count to 0
            session['asked_words'] = []  # Clear the list of asked words

            user_never_repeat_file = f"{username}_never_repeat.json"

            # Check if the user's never_repeat file exists
            if not os.path.exists(user_never_repeat_file):
                with open(user_never_repeat_file, "w", encoding="utf-8") as f:
                    json.dump([], f)  # Initialize with an empty list if it doesn't exist

            return redirect(url_for('quiz'))  # Redirect to the quiz page
        else:
            return render_template('index.html', error="Username already exists.")
    return render_template('index.html', error="Please provide a username and password.")


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')  # Get the username from the form
    password = request.form.get('password')  # Get the password from the form

    # Check if the username exists and if the password is correct
    if username in users_data and users_data[username] == password:
        session['username'] = username  # Store the username in the session
        session['score'] = 0  # Initialize score to 0
        session['attempted'] = 0  # Initialize attempted count to 0
        session['asked_words'] = []  # Clear the list of asked words
        return redirect(url_for('quiz'))  # Redirect to the quiz page
    else:
        return render_template('index.html', error="Invalid username or password")


@app.route('/quiz')
def quiz():
    username = session.get('username', None)
    if not username:
        return redirect(url_for('index'))  # If no user is logged in, redirect to index
    return render_template('quiz.html', username=username)


@app.route('/get_word/<username>')
def get_word(username):
    never_repeat_file = f"{username}_never_repeat.json"

    # Load the user's never_repeat list
    if os.path.exists(never_repeat_file):
        with open(never_repeat_file, "r", encoding="utf-8") as f:
            never_repeat = json.load(f)
    else:
        never_repeat = []

    # Initialize session variables if they do not exist
    if 'asked_words' not in session:
        session['asked_words'] = []  # Track words asked in the session

    # Get remaining words that have not been asked yet and are not in the never_repeat list
    remaining_words = [
        entry for entry in eng_to_bangla_dict
        if entry["en"] not in session['asked_words'] and entry["en"] not in never_repeat
    ]

    if remaining_words:
        word_entry = random.choice(remaining_words)  # Get a random word from remaining words
        session['asked_words'].append(word_entry["en"])  # Mark this word as asked in the session
        return jsonify({"word": word_entry["en"], "meaning": word_entry["bn"]})
    else:
        return jsonify({"error": "No more words available"})


@app.route('/answer', methods=['POST'])
def answer():
    data = request.get_json()
    word = data.get("word")
    correct = data.get("correct")
    action = data.get("action")
    username = data.get("username")

    # Load the user's never_repeat list
    never_repeat_file = f"{username}_never_repeat.json"
    if os.path.exists(never_repeat_file):
        with open(never_repeat_file, "r", encoding="utf-8") as f:
            never_repeat = json.load(f)
    else:
        never_repeat = []

    # Initialize score and attempted in session if not already set
    if 'score' not in session:
        session['score'] = 0
    if 'attempted' not in session:
        session['attempted'] = 0
    if 'asked_words' not in session:
        session['asked_words'] = []  # Track words that have been asked during the session

    # Increment the attempted count (for each unique word asked)
    if word not in session['asked_words']:
        session['asked_words'].append(word)
        session['attempted'] += 1

    # Update the score if the answer is correct
    if correct:
        session['score'] += 1

    # If the action is "never_repeat" and the word is not in the never_repeat list, add it
    if action == "never_repeat" and word not in never_repeat:
        never_repeat.append(word)

    # Save the updated never_repeat list
    with open(never_repeat_file, "w", encoding="utf-8") as f:
        json.dump(never_repeat, f)

    return jsonify({"score": session['score'], "attempted": session['attempted']})


@app.route('/finish')
def finish():
    username = session.get('username', None)
    total = session.get('attempted', 0)  # Get the total number of words attempted
    score = session.get('score', 0)  # Final score
    return jsonify({"score": score, "total": total})


@app.route('/restart_quiz', methods=['POST'])
def restart_quiz():
    username = request.json.get('username')  # Get the username from the frontend
    if username:
        # Reset the session variables related to the quiz
        session.pop('asked_words', None)  # Clear the list of asked words
        session['score'] = 0  # Reset score
        session['attempted'] = 0  # Reset attempted count
        return jsonify({"success": True})
    else:
        return jsonify({"success": False})


if __name__ == '__main__':
    app.run(debug=True)
