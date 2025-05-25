import sys
import threading
from pyngrok import ngrok
import os

from app import app
NGROK_AUTH_TOKEN = "2jYaDeuLGtIQekL0UT0YiRzE54l_2tWD828DkdMbMtn8FN6XP"
ngrok.set_auth_token(NGROK_AUTH_TOKEN)
threading.Thread(target=app.run, kwargs={"debug": False, "use_reloader": False}).start()
public_url = ngrok.connect(5000)
print(f"🔗 URL publique : {public_url}")