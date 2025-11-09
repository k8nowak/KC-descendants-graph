"""
Streamlit web app for interactive KC descendance graph visualization.

This app allows users to:
- Upload a CSV file or paste a Google Sheets link
- Generate interactive HTML visualizations
- View full graphs or neighborhoods of specific KCs
"""

import streamlit as st
import pandas as pd
import re
import tempfile
import os
from io import StringIO
import requests

# Import visualization functions
from visualize_kc_graph_interactive import (
    visualize_descendance_graph_interactive,
    visualize_neighborhood_interactive
)
from visualize_kc_graph_with_neighborhood import (
    create_graph_from_csv,
    resolve_kc_identifier
)


def parse_google_sheets_url(url):
    """
    Parse a Google Sheets URL and convert it to CSV export URL.
    
    Handles formats like:
    - https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={GID}
    - https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit?usp=sharing#gid={GID}
    
    Returns:
        CSV export URL or None if parsing fails
    """
    # Extract sheet ID and GID from URL
    sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    gid_match = re.search(r'[#&]gid=([0-9]+)', url)
    
    if not sheet_id_match:
        return None
    
    sheet_id = sheet_id_match.group(1)
    gid = gid_match.group(1) if gid_match else '0'  # Default to first sheet
    
    # Construct CSV export URL
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return csv_url


def load_csv_from_url(url):
    """Load CSV data from a URL (Google Sheets export)."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return StringIO(response.text)
    except Exception as e:
        st.error(f"Error loading data from URL: {e}")
        return None


def load_csv_from_upload(uploaded_file):
    """Load CSV data from uploaded file."""
    return StringIO(uploaded_file.getvalue().decode('utf-8'))


def create_graph_from_csv_io(csv_io):
    """
    Create a graph from a CSV file-like object.
    Temporarily saves to file since create_graph_from_csv expects a file path.
    """
    # Read the CSV content
    csv_io.seek(0)
    content = csv_io.read()
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp_file:
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # Use the existing function
        G, id_to_number, _ = create_graph_from_csv(tmp_file_path)
        return G, id_to_number
    finally:
        # Clean up temp file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


def save_html_to_temp(html_content):
    """Save HTML content to a temporary file and return the path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
        tmp_file.write(html_content)
        return tmp_file.name


# Page configuration
st.set_page_config(
    page_title="KC Descendance Graph Visualizer",
    page_icon="📊",
    layout="wide"
)

st.title("📊 KC Descendance Graph Visualizer")
st.markdown("Create interactive visualizations of Knowledge Component relationships")

# Sidebar for input
st.sidebar.header("📥 Data Input")

input_method = st.sidebar.radio(
    "Choose input method:",
    ["Google Sheets Link", "Upload CSV File"]
)

csv_data = None
csv_io = None

if input_method == "Google Sheets Link":
    st.sidebar.markdown("### Google Sheets")
    st.sidebar.markdown("**Note:** The sheet must be publicly accessible (anyone with the link can view).")
    
    sheets_url = st.sidebar.text_input(
        "Paste Google Sheets link:",
        placeholder="https://docs.google.com/spreadsheets/d/...",
        help="Make sure the sheet is set to 'Anyone with the link can view'"
    )
    
    # Check if URL has a specific tab (gid) specified
    gid_in_url = None
    if sheets_url:
        gid_match = re.search(r'[#&]gid=([0-9]+)', sheets_url)
        if gid_match:
            gid_in_url = gid_match.group(1)
    
    # Allow manual tab selection
    use_custom_tab = st.sidebar.checkbox(
        "Specify a different tab",
        value=False,
        help="If your sheet has multiple tabs and you want to use a different one"
    )
    
    custom_gid = None
    if use_custom_tab:
        custom_gid = st.sidebar.text_input(
            "Tab ID (gid):",
            value=gid_in_url if gid_in_url else "",
            placeholder="e.g., 0, 1234567890",
            help="Find the tab ID in the URL when viewing that tab (look for #gid=...)"
        )
    
    if sheets_url:
        # Parse URL and use custom gid if provided
        sheet_id_match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheets_url)
        if sheet_id_match:
            sheet_id = sheet_id_match.group(1)
            # Use custom gid if provided, otherwise use gid from URL, otherwise default to 0
            gid_to_use = custom_gid if (use_custom_tab and custom_gid) else (gid_in_url if gid_in_url else '0')
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_to_use}"
            
            # Show which tab is being used
            if gid_in_url or (use_custom_tab and custom_gid):
                st.sidebar.info(f"📑 Using tab with ID: {gid_to_use}")
            else:
                st.sidebar.info("📑 Using first tab (default). To use a different tab, check 'Specify a different tab' above.")
            
            with st.spinner("Loading data from Google Sheets..."):
                csv_io = load_csv_from_url(csv_url)
                if csv_io:
                    st.sidebar.success("✅ Data loaded successfully!")
        else:
            st.sidebar.error("❌ Invalid Google Sheets URL. Please check the format.")
