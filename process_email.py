# process_email.py
import os
import json
import sqlite3
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
DB_FILE = "emails.db"

# --- Setup the Gemini Model ---
if not API_KEY:
    raise ValueError("Error: GEMINI_API_KEY not found in .env file.")

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    print("Successfully configured Gemini model.")
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    exit()

def analyze_email_content(email_content):
    """
    Sends email content to Gemini for detailed analysis and information extraction.
    """
    prompt = f"""
    You are an expert data analyst. Your task is to analyze the following email and extract key information.
    
    Analyze the email's content to determine its sentiment, priority, summarize the customer's core request, and extract any contact information found.

    Respond ONLY with a single, minified JSON object with the following keys: "sentiment", "priority", "customer_request", "contact_info".
    - "sentiment": Must be one of "Positive", "Negative", or "Neutral".
    - "priority": Must be one of "Urgent" or "Not urgent".
    - "customer_request": Must be a brief, one-sentence summary of what the customer wants.
    - "contact_info": Must be a JSON object containing any phone numbers or alternate emails found. If none are found, this should be an empty object {{}}.

    Email Content:
    ---
    {email_content}
    ---
    """
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```").strip()
        analysis = json.loads(cleaned_response)
        
        required_keys = ["sentiment", "priority", "customer_request", "contact_info"]
        if all(key in analysis for key in required_keys):
            return analysis
        else:
            print(f"Warning: Model response missing required keys. Response: {analysis}")
            return None
            
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from model response: {response.text}")
        return None
    except Exception as e:
        print(f"An error occurred during Gemini API call: {e}")
        return None

def generate_response(sentiment, priority, email_body):
    """Generates a context-aware draft response using Gemini."""
    knowledge_base = """
    - Our standard support hours are 9 AM to 6 PM, Monday to Friday.
    - Password resets can be done by the user at our website's login page via the 'Forgot Password' link.
    - Our premium plan costs $99/month and includes advanced analytics and priority support.
    - For billing issues, users should be directed to the billing department by replying to this email and we will forward it.
    """
    
    prompt = f"""
    You are a professional and empathetic customer support assistant. Your task is to draft a response to a customer's email.

    **Analysis of the incoming email:**
    - Customer Sentiment: {sentiment}
    - Priority Level: {priority}

    **Your Instructions:**
    1.  Acknowledge and Empathize: If the sentiment is 'Negative', start by acknowledging the customer's frustration.
    2.  Maintain a Professional Tone: Be friendly, helpful, and concise.
    3.  Use the Knowledge Base: Use the provided knowledge base to answer questions accurately.
    4.  Provide Clear Next Steps: Either solve the user's problem directly or explain what will happen next.
    5.  Do NOT include a generic sign-off like "Best regards", as this will be added later.

    **Knowledge Base for Your Response:**
    ---
    {knowledge_base}
    ---

    **Original Customer Email:**
    ---
    {email_body}
    ---

    **Draft your response below:**
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"An error occurred during response generation: {e}")
        return "Failed to generate a response."

def main():
    """Main function to loop through emails in the DB, process them, and generate responses."""
    print(f"\nStarting analysis and response generation from '{DB_FILE}'...")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()

        cursor.execute("SELECT id, sender, subject, body FROM emails WHERE status = 'pending'")
        pending_emails = cursor.fetchall()

        if not pending_emails:
            print("No pending emails to process.")
            return
            
        print(f"Found {len(pending_emails)} emails to process.")
        for email in pending_emails:
            print("-" * 40)
            print(f"Processing email ID: {email['id']} from: {email['sender']}")
            
            full_email_content = f"Subject: {email['subject']}\n\n{email['body']}"
            
            analysis_result = analyze_email_content(full_email_content)
            
            if analysis_result:
                priority = analysis_result['priority']
                sentiment = analysis_result['sentiment']
                customer_request = analysis_result['customer_request']
                contact_info_str = json.dumps(analysis_result['contact_info'])

                print(f"  -> Analysis complete:")
                print(f"     - Priority: {priority}")
                print(f"     - Sentiment: {sentiment}")
                print(f"     - Request: {customer_request}")
                print(f"     - Contact Info: {contact_info_str}")

                draft_response = generate_response(sentiment, priority, full_email_content)
                print(f"  -> Generated Draft Response:\n---\n{draft_response}\n---")
                
                update_query = """
                UPDATE emails
                SET 
                    sentiment = ?, 
                    priority = ?, 
                    generated_response = ?, 
                    customer_request = ?,
                    contact_info = ?,
                    status = 'processed'
                WHERE id = ?;
                """
                cursor.execute(update_query, (
                    sentiment, 
                    priority, 
                    draft_response, 
                    customer_request, 
                    contact_info_str, 
                    email['id']
                ))
                conn.commit()
                print(f"  -> Successfully updated database for email ID: {email['id']}")
            else:
                print("  -> Analysis failed for this email. Skipping.")

    except sqlite3.Error as e:
        print(f"Database error during processing: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    main()