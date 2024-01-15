import azure.functions as func
import datetime
import json
import logging
import os
import requests

app = func.FunctionApp()


@app.timer_trigger(
    schedule="0 */30 * * * *",
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False,
)
def main(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info("The timer is past due!")

    url = os.environ["ENDPOINT_URL"].strip()
    response = requests.post(url)
    print(response.status_code)
    logging.info(response.status_code)
