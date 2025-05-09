# Simplified Wind Direction Algorithm

This document explains the simplified wind direction estimation algorithm used in Foil Lab.

## Algorithm Overview

The wind direction estimation algorithm uses the sailing angles from your track to calculate the most likely wind direction. It works by identifying upwind segments (which are most likely to be sailed as close to the wind as possible) and finding a wind direction that makes both port and starboard tacks equally efficient.

## Algorithm Steps

1. **Start with user input wind direction** as the anchor point
   - All sailing angles are initially calculated relative to this direction

2. **Select upwind tacks for analysis**
   - For both port and starboard, get all tacks < 90° off the user wind direction
   - If more than 5 tacks on either side, take only the best 5 (closest to wind)

3. **Find best upwind angle for each tack**
   - For each tack (port and starboard):
     - Find the segment with angle CLOSEST to the wind
     - Keep all segments within 20° of this best angle
     - Calculate the AVERAGE angle of these filtered segments
     - This is the AVERAGE UPWIND BEST for that tack

4. **Balance tack angles by adjusting wind direction**
   - When port and starboard angles differ significantly:
     - Calculate the difference between port and starboard best angles
     - Adjust wind direction by HALF this difference
     - If port angle is smaller than starboard: DECREASE wind direction
     - If starboard angle is smaller than port: INCREASE wind direction
     - This makes both tacks equally efficient upwind

5. **Calculate final wind direction**
   - After balancing the angles, verify with the adjusted wind direction:
     - Port: wind_dir = port_bearing + port_best_angle
     - Starboard: wind_dir = starboard_bearing - starboard_best_angle
     - These should now be very close to each other
   - Only use this result if it's within 60° of user input

6. **Filter impossible angles and iterate if needed**
   - With the newly calculated wind direction, check if any tacks are < 20° to wind
   - If such "impossible angles" exist, remove them from consideration
   - Re-run the balancing step with the filtered data

7. **Return wind estimate with confidence level**
   - High: Many segments with consistent angles across tacks
   - Medium: Good number of segments with reasonable consistency
   - Low: Few segments or inconsistent patterns
   - None: Insufficient data, using user input only

## Example Calculation

If port tack best angle is 55.7° and starboard best angle is 81.9°:
1. Difference: 81.9° - 55.7° = 26.2°
2. Adjustment needed: 26.2° / 2 = 13.1°
3. Since port angle is smaller than starboard, we DECREASE the wind direction
4. New wind direction: 90° - 13.1° = 76.9°

With this adjusted wind direction (76.9°):
- Port angles would increase to about 72.2°
- Starboard angles would decrease to about 72.9°
- The difference between tacks is reduced from 26.2° to just 0.6°!

## Understanding Wind Direction

Wind direction is specified as the direction **FROM WHICH** the wind is coming:
- 0° (North): Wind coming from the North, blowing South
- 90° (East): Wind coming from the East, blowing West
- 180° (South): Wind coming from the South, blowing North
- 270° (West): Wind coming from the West, blowing East

## Sailing Angle Terminology

- **Angle to Wind**: Degrees off the wind direction (0° = directly into the wind, impossible to sail)
- **Close-hauled**: Sailing as close to the wind as possible (typically 30-50°)
- **Beam Reach**: Wind coming from the side (90° to wind)
- **Broad Reach**: Wind coming from behind at an angle (120-150° to wind)
- **Running**: Wind directly behind (180° to wind)

## Physical Limitations

- Most watercraft cannot sail closer than 30-45° to the wind
- Angles less than 20° to the wind are physically impossible
- The algorithm considers angles less than 20° to be "suspicious" and may filter them out

## Tack Terminology

- **Port Tack**: Wind coming over the port (left) side of the craft
- **Starboard Tack**: Wind coming over the starboard (right) side of the craft

## Confidence Levels

The algorithm provides a confidence level with each wind direction estimate:

- **High**: Multiple consistent segments on both tacks with small variance
- **Medium**: Good data with reasonable consistency
- **Low**: Limited data or inconsistent angles
- **None**: Insufficient data to make an estimate, using user input only

## Limitations

- Best results require sailing on both port and starboard tacks
- Requires at least a few upwind segments for accurate estimation
- Very short sessions may have insufficient data for high confidence
- Performance improves with longer sessions and more tacking