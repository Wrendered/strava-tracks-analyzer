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

def plot_comparison_radar(gear_items: Dict[str, GearItem], selected_items: List[str]) -> plt.Figure:
    """Create a radar plot comparing selected gear items.
    
    Args:
        gear_items: Dictionary of all gear items
        selected_items: List of selected gear item IDs
        
    Returns:
        plt.Figure: Matplotlib figure with the radar plot
    """
    if not selected_items or len(selected_items) == 0:
        return None
    
    # Filter to only selected items
    items = [gear_items[item_id] for item_id in selected_items if item_id in gear_items]
    
    # Define the metrics to compare
    metrics = [
        ('avg_speed', 'Avg Speed (kn)'),
        ('upwind_progress_speed', 'Upwind Progress (kn)'),
        ('best_port_upwind_angle', 'Best Port Angle (°)'),
        ('best_starboard_upwind_angle', 'Best Starboard Angle (°)'),
        ('best_port_upwind_speed', 'Port Upwind Speed (kn)'),
        ('best_starboard_upwind_speed', 'Starboard Upwind Speed (kn)')
    ]
    
    # Set up the plot
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, polar=True)
    
    # Number of metrics
    num_metrics = len(metrics)
    
    # Set up the angles for the radar plot (equally spaced)
    angles = np.linspace(0, 2*np.pi, num_metrics, endpoint=False).tolist()
    # Make it a full circle
    angles += angles[:1]
    
    # Set up the axis labels
    metric_labels = [m[1] for m in metrics]
    
    # Reverse angle metrics (lower is better)
    angle_metrics = ['best_port_upwind_angle', 'best_starboard_upwind_angle']
    
    # Colors for different items
    colors = plt.cm.tab10(np.linspace(0, 1, len(items)))
    
    # Plot each item
    for i, item in enumerate(items):
        # Get the values
        values = []
        all_values = []  # To determine axis scale
        
        for j, (metric_key, _) in enumerate(metrics):
            value = getattr(item, metric_key)
            
            # Skip if value is None
            if value is None:
                values.append(0)
                continue
                
            # For angle metrics, lower is better, so invert
            if metric_key in angle_metrics:
                # We'll actually invert the scale later
                values.append(value)
            else:
                values.append(value)
                
            all_values.append(value)
        
        # Make the plot circular
        values += values[:1]
        
        # Plot the values
        ax.plot(angles, values, color=colors[i], linewidth=2, label=item.title)
        ax.fill(angles, values, color=colors[i], alpha=0.1)
    
    # Set the labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metric_labels)
    
    # Add legend
    ax.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    
    # Additional styling
    plt.grid(True)
    plt.tight_layout()
    
    return fig

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
        <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin-top: 20px;">
            <h3>How to Add Gear to Compare:</h3>
            <ol>
                <li>Go to the <strong>Track Analysis</strong> tab</li>
                <li>Upload and analyze a GPX track</li>
                <li>Click the <strong>Export to Comparison</strong> button</li>
                <li>Give your setup a descriptive title</li>
                <li>Return to this page to see your saved gear</li>
            </ol>
            <p style="margin-top: 15px; font-style: italic; color: #666;">
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
        # Show radar chart comparing key metrics
        st.markdown("### 📡 Performance Radar")
        
        fig = plot_comparison_radar(gear_items, selected_items)
        if fig:
            st.pyplot(fig)
            
            st.caption("""
            **Note on radar chart:**
            - For angles (port and starboard), smaller values are better (closer to wind)
            - For speeds, larger values are better
            """)
        else:
            st.info("Not enough data to create radar chart.")
        
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