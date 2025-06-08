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
import uuid

from core.models.gear_item import GearItem
from services.track_analysis_service import analyze_track_file, create_gear_item_from_analysis, get_analysis_parameters_from_session

logger = logging.getLogger(__name__)


def _render_bulk_upload_section():
    """Render bulk upload section for gear comparison."""
    with st.expander("📦 Bulk Upload Files for Comparison", expanded=False):
        st.markdown("""
        Upload multiple GPX files at once. Each file will be analyzed automatically with wind direction estimation.
        """)
        
        # Wind direction input for bulk upload
        col1, col2 = st.columns([1, 2])
        with col1:
            initial_wind = st.number_input(
                "Initial Wind Estimate (°)",
                min_value=0,
                max_value=359,
                value=90,
                step=5,
                help="Starting point for wind estimation. Algorithm will refine for each file.",
                key="bulk_wind_direction"
            )
        
        with col2:
            st.info("💡 The algorithm will automatically refine the wind direction for each file based on sailing patterns")
        
        # File uploader
        bulk_files = st.file_uploader(
            "Select GPX files",
            type=['gpx'],
            accept_multiple_files=True,
            help="Select multiple GPX files to analyze and compare",
            key="bulk_upload_comparison"
        )
        
        if bulk_files:
            if st.button(f"🚀 Process {len(bulk_files)} files", key="process_bulk_comparison"):
                _process_bulk_files(bulk_files, initial_wind)


def _process_bulk_files(files, initial_wind_direction):
    """Process multiple GPX files for comparison using the shared analysis service."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Get analysis parameters from session state - EXACTLY THE SAME AS MAIN PAGE
    analysis_params = get_analysis_parameters_from_session(st.session_state)
    
    successful = []
    failed = []
    
    for idx, file in enumerate(files):
        try:
            status_text.text(f"Processing {file.name}...")
            
            # Use the EXACT SAME analysis pipeline as the main page
            analysis_result = analyze_track_file(
                file=file,
                initial_wind_direction=initial_wind_direction,
                **analysis_params  # Use exact same parameters as main page
            )
            
            if not analysis_result.segments.empty:
                # Create gear item using the shared service
                gear_name = file.name.replace('.gpx', '')
                gear_item = create_gear_item_from_analysis(analysis_result, gear_name)
                
                # Add to session state
                if 'gear_items' not in st.session_state:
                    st.session_state.gear_items = {}
                
                st.session_state.gear_items[gear_name] = gear_item
                
                successful.append({
                    'file': file.name,
                    'segments': len(analysis_result.segments),
                    'upwind_segments': len(analysis_result.upwind_segments),
                    'initial_wind': initial_wind_direction,
                    'refined_wind': analysis_result.refined_wind,
                    'wind_change': analysis_result.refined_wind - initial_wind_direction,
                    'vmg': analysis_result.vmg_upwind,
                    'best_port_angle': analysis_result.best_port_angle,
                    'best_starboard_angle': analysis_result.best_starboard_angle
                })
            else:
                failed.append({'file': file.name, 'reason': 'No segments detected'})
                
        except Exception as e:
            logger.error(f"Error processing {file.name}: {e}")
            failed.append({'file': file.name, 'reason': str(e)})
        
        # Update progress
        progress_bar.progress((idx + 1) / len(files))
    
    # Clear progress indicators
    progress_bar.empty()
    status_text.empty()
    
    # Show results
    if successful:
        st.success(f"✅ Successfully processed {len(successful)} files")
        
        # Show detailed processing results
        st.markdown("**Processing Details:**")
        for result in successful:
            st.write(f"**{result['file']}**:")
            st.write(f"  • Wind: {result['initial_wind']}° → {result['refined_wind']:.1f}° "
                    f"(Δ{result['wind_change']:+.1f}°)")
            st.write(f"  • Segments: {result['segments']} total, {result['upwind_segments']} upwind")
            st.write(f"  • VMG: {result['vmg']:.1f}kn" if result['vmg'] else "  • VMG: N/A")
            if result['best_port_angle'] and result['best_starboard_angle']:
                st.write(f"  • Best angles: Port {result['best_port_angle']:.1f}°, Starboard {result['best_starboard_angle']:.1f}°")
            st.write("")
    
    if failed:
        st.warning(f"⚠️ Failed to process {len(failed)} files")
        st.markdown("**Failed Files:**")
        for fail in failed:
            st.error(f"• {fail['file']}: {fail['reason']}")
    
    # Refresh the page to show new items
    if successful:
        st.rerun()


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
    
    # Add bulk upload section first
    _render_bulk_upload_section()
    
    # Check if we have any gear items
    if not gear_items:
        st.info("No gear items to compare yet. Use bulk upload above or export from Track Analysis page.")
        
        # Add some more detailed instructions
        st.markdown("""
        <div style="padding: 20px; background-color: var(--secondary-background-color, #f8f9fa); color: var(--text-color, #262730); border-radius: 8px; margin-top: 20px;">
            <h3>Two Ways to Add Gear:</h3>
            <ol>
                <li><strong>Bulk Upload</strong>: Use the uploader above to process multiple files at once</li>
                <li><strong>Individual Analysis</strong>: Go to Track Analysis tab → Upload GPX → Click Export to Comparison</li>
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
        
        # Define the metrics we want to compare - matching main page display
        metrics = [
            ('avg_speed', 'Avg Speed (kn)'),
            ('wind_direction', 'Wind Dir (°)'),
            ('vmg_upwind', 'VMG Upwind (kn)'),  # Main page metric
            ('avg_upwind_angle', 'Avg Upwind Angle (°)'),  # Main page metric  
            ('best_port_upwind_angle', 'Best Port (°)'),
            ('best_starboard_upwind_angle', 'Best Starboard (°)')
            # Removed 'upwind_progress_speed' - deprecated legacy metric
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
                
                # Add computed "Best Upwind Angle" to match main page
                if item.best_port_upwind_angle is not None and item.best_starboard_upwind_angle is not None:
                    best_overall = min(item.best_port_upwind_angle, item.best_starboard_upwind_angle)
                    item_data['Best Upwind Angle (°)'] = f"{best_overall:.1f}°"
                elif item.best_port_upwind_angle is not None:
                    item_data['Best Upwind Angle (°)'] = f"{item.best_port_upwind_angle:.1f}°"
                elif item.best_starboard_upwind_angle is not None:
                    item_data['Best Upwind Angle (°)'] = f"{item.best_starboard_upwind_angle:.1f}°"
                else:
                    item_data['Best Upwind Angle (°)'] = "N/A"
                        
                comparison_data.append(item_data)
        
        # Display as a DataFrame if we have data
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True)
        else:
            st.info("No data available for comparison.")
        
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