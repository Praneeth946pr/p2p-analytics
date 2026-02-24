import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Page Configuration
st.set_page_config(
    page_title="P2P Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1e3a5f;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Database Connection
@st.cache_resource
def get_connection():
    """Create database connection using secrets"""
    return psycopg2.connect(
        st.secrets["DATABASE_URL"],
        cursor_factory=RealDictCursor
    )

@st.cache_data(ttl=60)  # Cache for 60 seconds, then auto-refresh
def load_data():
    """Load all data from PostgreSQL"""
    conn = get_connection()
    
    # KPI Queries
    queries = {
        'total_po': "SELECT COALESCE(SUM(po_amount), 0) as value FROM purchase_orders",
        'total_invoice': "SELECT COALESCE(SUM(invoice_amount), 0) as value FROM invoices",
        'total_payment': "SELECT COALESCE(SUM(payment_amount), 0) as value FROM payments",
        'approval_rate': """
            SELECT ROUND(
                COUNT(CASE WHEN approval_status = 'Approved' THEN 1 END) * 100.0 / 
                NULLIF(COUNT(*), 0), 2
            ) as value FROM invoices
        """,
        'payment_methods': """
            SELECT payment_method, SUM(payment_amount) as amount
            FROM payments
            GROUP BY payment_method
            ORDER BY amount DESC
        """,
        'vendor_spend': """
            SELECT v.vendor_name, SUM(po.po_amount) as total_spend
            FROM purchase_orders po
            JOIN vendors v ON po.vendor_id = v.vendor_id
            GROUP BY v.vendor_name
            ORDER BY total_spend DESC
        """,
        'invoice_status': """
            SELECT approval_status, COUNT(*) as count
            FROM invoices
            GROUP BY approval_status
            ORDER BY count DESC
        """
    }
    
    data = {}
    with conn.cursor() as cur:
        for key, query in queries.items():
            cur.execute(query)
            result = cur.fetchall()
            if key in ['total_po', 'total_invoice', 'total_payment', 'approval_rate']:
                data[key] = result[0]['value'] if result else 0
            else:
                data[key] = pd.DataFrame(result)
    
    return data

def format_currency(value):
    """Format number as currency with K suffix"""
    if value >= 1000:
        return f"${value/1000:.2f}K"
    return f"${value:.2f}"

def main():
    # Header
    st.markdown('<h1 class="main-header">📊 Procure-to-Pay Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Auto-refresh button
    col_refresh, col_time = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    with col_time:
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    st.divider()
    
    try:
        # Load data
        data = load_data()
        
        # KPI Cards Row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💰 Total PO Amount",
                value=format_currency(float(data['total_po'] or 0)),
                delta=None
            )
        
        with col2:
            st.metric(
                label="📄 Total Invoice Amount",
                value=format_currency(float(data['total_invoice'] or 0)),
                delta=None
            )
        
        with col3:
            st.metric(
                label="💳 Total Payment Amount",
                value=format_currency(float(data['total_payment'] or 0)),
                delta=None
            )
        
        with col4:
            st.metric(
                label="✅ Invoices Approved",
                value=f"{data['approval_rate'] or 0}%",
                delta=None
            )
        
        st.divider()
        
        # Charts Row
        chart_col1, chart_col2, chart_col3 = st.columns(3)
        
        # Payment Method Breakdown (Pie Chart)
        with chart_col1:
            st.subheader("Payment Method Breakdown")
            if not data['payment_methods'].empty:
                fig_pie = px.pie(
                    data['payment_methods'],
                    values='amount',
                    names='payment_method',
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.0
                )
                fig_pie.update_traces(
                    textposition='outside',
                    textinfo='percent+label+value',
                    texttemplate='%{label}<br>$%{value:,.0f}<br>(%{percent})'
                )
                fig_pie.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                    margin=dict(t=20, b=80, l=20, r=20),
                    height=400
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No payment data available")
        
        # Vendor Spend Analysis (Horizontal Bar Chart)
        with chart_col2:
            st.subheader("Vendor Spend Analysis")
            if not data['vendor_spend'].empty:
                fig_bar = px.bar(
                    data['vendor_spend'],
                    x='total_spend',
                    y='vendor_name',
                    orientation='h',
                    color='total_spend',
                    color_continuous_scale='Purples'
                )
                fig_bar.update_layout(
                    xaxis_title="Sum of PO Amount",
                    yaxis_title="",
                    showlegend=False,
                    coloraxis_showscale=False,
                    margin=dict(t=20, b=40, l=20, r=20),
                    height=400
                )
                fig_bar.update_traces(
                    texttemplate='$%{x:,.0f}',
                    textposition='outside'
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No vendor data available")
        
        # Invoice Approval Status (Column Chart)
        with chart_col3:
            st.subheader("Invoice Approval Status")
            if not data['invoice_status'].empty:
                # Define colors for each status
                color_map = {
                    'Approved': '#9b59b6',
                    'Pending': '#a569bd',
                    'Disputed': '#bb8fce'
                }
                fig_col = px.bar(
                    data['invoice_status'],
                    x='approval_status',
                    y='count',
                    color='approval_status',
                    color_discrete_map=color_map
                )
                fig_col.update_layout(
                    xaxis_title="Approval Status",
                    yaxis_title="Count of Invoices",
                    showlegend=False,
                    margin=dict(t=20, b=40, l=20, r=20),
                    height=400
                )
                fig_col.update_traces(
                    texttemplate='%{y}',
                    textposition='outside'
                )
                st.plotly_chart(fig_col, use_container_width=True)
            else:
                st.info("No invoice data available")
        
        # Footer
        st.divider()
        st.markdown("""
        <div style="text-align: center; color: #666; font-size: 0.8rem;">
            Built with Streamlit | Data refreshes automatically every 60 seconds | 
            <a href="https://github.com/yourusername/p2p-analytics" target="_blank">View Source</a>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error connecting to database: {str(e)}")
        st.info("Please check your database connection settings in Streamlit secrets.")

if __name__ == "__main__":
    main()
