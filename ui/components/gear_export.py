"""Export UI component for gear comparison.

This module contains the UI component for exporting track data to gear comparison.
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any, Tuple

from core.models.gear_item import GearItem

logger = logging.getLogger(__name__)

def export_to_comparison_button(metrics: Dict[str, Any], stretches: pd.DataFrame) -> Optional[str]:
    """Add an export to comparison button.
    
    Args:
        metrics: Dictionary of track metrics
        stretches: DataFrame of sailing segments
        
    Returns:
        Optional[str]: The ID of the exported gear item if successful, None otherwise
    """
    # Initialize the session state for gear comparison items if not exists
    if 'gear_items' not in st.session_state:
        st.session_state.gear_items = {}
    
    # Check if we have metrics to export
    if not metrics:
        return None
    
    # Create a container for the export UI
    with st.container(border=True):
        st.markdown("""
        <div style="font-size: 0.9rem;">
            Export this track's data to the Gear Comparison page to compare with other sessions.
        </div>
        """, unsafe_allow_html=True)
        
        # Check if the current track has already been exported
        current_file = st.session_state.get('current_file_name')
        existing_item = None
        
        if current_file:
            for item_id, item in st.session_state.gear_items.items():
                if item.source_file == current_file:
                    existing_item = item
                    break
        
        # Show existing export info or the export form
        if existing_item:
            st.info(f"✅ This track has already been exported as: **{existing_item.title}**")
            
            # Add option to update the existing export
            if st.button("Update Export", key="update_gear_export"):
                # Remove the existing item
                del st.session_state.gear_items[existing_item.id]
                # Re-display the export form
                st.rerun()
        else:
            # Title input for the export
            with st.form(key="export_gear_form"):
                # Add description of what info we're exporting
                st.markdown("""
                <div style="font-size: 0.9rem; margin-bottom: 10px;">
                    <strong>What we'll export:</strong> Summary metrics, performance data, and wind angles.
                </div>
                """, unsafe_allow_html=True)
                
                # Get a title for the export
                default_title = f"{st.session_state.get('track_name', 'Track')} - {metrics.get('date', 'Unknown date')}"
                title = st.text_input(
                    "Title for this setup", 
                    value=default_title,
                    help="Give this setup a descriptive name like 'Rocket 3m - 17 knots' or 'A-Wing 4.2m - 15 knots'"
                )
                
                # Submit button
                submitted = st.form_submit_button("Export to Comparison", type="primary")
                
                # Process form submission
                if submitted:
                    if not title.strip():
                        st.error("Please enter a title for this setup.")
                        return None
                    
                    try:
                        # Create a GearItem from the current session state
                        gear_item = GearItem.from_session_state(title, st.session_state)
                        
                        # Store in session state
                        st.session_state.gear_items[gear_item.id] = gear_item
                        
                        logger.info(f"Exported gear item: {title} (ID: {gear_item.id})")
                        st.success(f"✅ Successfully exported '{title}' to Gear Comparison!")
                        
                        # Return the item ID
                        return gear_item.id
                    except Exception as e:
                        logger.error(f"Error exporting gear item: {e}")
                        st.error(f"Error exporting to comparison: {e}")
            
    return None
