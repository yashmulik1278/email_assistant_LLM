# dashboard.py
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, timedelta
import json

DB_FILE = "emails.db"

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Email Assistant Dashboard",
    page_icon="📧",
    layout="wide"
)

# --- Database Functions ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    return sqlite3.connect(DB_FILE)

@st.cache_data(ttl=60) # Cache data for 60 seconds
def load_data():
    """Loads all email data from the database into a pandas DataFrame."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM emails", conn)
        # Convert date column to datetime objects
        df['received_at'] = pd.to_datetime(df['received_at'])
        return df
    except Exception as e:
        st.error(f"Failed to load data from database: {e}")
        return pd.DataFrame() # Return empty dataframe on error
    finally:
        conn.close()

def update_email_status(email_id, new_status):
    """Updates the status of a specific email in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE emails SET status = ? WHERE id = ?", (new_status, email_id))
        conn.commit()
    finally:
        conn.close()
    # Clear the cache to force a data reload on the next run
    st.cache_data.clear()

# --- Main Dashboard ---
st.title("📧 AI Email Assistant Dashboard")
st.markdown("Manage and respond to support emails efficiently.")

# Load the data
df = load_data()

if df.empty:
    st.warning("No emails found in the database. Run the email monitor to fetch new emails.")
else:
    # --- Key Metrics ---
    st.subheader("Analytics Overview")
    
    # Calculate metrics
    time_24_hours_ago = datetime.now() - timedelta(hours=24)
    emails_last_24h = df[df['received_at'] > time_24_hours_ago].shape[0]
    emails_pending = df[df['status'] == 'pending'].shape[0]
    emails_processed = df[df['status'] == 'processed'].shape[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Emails (Last 24H)", emails_last_24h)
    col2.metric("Pending Emails", emails_pending, help="Emails fetched but not yet analyzed by the AI.")
    col3.metric("Processed Emails", emails_processed, help="Emails analyzed and have a draft response.")

    # --- Interactive Charts ---
    col1, col2 = st.columns(2)

    with col1:
        sentiment_counts = df['sentiment'].value_counts().reset_index()
        sentiment_counts.columns = ['sentiment', 'count']
        fig_sentiment = px.pie(sentiment_counts, names='sentiment', values='count', 
                               title='Sentiment Distribution', hole=0.3,
                               color_discrete_map={'Positive':'green', 'Negative':'red', 'Neutral':'blue'})
        st.plotly_chart(fig_sentiment, use_container_width=True)

    with col2:
        priority_counts = df['priority'].value_counts().reset_index()
        priority_counts.columns = ['priority', 'count']
        fig_priority = px.bar(priority_counts, x='priority', y='count', 
                              title='Priority Distribution', color='priority',
                              color_discrete_map={'Urgent':'red', 'Not urgent':'green'})
        st.plotly_chart(fig_priority, use_container_width=True)

    st.divider()

    # --- Email Listing and Details ---
    st.subheader("Support Email Inbox")
    
    # Sort emails to show Urgent and Pending first
    df_display = df.sort_values(by=['priority', 'status', 'received_at'], 
                                ascending=[False, True, False])
    
    # Columns to display in the main table
    display_cols = ['id', 'sender', 'subject', 'priority', 'sentiment', 'status', 'received_at']
    st.dataframe(df_display[display_cols], use_container_width=True, hide_index=True)

    # --- Detail View and Response Editor ---
    st.subheader("Email Details & AI Response")
    
    # Dropdown to select an email to view
    if not df_display.empty:
        selected_id = st.selectbox(
            "Select an Email ID to view details and respond:",
            options=df_display['id'],
            format_func=lambda x: f"ID: {x} - {df_display.loc[df_display['id'] == x, 'subject'].iloc[0]}"
        )
    
        if selected_id:
            email = df[df['id'] == selected_id].iloc[0]
            
            col1, col2 = st.columns([2, 1]) # Make the first column wider

            with col1:
                st.write(f"**From:** {email['sender']}")
                st.write(f"**Subject:** {email['subject']}")
                st.text_area("Full Email Body:", value=email['body'], height=250, disabled=True)
                
                # Display extracted information
                st.write("**Extracted Information:**")
                st.write(f"  - **Customer Request:** *{email['customer_request']}*")
                try:
                    # Format the contact info JSON for nice display
                    contact_info = json.loads(email['contact_info']) if email['contact_info'] else {}
                    contact_display = ", ".join([f"{k}: {v}" for k, v in contact_info.items()]) if contact_info else "None"
                    st.write(f"  - **Contact Info:** {contact_display}")
                except (json.JSONDecodeError, TypeError):
                    st.write(f"  - **Contact Info:** {email['contact_info']}")


            with col2:
                st.write("**AI-Generated Response:**")
                draft_response = st.text_area(
                    "You can edit the response below before sending:", 
                    value=email['generated_response'], 
                    height=300
                )
                
                # ### MODIFIED SECTION ###
                # Check the status of the selected email to determine button state
                if email['status'] == 'resolved':
                    st.button("Resolved", disabled=True, help="This email has already been resolved.")
                else:
                    if st.button("Mark as Resolved / Sent", key=f"resolve_{selected_id}"):
                        update_email_status(selected_id, "resolved")
                        st.success(f"Email ID {selected_id} marked as 'resolved'.")
                        st.rerun()