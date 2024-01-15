import regex as re
import datetime
import os
import openai
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
import time
from openai import OpenAI, AzureOpenAI


def get_llm_response(prompt):
    openai.api_base = os.environ["OPENAI_API_ENDPOINT"].strip()
    openai.api_type = os.environ["OPENAI_API_TYPE"].strip()
    openai.api_key = os.environ["OPENAI_API_KEY"].strip()
    openai.api_version = os.environ["OPENAI_API_VERSION"].strip()

    model_engine = "gpt-4-32k"

    client = AzureOpenAI(
        api_key=os.environ["OPENAI_API_KEY"].strip(),
        api_version=os.environ["OPENAI_API_VERSION"].strip(),
        azure_endpoint=os.environ["OPENAI_API_ENDPOINT"].strip(),
    )

    i = 1
    flag = False
    while not flag:
        try:
            response = client.chat.completions.create(
                model=model_engine,
                messages=prompt,
                temperature=0,
            )
            flag = True
        except Exception as e:
            print(e)
            flag = False
            time.sleep(i)
            if i <= 64:
                i = i * 2
            else:
                i = 1

    response_text = response.choices[0].message.content.strip()
    return response_text


def gsheet_api_check(SCOPES, local_path):
    creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = service_account.Credentials.from_service_account_file(
                os.path.join(local_path, "cron_jobs/credentials.json")
            )
    return creds


def delete_all_rows(SCOPES, spreadsheet_id, range_name, local_path):
    creds = gsheet_api_check(SCOPES, local_path)
    service = build("sheets", "v4", credentials=creds)

    # Clear the specified range (delete all rows)
    request = (
        service.spreadsheets()
        .values()
        .clear(spreadsheetId=spreadsheet_id, range=range_name, body={})
    )
    response = request.execute()
    print(f"All rows deleted from {range_name}.")


def add_rows(SCOPES, spreadsheet_id, range_name, df, local_path):
    values = df.values.tolist()
    column_names = df.columns.tolist()

    creds = gsheet_api_check(SCOPES, local_path)
    service = build("sheets", "v4", credentials=creds)

    body = {"values": [column_names]}
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="RAW",
        body=body,
        insertDataOption="INSERT_ROWS",
    ).execute()

    body = {"values": values}

    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body,
            insertDataOption="INSERT_ROWS",
        )
        .execute()
    )

    print(f"Added {result.get('updates').get('updatedCells')} cells.")


def append_rows(SCOPES, spreadsheet_id, range_name, df, local_path):
    values = df.values.tolist()

    creds = gsheet_api_check(SCOPES, local_path)
    service = build("sheets", "v4", credentials=creds)

    body = {"values": values}

    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body=body,
            insertDataOption="INSERT_ROWS",
        )
        .execute()
    )

    print(f"Appended {result.get('updates').get('updatedCells')} cells.")


def pull_sheet_data(SCOPES, SPREADSHEET_ID, DATA_TO_PULL, local_path):
    creds = gsheet_api_check(SCOPES, local_path)
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    result = (
        sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=DATA_TO_PULL).execute()
    )
    values = result.get("values", [])

    if not values:
        print("No data found.")
    else:
        rows = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=DATA_TO_PULL)
            .execute()
        )
        data = rows.get("values")
        print("COMPLETE: Data copied")
        return data


def remove_extra_voice_files(audio_file_path, out_path):
    if os.path.isfile(audio_file_path):
        os.remove(audio_file_path)
    if os.path.isfile(audio_file_path[:-3] + "wav"):
        os.remove(audio_file_path[:-3] + "wav")
    if os.path.isfile(out_path):
        os.remove(out_path)
    if os.path.isfile(out_path[:-3] + "wav"):
        os.remove(out_path[:-3] + "wav")


def strikethrough(text: str) -> str:
    """
    Strike off the text
    """
    result = ""
    for c in text:
        result = result + c + "\u0336"
    return result


def replace_special_character(text: str) -> str:
    """
    Replace special characters with the correct ones.
    Args:
    text (str): text to be cleaned
    Returns:
    str: cleaned text
    """
    corrections: dict(str, str) = {
        "ﬁ": "fi",
        "ﬀ": "ff",
        "ﬂ": "fl",
        "ﬃ": "ffi",
        "\uf075": "",
        "¼": "1/4",
    }
    return re.sub(r"ﬁ|ﬀ|ﬂ|ﬃ|\uf075|¼", lambda x: corrections[x.group()], text)


def clean_txt_from_pdf(text: str):
    # remove all '\n' that are not followed by a heading or a capital letter
    _text = re.sub(r"\n(^![A-Z•])", " ", text)
    # replace special characters
    _text = replace_special_character(_text)
    # remove all characters that are not alphanumeric or a linebreaker
    _text = re.sub(r"[^a-zA-Z0-9•\n]", " ", _text)
    # save the cleaned text
    return _text