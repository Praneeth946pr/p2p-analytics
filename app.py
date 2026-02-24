import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="P2P Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp { background-color:#ffffff; font-family:'Inter','Segoe UI',sans-serif; }
    .block-container { padding:1.5rem 2rem 1rem 2rem; max-width:100%; }
    .dashboard-title {
        text-align:center; font-size:2rem; font-weight:700; color:#1a1a2e;
        background-color:#f0eaf8; padding:0.75rem 1rem; border-radius:8px;
        margin-bottom:1.25rem; letter-spacing:0.5px;
    }
    .kpi-primary {
        background:linear-gradient(135deg,#1e90ff 0%,#1565c0 100%);
        border-radius:14px; padding:1.5rem 1.25rem; text-align:center;
        color:white; min-height:110px; display:flex; flex-direction:column;
        justify-content:center; box-shadow:0 4px 15px rgba(30,90,255,0.35); margin-bottom:0.5rem;
    }
    .kpi-primary .kpi-value { font-size:2rem; font-weight:700; line-height:1.1; }
    .kpi-primary .kpi-label { font-size:0.85rem; margin-top:4px; opacity:0.9; font-weight:500; }
    .kpi-secondary {
        background-color:#ffffff; border-radius:14px; padding:1.5rem 1.25rem;
        text-align:center; color:#1a1a2e; min-height:110px; display:flex;
        flex-direction:column; justify-content:center;
        box-shadow:0 2px 10px rgba(0,0,0,0.08); margin-bottom:0.5rem;
    }
    .kpi-secondary .kpi-value { font-size:1.9rem; font-weight:700; line-height:1.1; color:#1a1a2e; }
    .kpi-secondary .kpi-label { font-size:0.82rem; margin-top:6px; color:#666; font-weight:500; }
    .chart-card {
        background-color:#ffffff; border-radius:12px; padding:0.75rem;
        box-shadow:0 2px 10px rgba(0,0,0,0.07); margin-bottom:1rem;
    }
    .chart-title {
        background-color:#f4c2a1; border-radius:6px; padding:0.4rem 0.75rem;
        font-size:0.88rem; font-weight:600; color:#2c2c2c;
        margin-bottom:0.5rem; text-align:center;
    }
    .refresh-bar { text-align:right; color:#888; font-size:0.78rem; margin-bottom:0.5rem; }
    @media (max-width:768px) {
        .block-container { padding-left:0.75rem !important; padding-right:0.75rem !important; }
        .dashboard-title { font-size:1.3rem !important; }
        [data-testid="column"] { width:100% !important; flex:1 1 100% !important; min-width:100% !important; }
        .kpi-primary,.kpi-secondary { min-height:85px !important; padding:1rem !important; }
        .kpi-primary .kpi-value,.kpi-secondary .kpi-value { font-size:1.5rem !important; }
        .kpi-primary .kpi-label,.kpi-secondary .kpi-label { font-size:0.75rem !important; }
        .chart-card { padding:0.5rem !important; }
        .chart-title { font-size:0.8rem !important; }
    }
    footer { visibility:hidden; }
    header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── DB ────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"], cursor_factory=RealDictCursor)

@st.cache_data(ttl=60)
def load_data():
    conn = get_connection()
    queries = {
        'total_po':        "SELECT COALESCE(SUM(po_amount),0) as value FROM purchase_orders",
        'total_invoice':   "SELECT COALESCE(SUM(invoice_amount),0) as value FROM invoices",
        'total_payment':   "SELECT COALESCE(SUM(payment_amount),0) as value FROM payments",
        'approval_rate':   """SELECT ROUND(COUNT(CASE WHEN approval_status='Approved' THEN 1 END)*100.0/NULLIF(COUNT(*),0),2) as value FROM invoices""",
        'payment_methods': "SELECT payment_method, SUM(payment_amount) as amount FROM payments GROUP BY payment_method ORDER BY amount DESC",
        'vendor_spend':    "SELECT v.vendor_name, SUM(po.po_amount) as total_spend FROM purchase_orders po JOIN vendors v ON po.vendor_id=v.vendor_id GROUP BY v.vendor_name ORDER BY total_spend DESC",
        'invoice_status':  "SELECT approval_status, COUNT(*) as count FROM invoices GROUP BY approval_status ORDER BY count DESC",
    }
    data = {}
    with conn.cursor() as cur:
        for key, query in queries.items():
            cur.execute(query)
            result = cur.fetchall()
            if key in ['total_po','total_invoice','total_payment','approval_rate']:
                data[key] = result[0]['value'] if result else 0
            else:
                data[key] = pd.DataFrame(result)
    return data

def fmt_k(value):
    v = float(value or 0)
    if v >= 1_000_000: return f"{v/1_000_000:.2f}M"
    if v >= 1_000:     return f"{v/1_000:.2f}K"
    return f"{v:.2f}"

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown('<div class="dashboard-title">Procure-to-Pay Analytics Dashboard</div>', unsafe_allow_html=True)

    rc1, rc2 = st.columns([1, 9])
    with rc1:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()
    with rc2:
        st.markdown(f'<div class="refresh-bar">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)

    try:
        data = load_data()
        total_po      = float(data['total_po'] or 0)
        total_inv     = float(data['total_invoice'] or 0)
        total_pay     = float(data['total_payment'] or 0)
        approval_rate = float(data['approval_rate'] or 0)

        # ── KPI Cards ────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns([1.3, 1, 1, 1])
        with k1:
            st.markdown(f'<div class="kpi-primary"><div class="kpi-value">{fmt_k(total_po)}</div><div class="kpi-label">Total PO Amount</div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="kpi-secondary"><div class="kpi-value">{fmt_k(total_inv)}</div><div class="kpi-label">Total Invoice Amount</div></div>', unsafe_allow_html=True)
        with k3:
            st.markdown(f'<div class="kpi-secondary"><div class="kpi-value">{fmt_k(total_pay)}</div><div class="kpi-label">Total Payment Amount</div></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="kpi-secondary"><div class="kpi-value">{approval_rate:.2f}</div><div class="kpi-label">% Invoices Approved</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Charts ───────────────────────────────────────────────────────────
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown('<div class="chart-card"><div class="chart-title">Payment Method Breakdown</div>', unsafe_allow_html=True)
            if not data['payment_methods'].empty:
                df_pm = data['payment_methods'].copy()
                total_pm = df_pm['amount'].sum()
                df_pm['pct'] = df_pm['amount'] / total_pm * 100
                df_pm['label'] = df_pm.apply(lambda r: f"{r['amount']/1000:.1f}K<br>({r['pct']:.2f}%)", axis=1)
                fig = go.Figure(go.Pie(
                    labels=df_pm['payment_method'], values=df_pm['amount'], hole=0.42,
                    marker=dict(colors=["#1e3a8a","#1d6ae5","#e07b39"]),
                    textposition='outside', textinfo='text', text=df_pm['label'],
                ))
                fig.update_traces(outsidetextfont=dict(size=9, color="#222222", family="Inter,sans-serif"))
                fig.update_layout(
                    paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(t=10, b=10, l=55, r=85), height=300,
                    showlegend=True,
                    legend=dict(
                        orientation="v", x=0.75, y=0.5,
                        font=dict(size=10, color="#222222", family="Inter,sans-serif"),
                        title=dict(text="payment_meth...", font=dict(size=9, color="#444444")),
                        itemsizing="constant",
                    ),
                    font=dict(family="Inter,sans-serif", size=10, color="#222222"),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No payment data available")
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="chart-card"><div class="chart-title">Vendor Spend Analysis</div>', unsafe_allow_html=True)
            if not data['vendor_spend'].empty:
                df_vs = data['vendor_spend'].sort_values('total_spend', ascending=True)
                fig = go.Figure(go.Bar(
                    x=df_vs['total_spend'], y=df_vs['vendor_name'], orientation='h',
                    marker=dict(color="#b39ddb"),
                    text=df_vs['total_spend'].apply(lambda v: f"{v/1000:.0f}K"),
                    textposition='outside', textfont=dict(size=9, color="#222222"),
                ))
                fig.update_layout(
                    paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(t=5, b=45, l=10, r=40), height=310,
                    xaxis=dict(
                        title=dict(text="Sum of po_amount", font=dict(size=11, color="#222222")),
                        tickformat=".0s", tickfont=dict(size=10, color="#222222"),
                        showgrid=True, gridcolor="#e8e0f0", zeroline=True, zerolinecolor="#ccc",
                    ),
                    yaxis=dict(
                        title=dict(text="vendor_name", font=dict(size=11, color="#222222")),
                        tickfont=dict(size=9, color="#222222"), autorange=True,
                    ),
                    font=dict(family="Inter,sans-serif", size=10, color="#222222"),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No vendor data available")
            st.markdown('</div>', unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="chart-card"><div class="chart-title">Invoice Approval Status</div>', unsafe_allow_html=True)
            if not data['invoice_status'].empty:
                df_is = data['invoice_status']
                fig = go.Figure(go.Bar(
                    x=df_is['approval_status'], y=df_is['count'],
                    marker=dict(color="#b39ddb"),
                    text=df_is['count'], textposition='outside',
                    textfont=dict(size=11, color="#222222"),
                ))
                fig.update_layout(
                    paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(t=25, b=45, l=10, r=10), height=310,
                    xaxis=dict(
                        title=dict(text="approval_status", font=dict(size=11, color="#222222")),
                        tickfont=dict(size=11, color="#222222"), showgrid=False, zeroline=False,
                    ),
                    yaxis=dict(
                        title=dict(text="Count of invoice_id", font=dict(size=11, color="#222222")),
                        tickfont=dict(size=10, color="#222222"),
                        showgrid=True, gridcolor="#e8e0f0",
                        zeroline=True, zerolinecolor="#ccc", dtick=5,
                    ),
                    font=dict(family="Inter,sans-serif", size=10, color="#222222"),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("No invoice data available")
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ Error connecting to database: {str(e)}")
        st.info("Please check your database connection settings in Streamlit secrets.")

if __name__ == "__main__":
    main()
