import os
import sys
from threading import Thread, Lock
import yaml
import logging
from azure.storage.queue import QueueClient
from azure.core.exceptions import ResourceExistsError
from datetime import datetime
import pytz
from croniter import croniter
import subprocess
import json
from flask import Flask, request
from time import sleep
import traceback

__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
sys.path.append("src")
from conversation_database import LoggingDatabase
from responder import WhatsappResponder
from medics_integration import OnboardMedics
from az_table import PatientTable
from utils import is_older_than_n_minutes

with open("config.yaml") as file:
    config = yaml.load(file, Loader=yaml.FullLoader)

print("Starting application")
app = Flask(__name__)
log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

logger = LoggingDatabase(config)
medics_onboard = OnboardMedics(config, logger)
print("Loading Databases done")

if config["CHAT_APPLICATION"] == "whatsapp":
    responder = WhatsappResponder(config)


pause_queue = False
queue_lock = Lock()

queue_name = os.environ["AZURE_QUEUE_NAME"].strip()
queue_client = QueueClient.from_connection_string(os.environ["AZURE_STORAGE_CONNECTION_STRING"].strip(), queue_name)

try:
    queue_client.create_queue()
except ResourceExistsError:
    pass

patient_table = PatientTable()


@app.route("/")
def index():
    print("Request for index page received")
    return "Flask is running!"

@app.route('/medics', methods=['POST'])
def medics():
    data = request.json
    for row in data:
        medics_onboard.onboard_medics_helper(row)
    return 'OK', 200

@app.route("/webhooks", methods=["POST"])
def webhook():
    body = request.json
    if (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    ):
        timestamp = body["entry"][0]["changes"][0]["value"]["messages"][0]["timestamp"]
        n = 2
        if is_older_than_n_minutes(int(timestamp), n=n):
            logger.add_log(
                sender_id="whatsapp_api",
                receiver_id="Bot",
                message_id=None,
                action_type="Old message",
                details={"message": f"Message older than {n} minutes"},
                timestamp=datetime.now(),
            )
            return "OK", 200
    # adding request to queue
    print("Adding message to queue, ", body)
    queue_client.send_message(json.dumps(body))
    return "OK", 200


@app.route("/scheduler", methods=["POST"])
def scheduler():
    logger.add_log(
        sender_id="Scheduler",
        receiver_id="Bot",
        message_id=None,
        action_type="Scheduler",
        details={"date": datetime.now()},
        timestamp=datetime.now(),
    )
    # stop the process queue
    global pause_queue, queue_lock
    queue_lock.acquire()
    pause_queue = True

    # Get the current time in IST
    now = datetime.now(pytz.timezone("Asia/Kolkata"))
    print("Current time: ", now)
    # Round the time to the nearest half hour
    minutes = (now.minute // 5) * 5
    rounded_now = now.replace(minute=minutes, second=0, microsecond=0)

    # Parse the cron schedules
    with open("cron.txt", "r") as f:
        lines = f.readlines()

    for line in lines:
        # Parse the cron schedule
        parts = line.strip().split()
        cron_expression = " ".join(parts[:5])
        command = " ".join(parts[5:])

        iter = croniter(cron_expression, now)
        prev_time = iter.get_prev(datetime)

        command = command.replace("$LOCAL_PATH", os.environ["APP_PATH"])
        print("Command: ", command)
        print("Previous execution time: ", prev_time)

        # Check if the job should run at the current time
        if (rounded_now - prev_time).total_seconds() < 60:
            print("Running command: ", command)
            subprocess.run(command, shell=True)
            if "kb_update" in command:
                responder.update_kb()

    # Start the process queue again
    pause_queue = False
    queue_lock.release()

    return "OK", 200


# Define a route for handling a POST request related to long-term processing
@app.route("/medics-sankara", methods=["POST"])
def long_term():
    data = request.json
    for row in data:
        #make all values string
        for key in row:
            row[key] = str(row[key])
        try:
            patient_table.insert_data(row)
        except Exception as e:
            print(e)
            traceback.print_exc()
    print("Medics sankara data received")
    return "OK", 200


# Define a route for handling webhooks
@app.route("/webhooks", methods=["GET"])
def verify_webhook():
    verify_token = os.environ.get("VERIFY_TOKEN").strip()
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("verify token is ", repr(verify_token), mode, repr(token), challenge)
    if mode and token:
        if mode == "subscribe" and token == verify_token:
            print("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            return "Forbidden", 403
    return "Not Found", 404


def process_queue():
    print("Starting queue processing")
    global pause_queue
    global config, logger
    # while the queue is non empty, retrieve the top massage and process it
    while True:
        queue_lock.acquire()
        if pause_queue:
            print("Pausing queue processing")
            sleep(0.01)
            continue
        try:
            messages = queue_client.receive_messages(messages_per_page=1, visibility_timeout=5)
            for message in messages:
                try:
                    if message.dequeue_count > 1:
                        logger.add_log(
                            event_name="app_error",
                            details={"message": message.content, "error": "Dequeue count exceeded"},
                        )
                        queue_client.delete_message(message)
                        continue
                    print("Message received", message.content)
                    body = json.loads(message.content)
                    print("Processing new message")
                    responder.response(body)
                    queue_client.delete_message(message)
                except Exception as e:
                    print(e)
                    traceback.print_exc()
                    print("Invalid message received: ", message.content)
                    queue_client.delete_message(message)
        except Exception as e:
            print(e)
            traceback.print_exc()
        queue_lock.release()
        sleep(0.1)


Thread(target=process_queue).start()

if __name__ == "__main__":
    if config["CHAT_APPLICATION"] == "whatsapp":
        app.run()
