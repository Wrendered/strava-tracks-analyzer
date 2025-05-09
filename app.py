"""
WingWizard - Strava Tracks Analyzer

Main entry point for the Streamlit application.
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
import os

# Configure logging
from config.settings import LOGGING_CONFIG, PAGE_CONFIG

logging.basicConfig(
    level=LOGGING_CONFIG["level"],
    format=LOGGING_CONFIG["format"],
    handlers=LOGGING_CONFIG["handlers"]
)
logger = logging.getLogger(__name__)

# Import page modules
from ui.pages.analysis import display_page as display_analysis_page
# We'll add other pages later as they are refactored

def main():
    """Main application entry point"""
    # Set page configuration
    st.set_page_config(
        layout=PAGE_CONFIG["layout"], 
        page_title=PAGE_CONFIG["page_title"],
        page_icon=PAGE_CONFIG["page_icon"],
        initial_sidebar_state=PAGE_CONFIG["initial_sidebar_state"],
        menu_items=PAGE_CONFIG["menu_items"]
    )
    
    # Custom CSS for modern styling with dark mode compatibility
    st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px 4px 0px 0px;
        padding: 5px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 104, 201, 0.1);
        border-bottom: 2px solid var(--primary-color, rgb(0, 104, 201));
    }
    div.block-container {
        padding-top: 1rem;
    }
    h1 {
        font-size: 2.5rem;
        color: var(--primary-color, #0068C9);
        margin-bottom: 0.5rem;
    }
    h2 {
        margin-top: 0.8rem;
        margin-bottom: 0.8rem;
    }
    .metric-value {
        color: var(--primary-color, #0068C9);
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.8rem;
        color: var(--text-color, #555);
    }
    /* Dark mode compatibility */
    @media (prefers-color-scheme: dark) {
        .highlight-container {
            background-color: rgba(0, 104, 201, 0.2) !important;
        }
        .card-metric {
            color: var(--primary-color, #4DA8FF) !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main title with emoji and creative name
    st.title("🪂 WingWizard")
    
    # Initialize session state for navigation and data persistence
    if 'page' not in st.session_state:
        st.session_state.page = "Track Analysis"
        
    # Create tabs-based navigation at the top of the page
    selected_tab = st.radio(
        "Navigation",
        ["📚 Guide", "📊 Track Analysis", "🔄 Gear Comparison"],
        horizontal=True,
        label_visibility="collapsed",
        index=1 if st.session_state.page == "Track Analysis" else (0 if st.session_state.page == "Guide" else 2)
    )
    
    # Update session state based on selected tab
    if selected_tab == "📊 Track Analysis":
        st.session_state.page = "Track Analysis"
    elif selected_tab == "🔄 Gear Comparison":
        st.session_state.page = "Gear Comparison"
    else:
        st.session_state.page = "Guide"
    
    # Display content based on the selected page
    if st.session_state.page == "Track Analysis":
        display_analysis_page()
    elif st.session_state.page == "Gear Comparison":
        st.write("Gear Comparison page is under refactoring...")
        # We'll add this back when it's refactored: gear_comparison()
    else:
        # Guide page
        st.write("Guide page is under refactoring...")
        # We'll add this back when it's refactored: display_guide()
    
    logger.info(f"App started - {st.session_state.page} page")

if __name__ == "__main__":
    main()