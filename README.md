# P2P Analytics Dashboard

A real-time Procure-to-Pay analytics dashboard built with **Streamlit** and **PostgreSQL (Neon)**.

![Dashboard Preview](preview.png)

## 🚀 Live Demo
[View Live Dashboard](https://your-app.streamlit.app)

## 📊 Features
- **Real-time KPI Cards**: Total PO, Invoice, Payment amounts + Approval rate
- **Interactive Charts**: Payment methods, Vendor spend, Invoice status
- **Auto-refresh**: Data updates every 60 seconds
- **Cloud-native**: PostgreSQL on Neon + Streamlit Cloud

## 🛠️ Tech Stack
- **Frontend**: Streamlit, Plotly
- **Backend**: Python, PostgreSQL
- **Database**: Neon (Serverless Postgres)
- **Hosting**: Streamlit Cloud (Free)

## 📁 Project Structure
```
p2p-analytics/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── .gitignore         # Git ignore rules
├── .streamlit/
│   └── secrets.toml   # Database credentials (local only)
└── README.md
```

## 🏃 Local Development

1. **Clone the repo**
   ```bash
   git clone https://github.com/yourusername/p2p-analytics.git
   cd p2p-analytics
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure secrets**
   Create `.streamlit/secrets.toml`:
   ```toml
   DATABASE_URL = "your-neon-connection-string"
   ```

4. **Run locally**
   ```bash
   streamlit run app.py
   ```

## ☁️ Deployment to Streamlit Cloud

1. Push code to GitHub (secrets.toml is gitignored)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Add secrets in Streamlit Cloud dashboard:
   - Click **Advanced settings** → **Secrets**
   - Add: `DATABASE_URL = "your-neon-connection-string"`
5. Deploy!

## 📈 Data Model

The dashboard analyzes 4 tables in the P2P process:

- **vendors**: Supplier information
- **purchase_orders**: PO details and amounts
- **invoices**: Invoice records with approval status
- **payments**: Payment transactions with methods

## 👤 Author
**Praneeth Reddy Ramaswamy**  
Senior Data Engineer | [LinkedIn](https://linkedin.com/in/yourprofile)

---
Built with ❤️ using Streamlit
