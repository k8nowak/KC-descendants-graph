# Deployment Guide for KC Descendance Graph Visualizer

This guide explains how to deploy the Streamlit web app for easy access by non-technical users.

## Option 1: Streamlit Cloud (Recommended - Easiest)

Streamlit Cloud offers free hosting for Streamlit apps. This is the easiest option for zero-install access.

### Steps:

1. **Push your code to GitHub**
   - Create a GitHub repository
   - Push all files (including `streamlit_app.py`, `visualize_kc_graph_interactive.py`, `visualize_kc_graph_with_neighborhood.py`, and `requirements.txt`)

2. **Deploy to Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account
   - Click "New app"
   - Select your repository
   - Set main file path to: `streamlit_app.py`
   - Click "Deploy"

3. **Share the URL**
   - Streamlit Cloud will provide a URL like: `https://your-app-name.streamlit.app`
   - Share this URL with your colleague - they can access it from any browser!

### Benefits:
- ✅ Zero installation for users
- ✅ Always accessible via URL
- ✅ Automatic updates when you push to GitHub
- ✅ Free tier available

---

## Option 2: Run Locally (For Testing)

If you want to test the app locally before deploying:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   streamlit run streamlit_app.py
   ```

3. **Access in browser:**
   - The app will open automatically at `http://localhost:8501`
   - Or manually navigate to that URL

---

## Option 3: Self-Hosted Server

If you have a server available, you can run Streamlit there:

1. Install Python and dependencies on the server
2. Run: `streamlit run streamlit_app.py --server.port 8501`
3. Configure firewall/port forwarding as needed
4. Access via server IP/domain

---

## Google Sheets Setup

For the Google Sheets link feature to work:

1. **Make the sheet public:**
   - Open your Google Sheet
   - Click "Share" button
   - Change access to "Anyone with the link can view"
   - Copy the shareable link

2. **Paste the link in the app:**
   - The app will automatically convert it to CSV format
   - No need to export manually!

---

## Troubleshooting

### "Error loading data from URL"
- Make sure the Google Sheet is set to "Anyone with the link can view"
- Check that the URL is a valid Google Sheets link

### "No valid KCs found"
- Check that your CSV has the required columns: `ID`, `Number`, `Antecedents`
- Verify KC numbers match what's in your data

### App won't start
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check that Python 3.8+ is installed

---

## File Structure

Make sure these files are in your repository:
```
├── streamlit_app.py                    # Main Streamlit app
├── visualize_kc_graph_interactive.py   # Interactive visualization functions
├── visualize_kc_graph_with_neighborhood.py  # Graph creation functions
└── requirements.txt                    # Python dependencies
```

---

## Support

For issues or questions, check:
- Streamlit documentation: https://docs.streamlit.io
- Streamlit Cloud: https://streamlit.io/cloud

