"""
SAFE TO EDIT: the SMS / WhatsApp text sent to patients about appointments.

- One text per event, in English (en), Gujarati (gu) and Hindi (hi).
  The patient's language (from their registration) decides which one is used.
- Keep the words in {curly brackets} exactly as they are. They are filled in automatically:
  {name} patient's first name, {doctor} doctor's name, {clinic} branch name,
  {date} e.g. 05-10-2026, {time} e.g. 10:15 AM, {token} token number, {phone} branch phone.
"""

MESSAGES = {
    "booked": {
        "en": "Namaste {name}, your appointment with {doctor} at {clinic} is on {date} at {time}. "
              "Please come 10 minutes early. For changes call {phone}.",
        "gu": "નમસ્તે {name}, {clinic} ખાતે {doctor} સાથે તમારી એપોઇન્ટમેન્ટ {date} ના રોજ {time} વાગ્યે છે. "
              "કૃપા કરીને 10 મિનિટ વહેલા આવશો. ફેરફાર માટે {phone} પર ફોન કરો.",
        "hi": "नमस्ते {name}, {clinic} में {doctor} के साथ आपका अपॉइंटमेंट {date} को {time} बजे है। "
              "कृपया 10 मिनट पहले आएँ। बदलाव के लिए {phone} पर कॉल करें।",
    },
    "rescheduled": {
        "en": "Namaste {name}, your appointment with {doctor} at {clinic} has been moved to {date} at {time}.",
        "gu": "નમસ્તે {name}, {clinic} ખાતે {doctor} સાથેની તમારી એપોઇન્ટમેન્ટ હવે {date} ના રોજ {time} વાગ્યે છે.",
        "hi": "नमस्ते {name}, {clinic} में {doctor} के साथ आपका अपॉइंटमेंट अब {date} को {time} बजे है।",
    },
    "cancelled": {
        "en": "Namaste {name}, your appointment with {doctor} at {clinic} on {date} has been cancelled. "
              "To book again call {phone}.",
        "gu": "નમસ્તે {name}, {clinic} ખાતે {doctor} સાથેની {date} ની તમારી એપોઇન્ટમેન્ટ રદ કરવામાં આવી છે. "
              "ફરી બુક કરવા {phone} પર ફોન કરો.",
        "hi": "नमस्ते {name}, {clinic} में {doctor} के साथ {date} का आपका अपॉइंटमेंट रद्द कर दिया गया है। "
              "फिर से बुक करने के लिए {phone} पर कॉल करें।",
    },
    "token": {
        "en": "Namaste {name}, your token number at {clinic} is {token} for {doctor}. Please wait to be called.",
        "gu": "નમસ્તે {name}, {clinic} ખાતે {doctor} માટે તમારો ટોકન નંબર {token} છે. કૃપા કરીને તમારા વારાની રાહ જુઓ.",
        "hi": "नमस्ते {name}, {clinic} में {doctor} के लिए आपका टोकन नंबर {token} है। कृपया अपनी बारी की प्रतीक्षा करें।",
    },
}
