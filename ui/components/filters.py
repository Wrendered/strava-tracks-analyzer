"""
Filter components for the WingWizard app.

This module contains UI components for filtering and selecting segments.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any

def segment_selection_bar(
    display_df: pd.DataFrame,
    suspicious_angle_threshold: float = 20.0
) -> Tuple[List[int], Dict[str, bool]]:
    """
    Create a horizontal segment selection bar with filter options.
    
    Args:
        display_df: DataFrame with segment data for display
        suspicious_angle_threshold: Threshold for suspicious angles
        
    Returns:
        tuple: (selected_segment_indices, filter_states)
    """
    # Set default filter state if not already set
    if 'filter_changes' not in st.session_state:
        st.session_state.filter_changes = {
            'upwind_selected': False,
            'downwind_selected': False,
            'suspicious_removed': True,  # Default to true
            'best_speed_selected': False
        }
    
    # Create a horizontal segment selection bar with filter status and wind re-estimation
    filter_container = st.container(border=True)
    
    top_row = filter_container.columns([1, 1, 2, 2, 1])
    # Left buttons
    with top_row[0]:
        if st.button("🔄 All", key="all_btn", help="Select all segments", use_container_width=True):
            st.session_state.filter_changes = {'upwind_selected': False, 'downwind_selected': False, 
                                          'suspicious_removed': False, 'best_speed_selected': False}
            selected_segments = display_df['original_index'].tolist()
            st.rerun()
    with top_row[1]:
        if st.button("❌ None", key="none_btn", help="Deselect all segments", use_container_width=True):
            st.session_state.filter_changes = {'upwind_selected': False, 'downwind_selected': False, 
                                          'suspicious_removed': False, 'best_speed_selected': False}
            selected_segments = []
            st.rerun()
    
    # Direction filter controls
    with top_row[2]:
        st.write("**Direction:**")
        dir_cols = st.columns(2)
        with dir_cols[0]:
            upwind = st.checkbox("⬆️ Upwind", value=st.session_state.filter_changes['upwind_selected'], key="upwind_check")
            st.session_state.filter_changes['upwind_selected'] = upwind
        with dir_cols[1]:
            downwind = st.checkbox("⬇️ Downwind", value=st.session_state.filter_changes['downwind_selected'], key="downwind_check")
            st.session_state.filter_changes['downwind_selected'] = downwind
    
    # Quality filter controls
    with top_row[3]:
        st.write("**Quality:**")
        qual_cols = st.columns(2)
        with qual_cols[0]:
            no_suspicious = st.checkbox("⚠️ No Suspicious", value=st.session_state.filter_changes['suspicious_removed'], key="suspicious_check")
            st.session_state.filter_changes['suspicious_removed'] = no_suspicious
        with qual_cols[1]:
            fastest = st.checkbox("⚡ Fastest Only", value=st.session_state.filter_changes['best_speed_selected'], key="speed_check")
            st.session_state.filter_changes['best_speed_selected'] = fastest
    
    # Apply button
    with top_row[4]:
        st.write("&nbsp;")  # Add some spacing
        apply_button = st.button("✅ Apply", type="primary", key="apply_filters", use_container_width=True, help="Apply filters & recalculate metrics")
    
    # Apply all filters together to get the correct selection
    all_segments = display_df['original_index'].tolist()
    filtered_segments = all_segments.copy()
    
    # Initialize filter text in this scope only
    filter_text = []
    
    # Apply direction filters if active
    if st.session_state.filter_changes['upwind_selected'] and not st.session_state.filter_changes['downwind_selected']:
        upwind_segments = display_df[display_df['upwind_downwind'] == 'Upwind']['original_index'].tolist()
        filtered_segments = [s for s in filtered_segments if s in upwind_segments]
        filter_text.append("Upwind only")
    elif st.session_state.filter_changes['downwind_selected'] and not st.session_state.filter_changes['upwind_selected']:
        downwind_segments = display_df[display_df['upwind_downwind'] == 'Downwind']['original_index'].tolist()
        filtered_segments = [s for s in filtered_segments if s in downwind_segments]
        filter_text.append("Downwind only")
    elif st.session_state.filter_changes['upwind_selected'] and st.session_state.filter_changes['downwind_selected']:
        filter_text.append("All directions")
    
    # Apply suspicious filter if active
    if st.session_state.filter_changes['suspicious_removed']:
        suspicious_segments = display_df[display_df['suspicious']]['original_index'].tolist()
        if suspicious_segments:
            filtered_segments = [s for s in filtered_segments if s not in suspicious_segments]
        filter_text.append("No suspicious angles")
    
    # Apply speed filter if active
    if st.session_state.filter_changes['best_speed_selected']:
        speed_threshold = display_df['speed (knots)'].quantile(0.75)
        fast_segments = display_df[display_df['speed (knots)'] >= speed_threshold]['original_index'].tolist()
        filtered_segments = [s for s in filtered_segments if s in fast_segments]
        filter_text.append(f"Fastest (>{speed_threshold:.1f} knots)")
    
    # Display filter status
    if filter_text:
        st.info(f"**Active filters:** {', '.join(filter_text)}")
    else:
        st.info("**No filters active** - showing all segments")
    
    return filtered_segments, st.session_state.filter_changes

def segment_details_table(display_df: pd.DataFrame, selected_segments: List[int]) -> None:
    """
    Display a table with segment details.
    
    Args:
        display_df: DataFrame with segment data for display
        selected_segments: List of selected segment indices
    """
    # Display segment data table in a compact format
    # Use only the selected segments for display
    if selected_segments and len(selected_segments) > 0:
        filtered_display_df = display_df[display_df['original_index'].isin(selected_segments)]
        source_note = f"Showing {len(filtered_display_df)} selected segments"
    else:
        filtered_display_df = display_df
        source_note = f"Showing all {len(display_df)} segments"
    
    # Caption
    st.caption(source_note)
    
    # Download buttons section
    cols = st.columns([1, 1])
    with cols[0]:
        # Compact download buttons
        csv = filtered_display_df.to_csv(index=False)
        st.download_button(
            "📥 Download Selected Segments (CSV)",
            data=csv,
            file_name="wingfoil_segments.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with cols[1]:
        # Full data export
        all_data_csv = display_df.to_csv(index=False)
        st.download_button(
            "📊 Download Complete Analysis",
            data=all_data_csv,
            file_name="wingfoil_full_analysis.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Show the filtered dataframe with improved formatting
    display_cols = [
        'segment_id', 'sailing_type', 'heading (°)', 
        'angle off wind (°)', 'speed (knots)', 
        'distance (m)', 'duration (sec)'
    ]
    
    if not filtered_display_df.empty:
        # Create suspicious indicator
        if 'suspicious' in filtered_display_df.columns:
            filtered_display_df['sailing_type'] = filtered_display_df.apply(
                lambda row: f"{row['sailing_type']} ⚠️" if row['suspicious'] else row['sailing_type'], 
                axis=1
            )
        
        st.dataframe(filtered_display_df[display_cols], use_container_width=True, height=200)
    else:
        st.warning("No segments selected. Please use the filters to select segments.")

def segment_selection_checkboxes(display_df: pd.DataFrame) -> List[int]:
    """
    Create advanced segment selection UI with individual checkboxes.
    
    Args:
        display_df: DataFrame with segment data for display
        
    Returns:
        list: Selected segment indices
    """
    # Initialize selected_segments with all original indices if not already set
    if ('selected_segments' not in st.session_state or 
        not isinstance(st.session_state.selected_segments, list)):
        # Default to all segments selected - use original indices
        st.session_state.selected_segments = display_df['original_index'].tolist()
    
    # Group by sailing type for better organization
    segment_types = display_df['sailing_type'].unique()
    
    for sailing_type in segment_types:
        st.write(f"**{sailing_type}:**")
        
        # Get segments of this type
        type_segments = display_df[display_df['sailing_type'] == sailing_type]
        
        # Show in 4 columns for more density
        check_cols = st.columns(4)
        
        # Distribute segments across columns
        segments_per_col = len(type_segments) // 4 + 1
        
        col_idx = 0
        segment_count = 0
        
        for i, row in type_segments.iterrows():
            segment_id = row['original_index']  # Use original index for selection
            angle = row['angle off wind (°)']
            speed = row['speed (knots)']
            is_suspicious = row['suspicious'] if 'suspicious' in row else False
            
            # Switch to next column if needed
            if segment_count >= segments_per_col:
                col_idx = (col_idx + 1) % 4
                segment_count = 0
            
            # Format the label based on whether it's suspicious - more compact
            label = f"#{int(row['segment_id'])}: {angle}°" + ("⚠️" if is_suspicious else "")
            
            # Create a checkbox for each segment in the appropriate column
            with check_cols[col_idx]:
                is_selected = st.checkbox(
                    label, 
                    value=segment_id in st.session_state.selected_segments,
                    key=f"segment_{segment_id}"
                )
                
                # Update selection
                if is_selected and segment_id not in st.session_state.selected_segments:
                    st.session_state.selected_segments.append(segment_id)
                elif not is_selected and segment_id in st.session_state.selected_segments:
                    st.session_state.selected_segments.remove(segment_id)
            
            segment_count += 1
    
    # Add a refresh button to apply segment selection changes
    apply_selection = st.button("✅ Apply Selection", 
                           key="apply_segment_selection", 
                           type="primary",
                           help="Apply your segment selection changes",
                           use_container_width=True)
    
    if apply_selection:
        st.rerun()
    
    return st.session_state.selected_segments