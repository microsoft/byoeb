# How to use BYOeB for building a teacher-student chatbot

This tutorial will guide you on how to build an expert-in-the-loop WhatsApp-based question answering chatbot using the BYOeB platform.

In this tutorial, you will build a chatbot to enable students to ask questions related to grade-8 science and provide responses from the NCERT (India) textbook. The teacher (as experts) need to verify the responses. Any corrections made by the teacher will be used to update the bot's knowledge base, thus ensuring that the chatbot learns from the teacher's input and improves its responses over time.

## Setup

1. Set up the repository. Follow the commands provided in `README.md` file (`Local installation`) to ensure you have all the necessary credentials, dependencies, and configurations.

2. Choose your bot's name. In this tutorial, lets call it 'science_bot' (use it for the project name and folder name, for consistency).

## Building science_bot

- **Step 1**: Insert keys and credentials in the `keys.env` file.

- **Step 2**: Change Azure DB and Cosmos DB parameters in `config.yaml` file. You have to create a mongo database in Cosmos DB with the name `science_bot` and a container in your Azure storage account with the name `science-bot-audio-storage`. 
    
    ```
    COSMOS_DB_NAME: science_bot
    COSMOS_DB_COLLECTION: conversation_science_bot
    COSMOS_LONGTERM_COLLECTION: science_bot_users
    COSMOS_LOGGING_COLLECTION: logs_science_bot
    AZURE_BLOB_CONTAINER_NAME: science-bot-audio-storage
    ```

    LONGTERM_COLLECTION is used to store user data (user_id, whatsapp_id, language), COSMOS_DB_COLLECTION is used to store conversational data (query, response, etc) and COSMOS_LOGGING_COLLECTION contains all logs from the bot. BYOeB system uses AZURE_BLOB_CONTAINER to store all incoming audio queries.

- **Step 3**: Update `config.yaml` file with details relevant to science_bot (with student as User, teacher as the expert, and domain of the teacher is academic):

    Note: You can define multiple experts, e.g., 'teacher' to answer 'academic' questions, while 'coordinator' to answer 'administrative' questions. In that case, the chatbot will classify the question raised by the student into 'academic' or 'administrative', and accordingly ask the respective expert for verification.
    
    ```
    PROJECT_NAME: science_bot
    USERS : ['Student']
    EXPERTS:
      Teacher: 'Academic'
    USER_PROMPT : 'You are a science bot. Your purpose is to help students with any queries that they might have.'
    ```

    **Query escalation**: If the expert (teacher here) does not verify the response within a pre-defined period (e.g, it is set to 3 hours in `cron_jobs/escalate.py`), the verification can be escalated to a senior teacher here. Below, provide details of ESCALATION expert as well.

    ```
    ESCALATION:
      Teacher: 
        name: 'Senior Teacher'
        whatsapp_id: '919876543210'
    ```

