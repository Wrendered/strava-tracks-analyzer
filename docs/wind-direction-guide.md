# Wind Direction Guide for Foil Lab

This guide explains how Foil Lab calculates and uses wind direction in your track analysis.

## Why Wind Direction Matters

Accurate wind direction is **critical** for wingfoil analysis because:

- It determines what angles you're sailing relative to the wind
- It affects the classification of upwind vs. downwind segments
- It's used to calculate your upwind pointing ability and downwind speed
- The polar diagram and all performance metrics depend on it

## How to Set Wind Direction

1. When you upload a track, use the slider in the Wind Direction panel
2. Enter your **approximate** wind direction from memory (where wind was coming FROM)
3. The app will refine this estimate based on your track data
4. You can always re-adjust using the slider and clicking "Apply Wind Direction"
5. You can also re-analyze selected segments with the "Re-analyze Wind Direction" button

## Cardinal Directions Reference

- **0° (N)**: Wind coming from North (blowing South) ⬇️
- **90° (E)**: Wind coming from East (blowing West) ⬅️
- **180° (S)**: Wind coming from South (blowing North) ⬆️
- **270° (W)**: Wind coming from West (blowing East) ➡️

## Understanding Confidence Levels

WingWizard shows confidence in wind direction estimates:

- **High Confidence (✅)**: Strong evidence based on multiple consistent segments
- **Medium Confidence (✓)**: Good evidence but with some variations
- **Low Confidence (⚠️)**: Limited evidence with inconsistencies
- **No Confidence (❓)**: Insufficient data, falling back to user-provided direction

## How Wind Direction Estimation Works

WingWizard uses a multi-stage algorithm to estimate wind direction:

1. **User-Guided Approach**: Starts with your provided wind direction
2. **Candidate Testing**: Tests various angles around your estimate
3. **Tack Analysis**: Analyzes your upwind tacks on port and starboard
4. **Segment Filtering**: Removes implausible angles and statistical outliers
5. **Weighted Bisector**: Calculates a balanced wind direction based on your best tacks

The algorithm specifically looks for:
- Balanced tack patterns between port and starboard
- Realistic upwind angles (typically 30-45°)
- Consistent sailing patterns across the session
- Statistical clustering of your bearings

## Sailing Angles Explained

Sailing angles are always measured relative to the wind direction:

- **0°**: Directly into the wind (impossible to sail)
- **30-50°**: Close-hauled (sailing as close to the wind as possible)
- **90°**: Beam reach (wind from the side)
- **120-150°**: Broad reach (wind from behind at an angle)
- **180°**: Running (wind directly behind)

## Tips for Accurate Analysis

- **Enter an approximate wind direction** even if you're not 100% sure
- **Remove suspicious segments** in the segment selection panel (those marked with ⚠️)
- **Use the re-analyze button** after selecting only your best, most consistent segments
- **Exclude erratic sections** from your track (like when launching or landing)
- **Expert tip:** If you know the exact wind direction from a weather report, enter it and the system will use it as a starting point

## Understanding the Results

After analysis, WingWizard will show:
- Your best upwind angles on port and starboard tacks
- Your speed at different angles to the wind in the polar plot
- The refined wind direction (if significantly different from your input)

Remember that wind direction is where the wind is coming FROM, not going to!

## Common Issues

- **Unrealistic pointing angles** (< 20°) usually indicate incorrect wind direction
- **Very asymmetric tacks** might mean the wind direction is off
- **Inconsistent results** could indicate shifting winds during your session
- **Too few segments** may not provide enough data for reliable wind estimation
- **Slider recalculating immediately** - You can always click "Apply Wind Direction" to finalize your setting

For best results, sail both upwind and downwind on both port and starboard tacks during your session!