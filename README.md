# Email_Assistance_LLM

This project is a POC for an AI assistant that helps manage a support email inbox. The goal was to build a system that can automatically fetch, analyze, prioritize, and draft responses for incoming support queries with a simple and clean clean dashboard.

## How It Works

###### email_monitor.py

It runs as a background process checking the Gmail account for new emails with subjects like "Support" or "Help". When it finds one, it extracts the data and saves it into  database with a `pending` status, then marks the email as read so it doesn't get processed again.

###### process_email.py

It queries the database for any `pending` emails and sends them to the Google Gemini API for a two-step analysis:

1. **Extraction:** First, it uses a detailed prompt to make the AI act like an analyst. It extracts key information like the user's sentiment, the urgency of the request, a one-sentence summary of their need, and any contact details.
2. **Response Generation:** Next, it takes that structured data and uses a second, separate prompt to draft a reply. This prompt tells the AI to act like an empathetic support agent, using the sentiment and request summary to create a relevant and helpful response.

###### dashboard.py

To display the dashboard I built a simple web interface using Streamlit. It connects directly to the same database and provides a real-time view of the emails table. You can see  all the emails sorted by priority, and click on any email to review the AI's work, edit the draft response, and mark the ticket as resolved.

###### emails.db

 I used a simple SQLite database. This means the monitor can keep fetching emails even if the AI processor is temporarily down, and the dashboard will always show the latest state of all tickets.

# My approach

* My main goal was to avoid creating a single script. By using a database as a message queue, the components are independent. The monitor doesn't know about the AI, and the AI doesn't know about the dashboard. This makes the system easier to debug or upgrade in the future. For example, we can swap out the Gmail monitor for an Outlook one without touching the AI processor.
* Instead of a single, complex prompt, I found it more reliable to separate the AI's tasks. The first prompt is focused on structured data extraction. The second is creative and focused on generating natural language. This leads to better, more consistent results.

# How to Run It

* pip install -r requirements.txt
* Make sure you have a `credentials.json`
* Create a `.env` file in the root directory and add your Gemini API key:
  `GEMINI_API_KEY="your_api_key_here"`
* **Initialize the Database:**
  `python database_setup.py`
* **Start the Services:**

  * In one terminal, start the email monitor: `python email_monitor.py`
  * In another terminal, you can run the processor as needed: `python process_email.py`
* **Launch the Dashboard:**
  `streamlit run dashboard.py`