else:
    st.sidebar.markdown("### CSV Upload")
    uploaded_file = st.sidebar.file_uploader(
        "Upload CSV file:",
        type=['csv'],
        help="Upload a CSV file with columns: ID, Number, Antecedents, Short Description"
    )
    
    if uploaded_file:
        csv_io = load_csv_from_upload(uploaded_file)
        if csv_io:
            st.sidebar.success("✅ File uploaded successfully!")

# Main content area
if csv_io:
    # Visualization options
    st.header("🎨 Visualization Options")
    
    viz_type = st.radio(
        "What would you like to visualize?",
        ["Full Graph", "Neighborhood of Specific KCs"],
        horizontal=True
    )
    
    kc_input = None
    if viz_type == "Neighborhood of Specific KCs":
        kc_input = st.text_input(
            "Enter KC numbers (comma-separated):",
            placeholder="e.g., 411, 701 or 1.1, 1.2",
            help="Enter one or more KC numbers separated by commas"
        )
    
    # Generate button
    if st.button("🚀 Generate Visualization", type="primary", use_container_width=True):
        with st.spinner("Creating graph..."):
            try:
                # Create graph from CSV
                G, id_to_number = create_graph_from_csv_io(csv_io)
                number_to_id = {v: k for k, v in id_to_number.items()}
                
                # Create temporary file for HTML output
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_html:
                    html_file_path = tmp_html.name
                
                if viz_type == "Full Graph":
                    # Generate full graph
                    visualize_descendance_graph_interactive(
                        G,
                        output_file=html_file_path,
                        title='Descendance Graph: KC Relationships'
                    )
                    
                    st.success("✅ Full graph generated successfully!")
                    
                else:
                    # Generate neighborhood
                    if not kc_input or not kc_input.strip():
                        st.error("❌ Please enter at least one KC number for neighborhood visualization.")
                    else:
                        # Parse KC identifiers
                        kc_identifiers = [kc.strip() for kc in kc_input.split(',')]
                        
                        # Generate filename based on KC numbers
                        resolved_ids = []
                        for identifier in kc_identifiers:
                            node_id = resolve_kc_identifier(identifier, number_to_id, id_to_number)
                            if node_id:
                                resolved_ids.append(id_to_number.get(node_id, node_id))
                        
                        if not resolved_ids:
                            st.error("❌ No valid KCs found. Please check your KC numbers.")
                        else:
                            visualize_neighborhood_interactive(
                                G, kc_identifiers, id_to_number, number_to_id,
                                output_file=html_file_path
                            )
                            
                            st.success(f"✅ Neighborhood visualization generated for KCs: {', '.join(resolved_ids)}")
                
                # Read the generated HTML
                if os.path.exists(html_file_path):
                    with open(html_file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Display in Streamlit
                    st.header("📊 Interactive Visualization")
                    st.markdown("**Drag nodes to reposition them • Zoom with mouse wheel • Hover to see descriptions**")
                    
                    # Use Streamlit's HTML component to display the visualization
                    import streamlit.components.v1 as components
                    components.html(html_content, height=800, scrolling=True)
                    
                    # Download button
                    st.download_button(
                        label="📥 Download HTML File",
                        data=html_content,
                        file_name=os.path.basename(html_file_path),
                        mime="text/html",
                        use_container_width=True
                    )
                    
                    # Clean up temp file
                    os.unlink(html_file_path)
                    
            except Exception as e:
                st.error(f"❌ Error generating visualization: {e}")
                st.exception(e)
else:
    st.info("👈 Please provide data using the sidebar options above.")
    
    # Show example
    with st.expander("📖 How to use this tool"):
        st.markdown("""
        ### Step 1: Provide Data
        - **Google Sheets**: Paste a link to a public Google Sheet
          - If your sheet has multiple tabs, the app will use the tab you're viewing (if the URL includes `#gid=...`)
          - Otherwise, it defaults to the first tab
          - To use a different tab: check "Specify a different tab" and enter the tab ID (found in the URL when viewing that tab)
        - **CSV Upload**: Upload a CSV file directly
        
        ### Step 2: Choose Visualization
        - **Full Graph**: Shows all KCs and their relationships
        - **Neighborhood**: Shows only specific KCs and their connections
        
        ### Step 3: Generate
        - Click "Generate Visualization" to create the interactive graph
        - The graph will appear below and can be downloaded
        
        ### CSV Format
        Your CSV should have these columns:
        - `ID`: Unique identifier for each KC
        - `Number`: Display number (e.g., "411", "1.1")
        - `Antecedents`: Comma-separated list of antecedent KC IDs
        - `Short Description`: Description text (optional, shown on hover)
        
        ### Multiple Tabs in Google Sheets
        If your Google Sheet has multiple tabs:
        1. Click on the tab you want to use in Google Sheets
        2. Copy the URL (it will include `#gid=1234567890` where the number is the tab ID)
        3. Paste that URL - the app will automatically use that tab
        4. Or manually enter the tab ID using the "Specify a different tab" option
        """)

