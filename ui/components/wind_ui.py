"""
Wind direction estimation UI components.

This module contains UI components for wind direction estimation and visualization.
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union

from core.segments import analyze_wind_angles
from core.wind.estimate import estimate_wind_direction
from core.wind.models import WindEstimate

logger = logging.getLogger(__name__)

def wind_direction_selector(
    current_wind: float,
    estimated_wind: Optional[float] = None,
    estimate_confidence: Optional[str] = None,
    on_change_callback: Optional[callable] = None
) -> float:
    """
    Creates a wind direction selector UI component with explanations.
    
    Args:
        current_wind: Current wind direction in degrees
        estimated_wind: Optional estimated wind direction (if available)
        estimate_confidence: Confidence level of estimate ("high", "medium", "low", "none")
        on_change_callback: Function to call when wind direction changes
    
    Returns:
        float: Selected wind direction in degrees
    """
    with st.container(border=True):
        st.markdown("### Wind Direction")
        st.markdown("""
        **Wind direction is where the wind is coming FROM:**
        
        0° (N): North ⬇️ | 90° (E): East ⬅️  
        180° (S): South ⬆️ | 270° (W): West ➡️
        """)
        
        # Add confidence indicator if available
        if estimated_wind is not None and estimate_confidence is not None:
            confidence_colors = {
                "high": "green",
                "medium": "blue",
                "low": "orange",
                "none": "gray"
            }
            confidence_emoji = {
                "high": "✅", 
                "medium": "✓", 
                "low": "⚠️", 
                "none": "❓"
            }
            
            color = confidence_colors.get(estimate_confidence, "gray")
            emoji = confidence_emoji.get(estimate_confidence, "❓")
            
            st.markdown(f"""
            <div style="padding: 5px 10px; background-color: rgba(0,0,0,0.05); border-radius: 5px; margin-bottom: 10px;">
                <span style="color: {color}; font-weight: bold;">{emoji} {estimate_confidence.title()} confidence</span> 
                in estimated wind direction of {estimated_wind:.1f}°
            </div>
            """, unsafe_allow_html=True)
        
        # Initialize the temporary wind direction in session state if not present
        if "temp_wind_direction" not in st.session_state:
            st.session_state.temp_wind_direction = round(current_wind) if current_wind is not None else 90
        
        # Wind direction slider that updates a temporary value without triggering recalculation
        user_wind_direction = st.slider(
            "Enter approximate wind direction", 
            min_value=0, 
            max_value=359, 
            value=st.session_state.temp_wind_direction,
            step=1,  # Allow 1-degree increments for fine-tuning
            key="wind_slider_value"
        )
        
        # Update the temporary value when slider changes
        st.session_state.temp_wind_direction = user_wind_direction
        
        # Also update the main wind_direction to the slider value immediately 
        # (but don't trigger recalculations until Apply is clicked)
        st.session_state.wind_direction = user_wind_direction
        
        # Add a button to explicitly apply the wind direction change
        if st.button("🔄 Apply Wind Direction", 
                   help="Recalculate all metrics with this wind direction",
                   key="apply_wind_btn",
                   type="primary"):
            # Call the callback only when Apply button is clicked
            if on_change_callback is not None:
                on_change_callback(user_wind_direction)
        
    return user_wind_direction

def reestimate_wind_button(
    stretches: pd.DataFrame, 
    current_wind: float,
    suspicious_angle_threshold: float = 20,
    on_success_callback: Optional[callable] = None
) -> Optional[WindEstimate]:
    """
    Add a wind re-estimation button that analyzes selected segments.
    
    Args:
        stretches: DataFrame with sailing segments to analyze
        current_wind: Current wind direction in degrees
        suspicious_angle_threshold: Angles less than this are considered suspicious
        on_success_callback: Function to call with new wind direction on success
        
    Returns:
        WindEstimate: The wind estimate result if successful, None otherwise
    """
    segment_count = len(stretches)
    
    # Add the re-estimation button
    if st.button("🧭 Re-analyze Wind Direction", 
               help="Refine wind direction based on selected segments", 
               key="reestimate_wind_btn", 
               use_container_width=True):
        
        if segment_count < 3:
            st.warning(f"⚠️ Need at least 3 segments to refine wind direction. You have {segment_count} selected.")
            return None
            
        # Analyze segments with current wind direction 
        analyzed_stretches = analyze_wind_angles(stretches.copy(), current_wind)
        
        # Use the unified wind estimation API
        wind_estimate = estimate_wind_direction(
            analyzed_stretches.copy(),
            current_wind,
            method="iterative",
            suspicious_angle_threshold=suspicious_angle_threshold
        )
        
        # If estimation was successful
        if not wind_estimate.user_provided:
            refined_wind = wind_estimate.direction
            
            # Store the estimate for reference
            st.session_state.estimated_wind = refined_wind
            st.session_state.wind_estimate = wind_estimate.to_dict()
            
            # Call the on_success callback
            if on_success_callback is not None:
                if on_success_callback(refined_wind):
                    # Show success message with confidence level
                    confidence_emoji = {
                        "high": "✅", 
                        "medium": "✓", 
                        "low": "⚠️", 
                        "none": "❓"
                    }[wind_estimate.confidence]
                    
                    st.success(f"{confidence_emoji} Wind direction refined to {refined_wind:.1f}° " + 
                             f"({wind_estimate.confidence} confidence) based on {segment_count} segments")
                    
                    # Show tack information if available
                    if wind_estimate.has_both_tacks:
                        st.info(f"Port angle: {wind_estimate.port_angle:.1f}°, " + 
                              f"Starboard angle: {wind_estimate.starboard_angle:.1f}° " + 
                              f"(Difference: {wind_estimate.tack_difference:.1f}°)")
                    
                    # Return the estimate
                    return wind_estimate
                else:
                    st.error("Failed to update calculations with refined wind direction")
            else:
                # No callback provided, just show the result
                st.info(f"Estimated wind direction: {refined_wind:.1f}° " + 
                      f"({wind_estimate.confidence} confidence)")
                return wind_estimate
        else:
            st.error("⚠️ Couldn't refine wind direction from selected segments")
    
    return None