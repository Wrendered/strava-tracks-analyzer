"""
Foil Lab - Wingfoil GPX Track Analyzer

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
from ui.pages.gear_comparison import display_page as display_gear_comparison_page

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
    
    # Main title with emoji and updated name
    st.title("🪂 Foil Lab")
    
    # Shorter introduction banner 
    st.markdown("""
    <div style="padding: 10px; background-color: rgba(0, 104, 201, 0.07); border-radius: 8px; margin-bottom: 15px;">
        <p style="margin: 0; font-size: 0.95rem;">
            A prototype built in my spare time to analyze upwind performance from your GPX tracks. 
            Expect quirks, breakage, and the occasional bug — and please send feedback to my Instagram: 
            <a href="https://www.instagram.com/heart_wrench/" target="_blank" style="font-weight: 500;">@heart_wrench</a>. 
            Sharing because I love this sport and data too much to keep it to myself.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state for navigation and data persistence
    if 'page' not in st.session_state:
        st.session_state.page = "Track Analysis"
        
    # Create tabs-based navigation at the top of the page
    selected_tab = st.radio(
        "Navigation",
        ["📚 About", "📊 Track Analysis", "🔄 Gear Comparison"],
        horizontal=True,
        label_visibility="collapsed",
        index=1 if st.session_state.page == "Track Analysis" else (0 if st.session_state.page == "About" else 2)
    )
    
    # Update session state based on selected tab
    if selected_tab == "📊 Track Analysis":
        st.session_state.page = "Track Analysis"
    elif selected_tab == "🔄 Gear Comparison":
        st.session_state.page = "Gear Comparison"
    else:
        st.session_state.page = "About"
    
    # Display content based on the selected page
    if st.session_state.page == "Track Analysis":
        display_analysis_page()
    elif st.session_state.page == "Gear Comparison":
        display_gear_comparison_page()
    else:
        # About page with instructions and features
        st.header("📚 About Foil Lab")
        
        # About section with longer explanation
        st.markdown("""
        <div style="padding: 15px; background-color: rgba(0, 104, 201, 0.07); border-radius: 8px; margin-bottom: 25px;">
            <p style="font-size: 1.1rem; line-height: 1.5;">
                Foil Lab is a side project I made to help understand how different gear, wind conditions, and technique affect upwind performance. 
                You can upload GPX tracks (like from Strava), and the tool will give you a breakdown of wind angles, tack symmetry, and more.
            </p>
            <p style="font-size: 1.1rem; line-height: 1.5; margin-top: 15px;">
                It's not perfect — just a prototype I built in my spare time out of curiosity and obsession. 
                You might find bugs or quirks (you definitely will). But if you do, or if you have ideas for improvement, 
                I'd love to hear from you. Message me on Instagram: 
                <a href="https://www.instagram.com/heart_wrench/" target="_blank">@heart_wrench</a>.
            </p>
            <p style="font-size: 1.1rem; line-height: 1.5; margin-top: 15px;">
                This isn't a commercial project. It's a tool I wish existed, so I built it — and I'm sharing it in the spirit of 
                learning, improvement, and foil-nerdery. 💨
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Step-by-step guide with visual formatting
        st.markdown("""
        <div style="padding: 0 10px;">
            <h3>Getting Started</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Step 1
        col1, col2 = st.columns([1, 8])
        with col1:
            st.markdown('<div style="background-color: #0068C9; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold;">1</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<strong style="font-size: 1.1rem;">Export Your GPS Track</strong>', unsafe_allow_html=True)
            st.write("Download your activity as a GPX file from Strava or your GPS device.")
            st.caption("In Strava: Open an activity → Click the \"...\" button → Select \"Export GPX\"")
        
        # Step 2
        col1, col2 = st.columns([1, 8])
        with col1:
            st.markdown('<div style="background-color: #0068C9; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold;">2</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<strong style="font-size: 1.1rem;">Upload to Foil Lab</strong>', unsafe_allow_html=True)
            st.write("Go to the Track Analysis tab and upload your GPX file.")
            st.caption("Enter your best estimate of the wind direction during your session.")
        
        # Step 3
        col1, col2 = st.columns([1, 8])
        with col1:
            st.markdown('<div style="background-color: #0068C9; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold;">3</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<strong style="font-size: 1.1rem;">Analyze Your Performance</strong>', unsafe_allow_html=True)
            st.write("Review your tracks, sailing angles, and performance data.")
            st.caption("The polar plot shows your speed at different angles to the wind.")
        
        # Step 4
        col1, col2 = st.columns([1, 8])
        with col1:
            st.markdown('<div style="background-color: #0068C9; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold;">4</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<strong style="font-size: 1.1rem;">Fine-tune Wind Direction</strong>', unsafe_allow_html=True)
            st.write("Adjust the wind direction if needed to match your actual session conditions.")
            st.caption("The app will calculate a session average wind direction based on your sailing patterns.")
        
        # Step 5 - New step for gear comparison
        col1, col2 = st.columns([1, 8])
        with col1:
            st.markdown('<div style="background-color: #0068C9; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-weight: bold;">5</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<strong style="font-size: 1.1rem;">Compare Different Gear Setups</strong>', unsafe_allow_html=True)
            st.write("Export your analyzed tracks to the Gear Comparison page.")
            st.caption("Compare multiple tracks to see how different equipment performs in various conditions.")
        
        # Current Features
        st.markdown("<h3>Current Features</h3>", unsafe_allow_html=True)
        
        features = [
            ("Track Visualization", "See your route with color-coded speed segments"),
            ("Segment Analysis", "Break down your session into consistent sailing segments"),
            ("Wind Direction Estimation", "Calculate the average wind direction from your sailing patterns"),
            ("Polar Performance Plot", "Visualize your speed at different angles to the wind"),
            ("Upwind/Downwind Analysis", "See your best angles and speeds on each tack"),
            ("Performance Metrics", "Get insights on your sailing efficiency"),
            ("Gear Comparison", "Compare performance across different equipment setups")
        ]
        
        for feature, description in features:
            st.markdown(f"* **{feature}** - {description}")
        
        # Upcoming Features
        st.markdown("""
        <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-radius: 8px;">
            <h3>Upcoming Features</h3>
            <p>These features are in development and coming soon:</p>
            <ul>
                <li><strong>Progress Tracking</strong> - Monitor your improvement over time</li>
                <li><strong>Automated Insights</strong> - Get personalized tips based on your sailing patterns</li>
                <li><strong>Session Highlights</strong> - Identify your fastest runs and best maneuvers</li>
            </ul>
            <p style="font-size: 0.9rem; font-style: italic; margin-top: 10px;">
                Have a feature you'd like to see? Contact me on Instagram <a href="https://www.instagram.com/heart_wrench/" target="_blank">@heart_wrench</a>!
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    logger.info(f"App started - {st.session_state.page} page")

if __name__ == "__main__":
    main()