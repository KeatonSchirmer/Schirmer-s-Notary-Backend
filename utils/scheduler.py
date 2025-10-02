from apscheduler.schedulers.background import BackgroundScheduler
import requests
import os

def sync_google_events():
    API_BASE_URL = os.environ.get("EXPO_PUBLIC_API_URL")
    USER_ID = "1"
    headers = {
        "Content-Type": "application/json",
        "X-User-Id": USER_ID,
    }
    try:
        response = requests.post(API_BASE_URL, headers=headers)
        print(f"Google sync status: {response.status_code}")
    except Exception as e:
        print(f"Google sync error: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(sync_google_events, 'interval', minutes=10)
    scheduler.start()