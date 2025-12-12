import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import yaml

# --- Configuration & Setup ---
st.set_page_config(page_title="Tax Commander Dashboard", page_icon="📊", layout="wide")

def load_config(config_path="config.yaml"):
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return {}

config = load_config()
db_path = config.get('system', {}).get('database_file', 'tioga_tax.db')

# --- Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect(db_path)
    return conn

def load_data():
    conn = get_db_connection()
    
    # Parcel Data (Duplicate)
    query_parcels = "SELECT * FROM tax_duplicate"
    df_parcels = pd.read_sql(query_parcels, conn)
    
    # Transaction Data
    query_transactions = "SELECT * FROM transactions"
    df_transactions = pd.read_sql(query_transactions, conn)
    
    conn.close()
    return df_parcels, df_transactions

# --- Main Dashboard ---
st.title("📊 Tioga Township Tax Collector Dashboard")
st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")

try:
    df_parcels, df_transactions = load_data()
except Exception as e:
    st.error(f"Error loading database: {e}")
    st.stop()

# --- KPI Row ---
col1, col2, col3, col4 = st.columns(4)

total_face_value = df_parcels['face_tax_amount'].sum()
total_collected = df_transactions[df_transactions['transaction_type'] == 'PAYMENT']['amount_paid'].sum()
collection_rate = (total_collected / total_face_value * 100) if total_face_value > 0 else 0
total_parcels_count = len(df_parcels)
paid_parcels_count = len(df_parcels[df_parcels['status'] == 'PAID'])

with col1:
    st.metric("Total Face Value", f"${total_face_value:,.2f}")
with col2:
    st.metric("Total Collected (YTD)", f"${total_collected:,.2f}", delta=f"{collection_rate:.1f}%")
with col3:
    st.metric("Parcels Paid", f"{paid_parcels_count} / {total_parcels_count}")
with col4:
    st.metric("Outstanding Balance (Est)", f"${(total_face_value - total_collected):,.2f}")

st.markdown("---")

# --- Charts Row ---
col_charts_1, col_charts_2 = st.columns(2)

with col_charts_1:
    st.subheader("Collection Status Distribution")
    if not df_parcels.empty:
        status_counts = df_parcels['status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Count']
        fig_pie = px.pie(status_counts, values='Count', names='Status', hole=0.4, color='Status',
                         color_discrete_map={'PAID': 'green', 'UNPAID': 'red', 'PARTIAL': 'orange', 'EXONERATED': 'gray'})
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No parcel data available.")

with col_charts_2:
    st.subheader("Revenue by Tax Type")
    if not df_parcels.empty and not df_transactions.empty:
        # Join for tax type
        # (Simple merge for this view)
        merged_df = pd.merge(df_transactions, df_parcels[['parcel_id', 'tax_type']], on='parcel_id', how='left')
        revenue_by_type = merged_df.groupby('tax_type')['amount_paid'].sum().reset_index()
        
        fig_bar = px.bar(revenue_by_type, x='tax_type', y='amount_paid', 
                         labels={'amount_paid': 'Amount Collected ($)', 'tax_type': 'Tax Type'},
                         color='tax_type')
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No transaction data available.")

# --- Recent Activity ---
st.subheader("Recent Transactions")
if not df_transactions.empty:
    # Clean up for display
    display_df = df_transactions[['date_received', 'parcel_id', 'transaction_type', 'amount_paid', 'payment_method', 'check_number']].copy()
    display_df['date_received'] = pd.to_datetime(display_df['date_received']).dt.date
    display_df = display_df.sort_values(by='date_received', ascending=False)
    
    st.dataframe(display_df, use_container_width=True)
else:
    st.info("No recent transactions.")

# --- Quick Links / Info ---
with st.expander("ℹ️ About This Dashboard"):
    st.write("""
    This dashboard provides a real-time view of the Tioga Township tax collection database.
    - **Total Face Value:** Sum of all face amounts in the duplicate.
    - **Total Collected:** Sum of all valid payments received.
    - **Charts:** Generated dynamically from current data.
    """)
