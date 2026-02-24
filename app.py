import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
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
    .section-header {
        font-size:1.3rem; font-weight:700; color:#1a1a2e;
        border-left:4px solid #1e90ff; padding-left:0.75rem;
        margin:1.5rem 0 1rem 0;
    }
    @media (max-width:768px) {
        .block-container { padding-left:0.75rem !important; padding-right:0.75rem !important; }
        .dashboard-title { font-size:1.3rem !important; }
        [data-testid="column"] { width:100% !important; flex:1 1 100% !important; min-width:100% !important; }
        .kpi-primary,.kpi-secondary { min-height:85px !important; padding:1rem !important; }
        .kpi-primary .kpi-value,.kpi-secondary .kpi-value { font-size:1.5rem !important; }
    }
    footer { visibility:hidden; }
    header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── DB Connection ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"], cursor_factory=RealDictCursor)

def get_conn():
    """Always-fresh connection for writes."""
    return psycopg2.connect(st.secrets["DATABASE_URL"], cursor_factory=RealDictCursor)

@st.cache_data(ttl=30)
def load_data():
    conn = get_connection()
    queries = {
        'total_po':       "SELECT COALESCE(SUM(po_amount),0) as value FROM purchase_orders",
        'total_invoice':  "SELECT COALESCE(SUM(invoice_amount),0) as value FROM invoices",
        'total_payment':  "SELECT COALESCE(SUM(payment_amount),0) as value FROM payments",
        'approval_rate':  """SELECT ROUND(COUNT(CASE WHEN approval_status='Approved' THEN 1 END)*100.0/NULLIF(COUNT(*),0),2) as value FROM invoices""",
        'payment_methods': "SELECT payment_method, SUM(payment_amount) as amount FROM payments GROUP BY payment_method ORDER BY amount DESC",
        'vendor_spend':   "SELECT v.vendor_name, SUM(po.po_amount) as total_spend FROM purchase_orders po JOIN vendors v ON po.vendor_id=v.vendor_id GROUP BY v.vendor_name ORDER BY total_spend DESC",
        'invoice_status': "SELECT approval_status, COUNT(*) as count FROM invoices GROUP BY approval_status ORDER BY count DESC",
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

def load_table(table_sql):
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(table_sql)
        return pd.DataFrame(cur.fetchall())

def fmt_k(value):
    v = float(value or 0)
    if v >= 1_000_000: return f"{v/1_000_000:.2f}M"
    if v >= 1_000:     return f"{v/1_000:.2f}K"
    return f"{v:.2f}"

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown('<div class="dashboard-title">Procure-to-Pay Analytics Dashboard</div>', unsafe_allow_html=True)

    # Refresh row
    rc1, rc2 = st.columns([1,9])
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
        k1,k2,k3,k4 = st.columns([1.3,1,1,1])
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
        c1,c2,c3 = st.columns(3)

        with c1:
            st.markdown('<div class="chart-card"><div class="chart-title">Payment Method Breakdown</div>', unsafe_allow_html=True)
            if not data['payment_methods'].empty:
                df_pm = data['payment_methods'].copy()
                total_pm = df_pm['amount'].sum()
                df_pm['pct'] = df_pm['amount']/total_pm*100
                df_pm['label'] = df_pm.apply(lambda r: f"{r['amount']/1000:.1f}K<br>({r['pct']:.2f}%)", axis=1)
                fig = go.Figure(go.Pie(
                    labels=df_pm['payment_method'], values=df_pm['amount'], hole=0.42,
                    marker=dict(colors=["#1e3a8a","#1d6ae5","#e07b39"]),
                    textposition='outside', textinfo='text', text=df_pm['label'],
                ))
                fig.update_traces(outsidetextfont=dict(size=9,color="#222222",family="Inter,sans-serif"))
                fig.update_layout(
                    paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(t=10,b=10,l=55,r=85), height=300, showlegend=True,
                    legend=dict(orientation="v",x=0.75,y=0.5,font=dict(size=10,color="#222222",family="Inter,sans-serif"),
                                title=dict(text="payment_meth...",font=dict(size=9,color="#444444")),itemsizing="constant"),
                    font=dict(family="Inter,sans-serif",size=10,color="#222222"),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="chart-card"><div class="chart-title">Vendor Spend Analysis</div>', unsafe_allow_html=True)
            if not data['vendor_spend'].empty:
                df_vs = data['vendor_spend'].sort_values('total_spend', ascending=True)
                fig = go.Figure(go.Bar(
                    x=df_vs['total_spend'], y=df_vs['vendor_name'], orientation='h',
                    marker=dict(color="#b39ddb"),
                    text=df_vs['total_spend'].apply(lambda v: f"{v/1000:.0f}K"),
                    textposition='outside', textfont=dict(size=9,color="#222222"),
                ))
                fig.update_layout(
                    paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(t=5,b=45,l=10,r=40), height=310,
                    xaxis=dict(title=dict(text="Sum of po_amount",font=dict(size=11,color="#222222")),
                               tickformat=".0s",tickfont=dict(size=10,color="#222222"),
                               showgrid=True,gridcolor="#e8e0f0",zeroline=True,zerolinecolor="#ccc"),
                    yaxis=dict(title=dict(text="vendor_name",font=dict(size=11,color="#222222")),
                               tickfont=dict(size=9,color="#222222"),autorange=True),
                    font=dict(family="Inter,sans-serif",size=10,color="#222222"),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

        with c3:
            st.markdown('<div class="chart-card"><div class="chart-title">Invoice Approval Status</div>', unsafe_allow_html=True)
            if not data['invoice_status'].empty:
                df_is = data['invoice_status']
                fig = go.Figure(go.Bar(
                    x=df_is['approval_status'], y=df_is['count'],
                    marker=dict(color="#b39ddb"),
                    text=df_is['count'], textposition='outside',
                    textfont=dict(size=11,color="#222222"),
                ))
                fig.update_layout(
                    paper_bgcolor="white", plot_bgcolor="white",
                    margin=dict(t=25,b=45,l=10,r=10), height=310,
                    xaxis=dict(title=dict(text="approval_status",font=dict(size=11,color="#222222")),
                               tickfont=dict(size=11,color="#222222"),showgrid=False,zeroline=False),
                    yaxis=dict(title=dict(text="Count of invoice_id",font=dict(size=11,color="#222222")),
                               tickfont=dict(size=10,color="#222222"),showgrid=True,
                               gridcolor="#e8e0f0",zeroline=True,zerolinecolor="#ccc",dtick=5),
                    font=dict(family="Inter,sans-serif",size=10,color="#222222"),showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

        # ── CRUD Section ─────────────────────────────────────────────────────
        st.markdown('<div class="section-header">📋 Data Management (CRUD)</div>', unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs(["🏢 Vendors", "📦 Purchase Orders", "🧾 Invoices", "💳 Payments"])

        # ═══════════════════════ VENDORS TAB ═══════════════════════
        with tab1:
            df_v = load_table("SELECT vendor_id, vendor_name, contact_email, vendor_category FROM vendors ORDER BY vendor_id")
            st.dataframe(df_v, use_container_width=True, hide_index=True)

            op = st.radio("Action", ["➕ Add Vendor", "✏️ Edit Vendor", "🗑️ Delete Vendor"], horizontal=True, key="v_op")

            if op == "➕ Add Vendor":
                with st.form("add_vendor"):
                    st.subheader("Add New Vendor")
                    name  = st.text_input("Vendor Name *")
                    email = st.text_input("Contact Email")
                    cat   = st.selectbox("Category", ["Construction","Technology","Logistics","Office Supplies","Other"])
                    if st.form_submit_button("✅ Save Vendor", type="primary"):
                        if not name:
                            st.error("Vendor name is required.")
                        else:
                            with get_conn() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("INSERT INTO vendors (vendor_name,contact_email,vendor_category) VALUES (%s,%s,%s)", (name,email,cat))
                                conn.commit()
                            st.success(f"✅ Vendor '{name}' added!")
                            st.cache_data.clear(); st.rerun()

            elif op == "✏️ Edit Vendor":
                if df_v.empty:
                    st.info("No vendors to edit.")
                else:
                    vid = st.selectbox("Select Vendor", df_v['vendor_id'].tolist(),
                                       format_func=lambda x: df_v[df_v['vendor_id']==x]['vendor_name'].values[0], key="v_edit_sel")
                    row = df_v[df_v['vendor_id']==vid].iloc[0]
                    with st.form("edit_vendor"):
                        st.subheader(f"Editing: {row['vendor_name']}")
                        name  = st.text_input("Vendor Name", value=row['vendor_name'])
                        email = st.text_input("Email", value=row['contact_email'] or "")
                        cat   = st.selectbox("Category", ["Construction","Technology","Logistics","Office Supplies","Other"],
                                             index=["Construction","Technology","Logistics","Office Supplies","Other"].index(row['vendor_category']) if row['vendor_category'] in ["Construction","Technology","Logistics","Office Supplies","Other"] else 4)
                        if st.form_submit_button("💾 Update Vendor", type="primary"):
                            with get_conn() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("UPDATE vendors SET vendor_name=%s,contact_email=%s,vendor_category=%s WHERE vendor_id=%s",
                                                (name,email,cat,vid))
                                conn.commit()
                            st.success("✅ Vendor updated!")
                            st.cache_data.clear(); st.rerun()

            else:  # Delete
                if df_v.empty:
                    st.info("No vendors to delete.")
                else:
                    vid = st.selectbox("Select Vendor to Delete", df_v['vendor_id'].tolist(),
                                       format_func=lambda x: df_v[df_v['vendor_id']==x]['vendor_name'].values[0], key="v_del_sel")
                    vname = df_v[df_v['vendor_id']==vid]['vendor_name'].values[0]
                    st.warning(f"⚠️ This will delete **{vname}** and may affect related POs. Are you sure?")
                    if st.button("🗑️ Confirm Delete Vendor", type="primary"):
                        with get_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM vendors WHERE vendor_id=%s", (vid,))
                            conn.commit()
                        st.success(f"✅ Vendor '{vname}' deleted!")
                        st.cache_data.clear(); st.rerun()

        # ═══════════════════════ PURCHASE ORDERS TAB ═══════════════════════
        with tab2:
            df_po = load_table("""
                SELECT po.po_id, v.vendor_name, po.po_number, po.po_amount, po.po_date::text, po.status
                FROM purchase_orders po JOIN vendors v ON po.vendor_id=v.vendor_id ORDER BY po.po_id
            """)
            st.dataframe(df_po, use_container_width=True, hide_index=True)

            df_vendors = load_table("SELECT vendor_id, vendor_name FROM vendors ORDER BY vendor_name")
            op = st.radio("Action", ["➕ Add PO", "✏️ Edit PO", "🗑️ Delete PO"], horizontal=True, key="po_op")

            if op == "➕ Add PO":
                with st.form("add_po"):
                    st.subheader("Add New Purchase Order")
                    vendor  = st.selectbox("Vendor", df_vendors['vendor_id'].tolist(),
                                           format_func=lambda x: df_vendors[df_vendors['vendor_id']==x]['vendor_name'].values[0])
                    po_num  = st.text_input("PO Number *")
                    amount  = st.number_input("PO Amount ($)", min_value=0.0, step=100.0)
                    po_date = st.date_input("PO Date", value=date.today())
                    status  = st.selectbox("Status", ["Open","Closed","Cancelled"])
                    if st.form_submit_button("✅ Save PO", type="primary"):
                        if not po_num:
                            st.error("PO Number is required.")
                        else:
                            with get_conn() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("INSERT INTO purchase_orders (vendor_id,po_number,po_amount,po_date,status) VALUES (%s,%s,%s,%s,%s)",
                                                (vendor,po_num,amount,po_date,status))
                                conn.commit()
                            st.success(f"✅ PO '{po_num}' added!")
                            st.cache_data.clear(); st.rerun()

            elif op == "✏️ Edit PO":
                if df_po.empty:
                    st.info("No POs to edit.")
                else:
                    po_id = st.selectbox("Select PO", df_po['po_id'].tolist(),
                                         format_func=lambda x: df_po[df_po['po_id']==x]['po_number'].values[0], key="po_edit_sel")
                    row = df_po[df_po['po_id']==po_id].iloc[0]
                    with st.form("edit_po"):
                        st.subheader(f"Editing PO: {row['po_number']}")
                        vendor  = st.selectbox("Vendor", df_vendors['vendor_id'].tolist(),
                                               format_func=lambda x: df_vendors[df_vendors['vendor_id']==x]['vendor_name'].values[0])
                        po_num  = st.text_input("PO Number", value=row['po_number'])
                        amount  = st.number_input("PO Amount ($)", value=float(row['po_amount']), min_value=0.0, step=100.0)
                        po_date = st.date_input("PO Date", value=datetime.strptime(row['po_date'], "%Y-%m-%d").date())
                        statuses = ["Open","Closed","Cancelled"]
                        status  = st.selectbox("Status", statuses, index=statuses.index(row['status']) if row['status'] in statuses else 0)
                        if st.form_submit_button("💾 Update PO", type="primary"):
                            with get_conn() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("UPDATE purchase_orders SET vendor_id=%s,po_number=%s,po_amount=%s,po_date=%s,status=%s WHERE po_id=%s",
                                                (vendor,po_num,amount,po_date,status,po_id))
                                conn.commit()
                            st.success("✅ PO updated!")
                            st.cache_data.clear(); st.rerun()

            else:
                if df_po.empty:
                    st.info("No POs to delete.")
                else:
                    po_id = st.selectbox("Select PO to Delete", df_po['po_id'].tolist(),
                                         format_func=lambda x: df_po[df_po['po_id']==x]['po_number'].values[0], key="po_del_sel")
                    po_num = df_po[df_po['po_id']==po_id]['po_number'].values[0]
                    st.warning(f"⚠️ Delete PO **{po_num}**? This may affect related invoices.")
                    if st.button("🗑️ Confirm Delete PO", type="primary"):
                        with get_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM purchase_orders WHERE po_id=%s", (po_id,))
                            conn.commit()
                        st.success(f"✅ PO '{po_num}' deleted!")
                        st.cache_data.clear(); st.rerun()

        # ═══════════════════════ INVOICES TAB ═══════════════════════
        with tab3:
            df_inv = load_table("""
                SELECT i.invoice_id, i.invoice_number, p.po_number, i.invoice_amount,
                       i.invoice_date::text, i.approval_status
                FROM invoices i JOIN purchase_orders p ON i.po_id=p.po_id ORDER BY i.invoice_id
            """)
            st.dataframe(df_inv, use_container_width=True, hide_index=True)

            df_pos = load_table("SELECT po_id, po_number FROM purchase_orders ORDER BY po_number")
            op = st.radio("Action", ["➕ Add Invoice", "✏️ Edit Invoice", "🗑️ Delete Invoice"], horizontal=True, key="inv_op")
            statuses = ["Approved","Pending","Disputed"]

            if op == "➕ Add Invoice":
                with st.form("add_inv"):
                    st.subheader("Add New Invoice")
                    po_id   = st.selectbox("Purchase Order", df_pos['po_id'].tolist(),
                                           format_func=lambda x: df_pos[df_pos['po_id']==x]['po_number'].values[0])
                    inv_num = st.text_input("Invoice Number *")
                    amount  = st.number_input("Invoice Amount ($)", min_value=0.0, step=100.0)
                    inv_date = st.date_input("Invoice Date", value=date.today())
                    status  = st.selectbox("Approval Status", statuses)
                    if st.form_submit_button("✅ Save Invoice", type="primary"):
                        if not inv_num:
                            st.error("Invoice number is required.")
                        else:
                            with get_conn() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("INSERT INTO invoices (po_id,invoice_number,invoice_amount,invoice_date,approval_status) VALUES (%s,%s,%s,%s,%s)",
                                                (po_id,inv_num,amount,inv_date,status))
                                conn.commit()
                            st.success(f"✅ Invoice '{inv_num}' added!")
                            st.cache_data.clear(); st.rerun()

            elif op == "✏️ Edit Invoice":
                if df_inv.empty:
                    st.info("No invoices to edit.")
                else:
                    inv_id = st.selectbox("Select Invoice", df_inv['invoice_id'].tolist(),
                                          format_func=lambda x: df_inv[df_inv['invoice_id']==x]['invoice_number'].values[0], key="inv_edit_sel")
                    row = df_inv[df_inv['invoice_id']==inv_id].iloc[0]
                    with st.form("edit_inv"):
                        st.subheader(f"Editing Invoice: {row['invoice_number']}")
                        po_id   = st.selectbox("Purchase Order", df_pos['po_id'].tolist(),
                                               format_func=lambda x: df_pos[df_pos['po_id']==x]['po_number'].values[0])
                        inv_num = st.text_input("Invoice Number", value=row['invoice_number'])
                        amount  = st.number_input("Invoice Amount ($)", value=float(row['invoice_amount']), min_value=0.0, step=100.0)
                        inv_date = st.date_input("Invoice Date", value=datetime.strptime(row['invoice_date'], "%Y-%m-%d").date())
                        status  = st.selectbox("Approval Status", statuses,
                                               index=statuses.index(row['approval_status']) if row['approval_status'] in statuses else 1)
                        if st.form_submit_button("💾 Update Invoice", type="primary"):
                            with get_conn() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("UPDATE invoices SET po_id=%s,invoice_number=%s,invoice_amount=%s,invoice_date=%s,approval_status=%s WHERE invoice_id=%s",
                                                (po_id,inv_num,amount,inv_date,status,inv_id))
                                conn.commit()
                            st.success("✅ Invoice updated!")
                            st.cache_data.clear(); st.rerun()

            else:
                if df_inv.empty:
                    st.info("No invoices to delete.")
                else:
                    inv_id = st.selectbox("Select Invoice to Delete", df_inv['invoice_id'].tolist(),
                                          format_func=lambda x: df_inv[df_inv['invoice_id']==x]['invoice_number'].values[0], key="inv_del_sel")
                    inv_num = df_inv[df_inv['invoice_id']==inv_id]['invoice_number'].values[0]
                    st.warning(f"⚠️ Delete invoice **{inv_num}**? Related payments will also be removed.")
                    if st.button("🗑️ Confirm Delete Invoice", type="primary"):
                        with get_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM payments WHERE invoice_id=%s", (inv_id,))
                                cur.execute("DELETE FROM invoices WHERE invoice_id=%s", (inv_id,))
                            conn.commit()
                        st.success(f"✅ Invoice '{inv_num}' deleted!")
                        st.cache_data.clear(); st.rerun()

        # ═══════════════════════ PAYMENTS TAB ═══════════════════════
        with tab4:
            df_pay = load_table("""
                SELECT p.payment_id, i.invoice_number, p.payment_amount,
                       p.payment_date::text, p.payment_method
                FROM payments p JOIN invoices i ON p.invoice_id=i.invoice_id ORDER BY p.payment_id
            """)
            st.dataframe(df_pay, use_container_width=True, hide_index=True)

            df_invs = load_table("SELECT invoice_id, invoice_number FROM invoices ORDER BY invoice_number")
            op = st.radio("Action", ["➕ Add Payment", "✏️ Edit Payment", "🗑️ Delete Payment"], horizontal=True, key="pay_op")
            methods = ["Bank Transfer","ACH","Check","Wire","Credit Card"]

            if op == "➕ Add Payment":
                with st.form("add_pay"):
                    st.subheader("Add New Payment")
                    inv_id  = st.selectbox("Invoice", df_invs['invoice_id'].tolist(),
                                           format_func=lambda x: df_invs[df_invs['invoice_id']==x]['invoice_number'].values[0])
                    amount  = st.number_input("Payment Amount ($)", min_value=0.0, step=100.0)
                    pay_date = st.date_input("Payment Date", value=date.today())
                    method  = st.selectbox("Payment Method", methods)
                    if st.form_submit_button("✅ Save Payment", type="primary"):
                        with get_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute("INSERT INTO payments (invoice_id,payment_amount,payment_date,payment_method) VALUES (%s,%s,%s,%s)",
                                            (inv_id,amount,pay_date,method))
                            conn.commit()
                        st.success("✅ Payment added!")
                        st.cache_data.clear(); st.rerun()

            elif op == "✏️ Edit Payment":
                if df_pay.empty:
                    st.info("No payments to edit.")
                else:
                    pay_id = st.selectbox("Select Payment", df_pay['payment_id'].tolist(),
                                          format_func=lambda x: f"#{x} – {df_pay[df_pay['payment_id']==x]['invoice_number'].values[0]}", key="pay_edit_sel")
                    row = df_pay[df_pay['payment_id']==pay_id].iloc[0]
                    with st.form("edit_pay"):
                        st.subheader(f"Editing Payment #{pay_id}")
                        inv_id  = st.selectbox("Invoice", df_invs['invoice_id'].tolist(),
                                               format_func=lambda x: df_invs[df_invs['invoice_id']==x]['invoice_number'].values[0])
                        amount  = st.number_input("Payment Amount ($)", value=float(row['payment_amount']), min_value=0.0, step=100.0)
                        pay_date = st.date_input("Payment Date", value=datetime.strptime(row['payment_date'], "%Y-%m-%d").date())
                        method  = st.selectbox("Payment Method", methods,
                                               index=methods.index(row['payment_method']) if row['payment_method'] in methods else 0)
                        if st.form_submit_button("💾 Update Payment", type="primary"):
                            with get_conn() as conn:
                                with conn.cursor() as cur:
                                    cur.execute("UPDATE payments SET invoice_id=%s,payment_amount=%s,payment_date=%s,payment_method=%s WHERE payment_id=%s",
                                                (inv_id,amount,pay_date,method,pay_id))
                                conn.commit()
                            st.success("✅ Payment updated!")
                            st.cache_data.clear(); st.rerun()

            else:
                if df_pay.empty:
                    st.info("No payments to delete.")
                else:
                    pay_id = st.selectbox("Select Payment to Delete", df_pay['payment_id'].tolist(),
                                          format_func=lambda x: f"#{x} – {df_pay[df_pay['payment_id']==x]['invoice_number'].values[0]}", key="pay_del_sel")
                    st.warning(f"⚠️ Delete payment **#{pay_id}**?")
                    if st.button("🗑️ Confirm Delete Payment", type="primary"):
                        with get_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute("DELETE FROM payments WHERE payment_id=%s", (pay_id,))
                            conn.commit()
                        st.success(f"✅ Payment #{pay_id} deleted!")
                        st.cache_data.clear(); st.rerun()

    except Exception as e:
        st.error(f"⚠️ Error: {str(e)}")
        st.info("Please check your database connection settings in Streamlit secrets.")

if __name__ == "__main__":
    main()