- **Step 4**: Now you need to add users (students here) and experts (teachers here) to this chatbot. Each user should be linked to one expert. E.g., there could be three grade-8 science teachers in a school (as experts) for a total of 200 grade-8 students (users). 

    You need to add users (with linked experts) to a Mongo database (with credentials defined as `COSMOS_DB_CONNECTION_STRING` in `keys.env`), with table name defined in  `COSMOS_LONGTERM_COLLECTION` variable (defined above in Step 2).

    The required fields to add `Student` (as users) with linked `Teacher` (as experts): `user_id, Student_whatsapp_id, Student_language, Teacher_name, Teacher_whatsapp_id`. Note: `user_id` should be unique.

    To onboard a student, you can execute the python code after filling the required fields in `processing/add_user.py`:

    ```console
    > python3 processing/add_user.py
    ```

    **Note**: Add international phone number codes in Student_whatsapp_id and Teacher_whatsapp_id (e.g., add '91' before the phone number '9876543210' for India).

    Additional fields can be added, such as Student_name, Student_class.
    
    After onboarding, either the chatbot can send a template welcome message to the user (using the `/long_term` API endpoint defined in `app.py`), or the user can start interacting with the bot. Learn more about defining template messages in WhatsApp [here](https://www.facebook.com/business/help/2055875911147364?id=2129163877102343).

- **Step 5**: Whenever an expert (such as a teacher) provides a correction to the bot, it gets recorded. To push these corrections to the knowledge base (KB), the recommended approach is to get it approved by a Knowledge Base (KB) Update Admin (e.g., a principal) at the end of each day. For that, the BYOeB system provides a way to aggregate all the expert corrections and share them with the KB Update Admin over Google Sheet. In this sheet, the Admin needs to indicate 'Yes' or 'No' against each correction to specify whether that correction should be used to update the KB or not. By default, every day at 8pm, an email gets automatically sent to the KB Update Admin (part of the `EMAIL_LIST` below) with the link of the Google Sheet. Moreover, every day at 3am, based on the KB Admin's responses, the KB gets updated.
    
    To use google sheets API, you will need to download `credentials.json` from [here](https://developers.google.com/sheets/api/quickstart/python#step_3_set_up_the_sample), and then save it in the `cron_jobs` folder . 
    
    Fill the following details in `config.yaml`:

    ```
    SPREADSHEET_ID: <spreadhsheetID>
    SHEET_LINK: <spreadsheetURL>
    # sender details
    EMAIL_ID: <sender-emailID>
    EMAIL_PASS: <sender-emailID-password>
    # receiver list
    EMAIL_LIST: ["teacher@school.com", "principal@school.com"] 
    ```

    Note: To send an automated email, you need to provide a sender email id with password in the `config.yaml` file (as shown above).

- **Step 6**: Create a folder named `science_bot` in the `data` folder. 

- **Step 7**: If the knowledge base files are in pdf format (e.g., [Link to the 8th-grade science textbook](https://ncert.nic.in/textbook.php?hesc1=0-13)), create a folder named `raw_documents_pdf` inside the `science_bot` folder, and copy all the pdf files to the `raw_documents_pdf` folder. 
    
    Use the following command to convert these files to txt documents.
    ```console
    > python3 processing/convert_pdf_to_txt.py
    ```

    If the knowledge base files are in txt format, create a folder named `raw_documents` inside the `science_bot` folder, and copy all the txt knowledge base files to the `raw_documents` folder.

- **Step 8**: Use the following commands to create LLM prompts from the given `USER_PROMPT` in `config.yaml`, and create a Chroma vector DB to store our custom KB.

    ```console
    > python3 processing/create_llm_prompts.py
    > python3 processing/create_embeddings.py
    ```

- **Step 9**: When a student gets onboarded, she/he receive a set of welcome messages along with a few questions as suggestions to get them started with using the `science_bot`. In the `config.yaml` file, please add the introductory message, along with these initial suggested questions, as below:

    ```
    WELCOME_MESSAGES:
      USERS:
        - 'Hi! I am a science bot. I can help you with any queries that you have regarding your science curriculum.'
      EXPERTS:
        - 'Hi! I am a science bot. Thank you for volunteering to help students with their science queries.'

    INITIAL_SUGGESTION_QUESTIONS:
      - 'What topics can you help me with?'
      - 'What is photosynthesis?'
      - 'What is the difference between a plant cell and an animal cell?'
    ```

    Now, to translate these messages and questions to multiple languages (like "hi" for Hindi, "kn" for Kannada, "ta" for Tamil, "te" for Telugu) and generate audio messages accordingly, use the following commands:
    ```console
    > python3 processing/translate_introductions.py
    > python3 processing/translate_language_prompt.py
    > python3 processing/translate_suggestion_questions.py
    > python3 processing/generate_audio_onboarding.py
    ```

    Note: Feel free to change the language list in the above four files to support different languages.

- **Step 10**: Run the Flask app and connect it with WhatsApp webhook API to start interacting with the bot.

    ```console
    > source keys.env
    > flask run
    ```

- **Step 11** (optional): The system use CronJobs for (a) sceduling escalation to ESCALATION expert (here senior teacher), and (b) updating KB (both send email to KB Update Admin at 8pm and deploy KB at 3am).

    You can schedule these CronJobs, or even define new ones, that may be relevant for your project in `/cron.txt` file. Learn more about CronJob [here](https://www.hostinger.in/tutorials/cron-job).
