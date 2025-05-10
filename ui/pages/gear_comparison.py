"""
Gear comparison page for the Foil Lab app.

This module contains the UI for comparing gear performance.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
from typing import Dict, List, Optional, Any, Tuple
import math

from core.models.gear_item import GearItem

logger = logging.getLogger(__name__)

# No need for the radar chart function anymore

def display_page():
    """Display the gear comparison page."""
    st.header("🔄 Gear Comparison")
    st.markdown("""
    <div style="margin-bottom: 1rem;">
        <p style="margin: 0; font-size: 1.1rem; color: var(--text-color, #555);">
        Compare performance across different gear setups to optimize your equipment choices for various conditions.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize the session state for gear comparison items if not exists
    if 'gear_items' not in st.session_state:
        st.session_state.gear_items = {}
    
    # Get the gear items
    gear_items = st.session_state.gear_items
    
    # Check if we have any gear items
    if not gear_items:
        st.info("No gear items to compare yet. Export some data from the Track Analysis page.")
        
        # Add some more detailed instructions
        st.markdown("""
        <div style="padding: 20px; background-color: var(--secondary-background-color, #f8f9fa); color: var(--text-color, #262730); border-radius: 8px; margin-top: 20px;">
            <h3>How to Add Gear to Compare:</h3>
            <ol>
                <li>Go to the <strong>Track Analysis</strong> tab</li>
                <li>Upload and analyze a GPX track</li>
                <li>Click the <strong>Export to Comparison</strong> button</li>
                <li>Give your setup a descriptive title</li>
                <li>Return to this page to see your saved gear</li>
            </ol>
            <p style="margin-top: 15px; font-style: italic; color: var(--text-color, #666);">
                The comparison feature allows you to compare different wing, foil, and board combinations
                to see which performs best in different conditions.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        return
    
    # Add gear management options
    with st.container(border=True):
        st.markdown("### 🛠️ Gear Management")
        
        # Display the number of gear items
        st.markdown(f"<div style='font-size: 0.9rem;'>You have <strong>{len(gear_items)}</strong> gear setups saved for comparison.</div>", unsafe_allow_html=True)
        
        # Add option to clear all gear items
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Clear All Setups", type="secondary"):
                # Show confirmation
                st.session_state.confirm_clear = True
        
        with col2:
            if st.session_state.get('confirm_clear', False):
                st.warning("This will delete all saved gear data. Are you sure?")
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if st.button("Yes, Clear All", type="primary"):
                        st.session_state.gear_items = {}
                        st.session_state.confirm_clear = False
                        st.rerun()
                
                with col_b:
                    if st.button("Cancel", type="secondary"):
                        st.session_state.confirm_clear = False
                        st.rerun()
    
    # Display the gear items
    st.markdown("### 📊 Gear Comparison")
    
    # Select which items to compare
    selected_items = []
    
    # Create a dataframe for selection
    gear_df = pd.DataFrame([
        {
            'id': item_id,
            'title': item.title,
            'date': item.date if item.date else 'Unknown',
            'avg_speed': f"{item.avg_speed:.1f} kn" if item.avg_speed else 'N/A',
            'wind_direction': f"{item.wind_direction:.1f}°" if item.wind_direction else 'N/A',
            'upwind_angle': f"{item.avg_upwind_angle:.1f}°" if item.avg_upwind_angle else 'N/A'
        }
        for item_id, item in gear_items.items()
    ])
    
    if not gear_df.empty:
        # Use checkboxes for selection
        with st.container(border=True):
            st.markdown("#### Select Setups to Compare")
            st.markdown("Choose the gear setups you want to compare side by side.")
            
            # Create 3 columns for selection to fit more on screen
            cols = st.columns(3)
            
            for i, (index, row) in enumerate(gear_df.iterrows()):
                col_idx = i % 3  # Distribute across 3 columns
                with cols[col_idx]:
                    if st.checkbox(f"{row['title']}", value=True, key=f"select_{row['id']}"):
                        selected_items.append(row['id'])
    
    # If we have selected items, display the comparison
    if selected_items:
        # Show a simple tabular comparison
        st.markdown("### 📊 Performance Comparison")
        
        # Create a summary table of key metrics
        comparison_data = []
        
        # Define the metrics we want to compare
        metrics = [
            ('avg_speed', 'Avg Speed (kn)'),
            ('upwind_progress_speed', 'Upwind Progress (kn)'),
            ('best_port_upwind_angle', 'Best Port Upwind (°)'),
            ('best_starboard_upwind_angle', 'Best Starboard Upwind (°)'),
            ('best_port_upwind_speed', 'Port Upwind Speed (kn)'),
            ('best_starboard_upwind_speed', 'Starboard Upwind Speed (kn)')
        ]
        
        # Get data for all selected items
        for item_id in selected_items:
            if item_id in gear_items:
                item = gear_items[item_id]
                item_data = {'Title': item.title}
                
                # Add each metric
                for metric_key, metric_name in metrics:
                    value = getattr(item, metric_key)
                    if value is not None:
                        if 'angle' in metric_key:
                            item_data[metric_name] = f"{value:.1f}°"
                        else:
                            item_data[metric_name] = f"{value:.1f}"
                    else:
                        item_data[metric_name] = "N/A"
                        
                comparison_data.append(item_data)
        
        # Display as a DataFrame if we have data
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True)
            
            st.info("""
            **Note on metrics:**
            - For angles (port and starboard), smaller values are better (closer to wind)
            - For speeds, larger values are better
            """)
        else:
            st.info("No data available for comparison.")
        
        # Show detailed comparison table
        st.markdown("### 📋 Detailed Comparison")
        
        # Create a detailed comparison table
        detail_cols = st.columns(len(selected_items))
        
        for i, item_id in enumerate(selected_items):
            if item_id in gear_items:
                item = gear_items[item_id]
                
                with detail_cols[i]:
                    st.markdown(f"#### {item.title}")
                    
                    # Create a more visual comparison with metrics
                    with st.container(border=True):
                        # Basic info
                        st.markdown(f"**📅 Date:** {item.date if item.date else 'Unknown'}")
                        st.markdown(f"**🧭 Wind:** {item.wind_direction:.1f}°" if item.wind_direction else "**🧭 Wind:** N/A")
                        
                        # Performance metrics
                        st.markdown("---")
                        st.markdown("##### Performance Metrics")
                        
                        # Speed metrics
                        if item.avg_speed:
                            st.metric("Avg Speed", f"{item.avg_speed:.1f} kn")
                        
                        if item.upwind_progress_speed:
                            st.metric("Upwind Progress", f"{item.upwind_progress_speed:.1f} kn")
                        
                        # Angle metrics
                        st.markdown("---")
                        st.markdown("##### Upwind Angles")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if item.best_port_upwind_angle:
                                st.metric("Port", f"{item.best_port_upwind_angle:.1f}°")
                        
                        with col2:
                            if item.best_starboard_upwind_angle:
                                st.metric("Starboard", f"{item.best_starboard_upwind_angle:.1f}°")
                        
                        # Upwind speed metrics
                        st.markdown("---")
                        st.markdown("##### Upwind Speeds")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if item.best_port_upwind_speed:
                                st.metric("Port", f"{item.best_port_upwind_speed:.1f} kn")
                        
                        with col2:
                            if item.best_starboard_upwind_speed:
                                st.metric("Starboard", f"{item.best_starboard_upwind_speed:.1f} kn")
                        
                        # Tack symmetry
                        if item.port_starboard_diff is not None:
                            st.markdown("---")
                            st.markdown("##### Tack Symmetry")
                            st.metric("Port-Starboard Difference", f"{item.port_starboard_diff:.1f}°")
        
        # Download option
        st.markdown("### 💾 Export Data")
        
        # Create a dataframe with all the data for download
        export_data = []
        
        for item_id in selected_items:
            if item_id in gear_items:
                item = gear_items[item_id]
                export_data.append(item.to_dict())
        
        if export_data:
            export_df = pd.DataFrame(export_data)
            
            # Convert to CSV
            csv = export_df.to_csv(index=False)
            
            # Create a download button
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name="foil_lab_gear_comparison.csv",
                mime="text/csv",
                help="Download the comparison data as a CSV file"
            )
    else:
        st.info("Select at least one gear setup to compare.")