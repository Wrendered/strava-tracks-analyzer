"""
Wind Direction Override Component.

This component provides a clean, intuitive interface for users to manually override
the algorithmically estimated wind direction and see the impact on all calculations.

Architecture:
- Algorithm estimates wind direction from sailing patterns
- User can override this estimate with manual input
- All calculations (VMG, angles, performance metrics, visualizations) update
- Clear visual feedback shows when override is active vs algorithm estimate
- Simple reset function to return to algorithm estimate

State Management:
- wind_override_active: Boolean flag for override status
- wind_override_value: User's override wind direction
- wind_direction: Currently active wind direction (algorithm or override)
- algorithm_wind_direction: Stores original algorithm estimate for reference
"""

import streamlit as st
from typing import Optional, Callable


def render_wind_override_control(
    algorithm_wind: float,
    current_wind: float,
    on_override_callback: Callable[[float], None]
) -> None:
    """
    Render wind direction override control with clear visual feedback.
    
    Args:
        algorithm_wind: Wind direction estimated by the algorithm
        current_wind: Currently active wind direction (may be override or algorithm)
        on_override_callback: Function to call when user applies an override
    """
    st.subheader("💨 Wind Direction Control")
    
    # Check if override is currently active
    is_override_active = _is_wind_override_active()
    override_value = _get_wind_override_value()
    
    with st.container(border=True):
        # Status display
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Algorithm Estimate", 
                f"{algorithm_wind:.0f}°",
                delta="✓ Calculated" if not is_override_active else "Not used",
                delta_color="normal" if not is_override_active else "off"
            )
        
        with col2:
            if is_override_active:
                st.metric(
                    "Your Override", 
                    f"{override_value:.0f}°",
                    delta="⚠️ Active",
                    delta_color="inverse"
                )
            else:
                st.metric(
                    "Active Wind Direction", 
                    f"{current_wind:.0f}°",
                    delta="Using algorithm",
                    delta_color="normal"
                )
        
        # Override controls
        st.markdown("---")
        st.markdown("**Manual Override:**")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Get current slider value or initialize with algorithm wind
            current_slider_value = st.session_state.get('manual_wind_slider_value', int(algorithm_wind))
            
            override_input = st.slider(
                "Override Wind Direction (°)",
                min_value=0,
                max_value=359,
                value=current_slider_value,
                step=1,
                help="Drag to adjust wind direction, then click Apply",
                key="manual_wind_slider"
            )
        
        with col2:
            # Apply button
            apply_clicked = st.button(
                "🔄 Apply Override",
                type="primary",
                help="Recalculate all metrics with this wind direction",
                use_container_width=True
            )
        
        with col3:
            # Reset button (only show if override is active)
            reset_clicked = False
            if is_override_active:
                reset_clicked = st.button(
                    "↺ Reset",
                    help="Return to algorithm estimate",
                    use_container_width=True
                )
        
        # Handle user actions
        if apply_clicked:
            _apply_wind_override(override_input, on_override_callback)
        
        if reset_clicked:
            _reset_wind_override(algorithm_wind, on_override_callback)
        
        # Show helpful message
        if is_override_active:
            st.info(f"🎯 All calculations are using your override of {override_value:.0f}° instead of the algorithm estimate of {algorithm_wind:.0f}°")
        else:
            st.caption("💡 Adjust the slider and click Apply to override the algorithm's wind direction estimate")


def _is_wind_override_active() -> bool:
    """Check if a wind override is currently active."""
    return st.session_state.get('wind_override_active', False)


def _get_wind_override_value() -> Optional[float]:
    """Get the current wind override value."""
    return st.session_state.get('wind_override_value', None)


def _apply_wind_override(wind_direction: float, callback: Callable[[float], None]) -> None:
    """Apply a wind direction override."""
    # Store override state
    st.session_state.wind_override_active = True
    st.session_state.wind_override_value = wind_direction
    st.session_state.wind_direction = wind_direction  # Update active wind direction
    st.session_state.manual_wind_slider_value = int(wind_direction)  # Store slider value
    
    # Call the recalculation callback
    try:
        callback(wind_direction)
        st.success(f"✅ All calculations updated with wind direction {wind_direction:.0f}°")
    except Exception as e:
        st.error(f"Error applying wind override: {e}")


def _reset_wind_override(algorithm_wind: float, callback: Callable[[float], None]) -> None:
    """Reset to algorithm wind estimate."""
    # Clear override state
    st.session_state.wind_override_active = False
    st.session_state.wind_override_value = None
    st.session_state.wind_direction = algorithm_wind  # Restore algorithm wind
    st.session_state.manual_wind_slider_value = int(algorithm_wind)  # Reset slider value
    
    # Call the recalculation callback
    try:
        callback(algorithm_wind)
        st.success(f"✅ Reset to algorithm estimate: {algorithm_wind:.0f}°")
    except Exception as e:
        st.error(f"Error resetting wind direction: {e}")


def get_effective_wind_direction() -> float:
    """
    Get the effective wind direction (override if active, otherwise refined/current).
    
    This is a utility function for other components to determine which
    wind direction value to use in their calculations.
    
    Returns:
        float: The wind direction that should be used for calculations
    """
    if _is_wind_override_active():
        return _get_wind_override_value()
    else:
        # Use refined wind if available, otherwise current wind direction
        return st.session_state.get('refined_wind_direction', 
                                   st.session_state.get('wind_direction', 90.0))