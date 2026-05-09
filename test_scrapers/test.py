import requests

r = requests.get("https://api.ipify.org")

print(r.text)