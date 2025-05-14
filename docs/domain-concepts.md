# Foil Lab Domain Concepts

This document explains the core domain concepts used in the Foil Lab application.

## 1. Track

A **Track** represents a complete GPS recording of a wingfoil session. It contains:

- A series of **Track Points** with position, time, and derived data
- Overall metrics like distance, duration, and average speed
- A collection of **Segments** detected within the track

## 2. Segment

A **Segment** is a stretch of consistent sailing in a track, characterized by:

- A consistent bearing/heading
- Sufficient duration and distance
- Similar speed characteristics
- Relationship to the estimated wind direction

Segments are the fundamental unit of analysis in the application. They represent periods where the sailor was maintaining a consistent angle to the wind, allowing us to analyze performance at different angles.

## 3. Wind Direction

**Wind Direction** represents where the wind is coming FROM, measured in degrees:

- 0° = North
- 90° = East
- 180° = South
- 270° = West

Accurate wind direction estimation is critical for all subsequent analysis, as it determines how segments are categorized and compared.

## 4. Angle to Wind

The **Angle to Wind** is the angle between a sailor's bearing and the wind direction:

- 0° = Sailing directly into the wind (impossible)
- 45° = Typical upwind angle
- 90° = Sailing across the wind (beam reach)
- 180° = Sailing directly downwind

Smaller upwind angles indicate better pointing ability, while optimal downwind angles vary by equipment and conditions.

## 5. Tack

**Tack** refers to which side of the sail or wing the wind is coming from:

- **Port Tack**: Wind coming from the port (left) side
- **Starboard Tack**: Wind coming from the starboard (right) side

The difference in performance between port and starboard tacks can reveal technique asymmetries.

## 6. VMG (Velocity Made Good)

**Velocity Made Good (VMG)** measures the effective speed made directly upwind or downwind:

For upwind:
- VMG = Speed × cos(angle to wind)

For downwind:
- VMG = Speed × cos(180° - angle to wind)

Higher VMG indicates more efficient sailing, regardless of the actual sailing angle.

## 7. Segment Quality

**Segment Quality** measures how reliable a segment is for analysis:

- Distance (50%): Longer segments are more reliable
- Speed consistency (30%): Segments with consistent speed are more reliable
- Duration (20%): Longer duration segments are more reliable

The quality score helps prioritize the most reliable data for analysis.

## 8. Suspicious Segments

**Suspicious Segments** are segments that are likely to be invalid or unreliable:

- Angles too close to the wind (< 20°) are physically impossible for wingfoiling
- Very short segments may be GPS artifacts or maneuvers
- Extreme speed variations may indicate measurement errors

Filtering out suspicious segments improves analysis accuracy.

## 9. Wind Estimation

**Wind Estimation** is the process of determining the wind direction from sailing patterns:

- **Basic**: Simple average of port and starboard tack angles
- **Iterative**: Successive refinement of wind direction to balance port/starboard angles
- **Weighted**: Distance-weighted algorithm that gives more importance to longer segments

Wind direction can be either user-provided or automatically estimated from the track data.

## 10. Gear Configuration

A **Gear Configuration** represents a specific combination of equipment:

- Wing size and model
- Board type and volume
- Foil make and model
- Rider weight and style

Comparing different gear configurations helps optimize equipment choices for conditions.

## Relationships Between Concepts

- A **Track** contains many **Track Points** and **Segments**
- **Segments** have an **Angle to Wind** based on the estimated **Wind Direction**
- **Segments** are categorized by **Tack** and upwind/downwind orientation
- **VMG** is calculated from segment speed and **Angle to Wind**
- **Segment Quality** helps determine which segments to prioritize in analysis
- **Gear Configurations** can be compared based on their performance metrics

## Key Analysis Metrics

1. **Best Upwind Angle**: The smallest angle to wind at which the sailor can effectively sail
2. **Upwind VMG**: The effective speed made directly upwind
3. **Best Downwind Angle**: The angle to wind that provides the fastest downwind progress
4. **Downwind VMG**: The effective speed made directly downwind
5. **Tack Balance**: The symmetry between port and starboard tack performance
6. **Speed Polar**: Speed achieved at different angles to the wind

These metrics help sailors understand their performance and improve their technique.