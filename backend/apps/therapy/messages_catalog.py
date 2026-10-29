"""
SAFE TO EDIT: the WhatsApp reminder text for a therapy session (Additional settings -> "WhatsApp reminders").

- One text in English (en), Gujarati (gu) and Hindi (hi); the patient's language decides which one is used.
- Keep the words in {curly brackets} exactly as they are. They are filled in automatically:
  {name} patient's first name, {therapy} therapy name, {clinic} branch name,
  {date} e.g. 05-10-2026, {time} e.g. 10:15 AM, {phone} branch phone.
"""

REMINDER = {
    "en": "Reminder: Namaste {name}, your {therapy} session at {clinic} is on {date} at {time}. "
          "Please come on time and follow the instructions given to you. For changes call {phone}.",
    "gu": "યાદ અપાવવા: નમસ્તે {name}, {clinic} ખાતે તમારું {therapy} સેશન {date} ના રોજ {time} વાગ્યે છે. "
          "કૃપા કરીને સમયસર આવશો અને આપેલી સૂચનાઓ પાળશો. ફેરફાર માટે {phone} પર ફોન કરો.",
    "hi": "याद दिलाने के लिए: नमस्ते {name}, {clinic} में आपका {therapy} सत्र {date} को {time} बजे है। "
          "कृपया समय पर आएँ और दी गई सलाह का पालन करें। बदलाव के लिए {phone} पर कॉल करें।",
}
