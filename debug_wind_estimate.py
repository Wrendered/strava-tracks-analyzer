#!/usr/bin/env python
"""
Debug the wind direction estimation with a real GPX file.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from utils.gpx_parser import load_gpx_from_path
from utils.calculations import calculate_track_metrics
from utils.analysis import find_consistent_angle_stretches, estimate_wind_direction

# Path to the real GPX file
gpx_path = "/Users/wren_dougherty/strava-tracks-analyzer/strava-tracks-analyzer/data/3m_pocket_rocket_20_knots.gpx"

# Parameters
angle_tolerance = 10
min_duration = 10
min_distance = 50
min_speed_knots = 10.0
min_speed_ms = min_speed_knots * 0.514444

# Load and process the GPX file
gpx_data = load_gpx_from_path(gpx_path)
stretches = find_consistent_angle_stretches(
    gpx_data, angle_tolerance, min_duration, min_distance
)

if stretches.empty:
    print("No consistent stretches found")
    exit(1)

# Filter by minimum speed
stretches = stretches[stretches['speed'] >= min_speed_ms]

if stretches.empty:
    print("No stretches meet minimum speed criteria")
    exit(1)

print(f"Found {len(stretches)} consistent segments")

# Print all bearings to see what we're working with
print("\nAll segment bearings:")
for i, bearing in enumerate(stretches['bearing']):
    print(f"Segment {i+1}: {bearing:.1f}°")

# Get the estimated wind direction and the details of how it was calculated
estimated_wind = estimate_wind_direction(stretches)
print(f"\nEstimated wind direction: {estimated_wind:.1f}°")

# Debug the wind direction estimation process
print("\nDebug the wind estimation process:")

# Filter to stretches with good distance
min_distance_threshold = stretches['distance'].quantile(0.5)
good_stretches = stretches[stretches['distance'] > min_distance_threshold]
print(f"Using {len(good_stretches)} stretches above median distance ({min_distance_threshold:.1f}m)")

# Get the bearings for clustering
bearings = good_stretches['bearing'].values
print("\nBearings used for clustering:")
for i, bearing in enumerate(bearings):
    print(f"Stretch {i+1}: {bearing:.1f}°")

# Convert bearings to x,y coordinates on unit circle for proper clustering
x = np.cos(np.radians(bearings))
y = np.sin(np.radians(bearings))

# Visualize bearings on a circle
fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': 'polar'})
ax.scatter(np.radians(bearings), np.ones(len(bearings)), s=100, alpha=0.7)

for i, bearing in enumerate(bearings):
    ax.text(np.radians(bearing), 1.1, f"{bearing:.0f}°", 
            ha='center', va='center', fontsize=10)

# Add estimated wind direction if available
if estimated_wind is not None:
    ax.scatter(np.radians(estimated_wind), 1.5, s=200, color='red', marker='*')
    ax.text(np.radians(estimated_wind), 1.6, f"Est. Wind: {estimated_wind:.0f}°", 
            ha='center', va='center', fontsize=12, color='red')
    
    # Add correct wind range (60-100°)
    for angle in [60, 100]:
        ax.scatter(np.radians(angle), 1.3, s=150, color='green', marker='*')
        ax.text(np.radians(angle), 1.4, f"{angle}°", 
                ha='center', va='center', fontsize=12, color='green')
    
    # Fill the expected range
    theta = np.linspace(np.radians(60), np.radians(100), 50)
    r = np.ones(50) * 1.3
    ax.fill(theta, r, color='green', alpha=0.2)

ax.set_theta_zero_location('N')
ax.set_theta_direction(-1)  # clockwise
ax.set_rticks([])  # Hide radial ticks
ax.set_title('Segment Bearings and Wind Direction Estimation', fontsize=14)
ax.grid(True)

plt.tight_layout()
plt.savefig('wind_estimation_debug.png')
print("\nSaved visualization to wind_estimation_debug.png")

# Try to find 2-4 clusters
from sklearn.cluster import KMeans

print("\nTrying different numbers of clusters:")
for n in range(2, min(5, len(good_stretches))):
    kmeans = KMeans(n_clusters=n, random_state=0, n_init=10).fit(np.column_stack([x, y]))
    score = kmeans.inertia_
    
    # Get cluster centers and convert back to angles
    centers = kmeans.cluster_centers_
    center_angles = (np.degrees(np.arctan2(centers[:, 1], centers[:, 0])) + 360) % 360
    
    print(f"\nWith {n} clusters:")
    print(f"  Score (inertia): {score:.2f}")
    print(f"  Cluster centers: {', '.join([f'{angle:.1f}°' for angle in center_angles])}")
    
    # Assign each bearing to its cluster
    labels = kmeans.labels_
    for i, (bearing, label) in enumerate(zip(bearings, labels)):
        print(f"  Stretch {i+1} bearing {bearing:.1f}° -> Cluster {label+1} ({center_angles[label]:.1f}°)")
    
    # Find the most opposite pair of angles
    max_diff = -1
    angle1 = angle2 = 0
    angle1_idx = angle2_idx = 0
    
    for i in range(len(center_angles)):
        for j in range(i+1, len(center_angles)):
            diff = abs(center_angles[i] - center_angles[j])
            diff = min(diff, 360 - diff)
            if diff > max_diff:
                max_diff = diff
                angle1 = center_angles[i]
                angle2 = center_angles[j]
                angle1_idx = i
                angle2_idx = j
    
    print(f"\n  Most opposite angles: {angle1:.1f}° and {angle2:.1f}° (difference: {max_diff:.1f}°)")
    
    if max_diff > 60:
        # Calculate the average heading
        avg_heading = (angle1 + angle2) / 2
        if abs(angle1 - angle2) > 180:
            # Adjust for the case where angles cross the 0/360 boundary
            avg_heading = (avg_heading + 180) % 360
            
        # The wind direction is perpendicular to this heading
        estimated_wind_from_pair = (avg_heading + 90) % 360
        
        print(f"  Average heading: {avg_heading:.1f}°")
        print(f"  Estimated wind direction: {estimated_wind_from_pair:.1f}°")
    else:
        print("  Angles not sufficiently opposite (less than 60° apart)")

# Visualize clusters with the best number of clusters
best_n = 3  # This is typically what the algorithm would choose based on the improvement threshold
kmeans = KMeans(n_clusters=best_n, random_state=0, n_init=10).fit(np.column_stack([x, y]))
labels = kmeans.labels_
centers = kmeans.cluster_centers_
center_angles = (np.degrees(np.arctan2(centers[:, 1], centers[:, 0])) + 360) % 360

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': 'polar'})

# Plot each cluster with a different color
colors = ['red', 'blue', 'green', 'purple', 'orange']
for i in range(best_n):
    cluster_points = bearings[labels == i]
    ax.scatter(np.radians(cluster_points), np.ones(len(cluster_points)), 
               s=100, alpha=0.7, color=colors[i % len(colors)], 
               label=f'Cluster {i+1} (center: {center_angles[i]:.1f}°)')
    
    # Add the cluster center
    ax.scatter(np.radians(center_angles[i]), 1.3, s=150, 
               color=colors[i % len(colors)], marker='X')

# Add estimated wind direction if available
if estimated_wind is not None:
    ax.scatter(np.radians(estimated_wind), 1.5, s=200, color='black', marker='*')
    ax.text(np.radians(estimated_wind), 1.6, f"Est. Wind: {estimated_wind:.0f}°", 
            ha='center', va='center', fontsize=12, color='black')
    
    # Add correct wind range (60-100°)
    for angle in [60, 100]:
        ax.scatter(np.radians(angle), 1.5, s=150, color='green', marker='*')
    
    # Fill the expected range
    theta = np.linspace(np.radians(60), np.radians(100), 50)
    r = np.ones(50) * 1.5
    ax.fill(theta, r, color='green', alpha=0.2, label='Expected wind range (60-100°)')

ax.set_theta_zero_location('N')
ax.set_theta_direction(-1)  # clockwise
ax.set_rticks([])  # Hide radial ticks
ax.set_title(f'Bearing Clusters (k={best_n}) and Wind Direction Estimation', fontsize=14)
ax.grid(True)
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=3)

plt.tight_layout()
plt.savefig('wind_estimation_clusters.png')
print("\nSaved cluster visualization to wind_estimation_clusters.png")

# Propose a correction to the wind estimation algorithm
print("\nProposed correction to wind estimation algorithm:")
print("The current algorithm assumes that:")
print("1. The most opposite angles are the upwind tacks")
print("2. Wind direction is perpendicular (+90°) to the average of these opposite angles")
print("\nThis assumption may be incorrect for this dataset. Let's try alternative approaches:")

# Alternative 1: Use the most frequent angles
from scipy.stats import circmean

# Calculate circular mean
radians = np.radians(bearings)
mean_angle = circmean(radians)
mean_degrees = (np.degrees(mean_angle) + 360) % 360

print("\nAlternative 1: Use circular mean of all bearings")
print(f"Mean bearing: {mean_degrees:.1f}°")
print(f"Estimated wind direction (mean + 90°): {(mean_degrees + 90) % 360:.1f}°")
print(f"Estimated wind direction (mean - 90°): {(mean_degrees - 90) % 360:.1f}°")

# Alternative 2: Directly clustering wind angles, assuming most sailing is done across the wind
print("\nAlternative 2: Directly estimate wind by assuming most sailing is across the wind")
for bearing in bearings:
    possible_wind1 = (bearing + 90) % 360
    possible_wind2 = (bearing - 90) % 360
    print(f"Bearing {bearing:.1f}° suggests wind at either {possible_wind1:.1f}° or {possible_wind2:.1f}°")

# Get all possible wind angles
all_possible_winds = []
for bearing in bearings:
    all_possible_winds.append((bearing + 90) % 360)
    all_possible_winds.append((bearing - 90) % 360)

# Cluster the possible wind angles to find the most consistent one
x_wind = np.cos(np.radians(all_possible_winds))
y_wind = np.sin(np.radians(all_possible_winds))
kmeans_wind = KMeans(n_clusters=2, random_state=0, n_init=10).fit(np.column_stack([x_wind, y_wind]))
centers_wind = kmeans_wind.cluster_centers_
center_angles_wind = (np.degrees(np.arctan2(centers_wind[:, 1], centers_wind[:, 0])) + 360) % 360

print("\nClustering possible wind directions:")
for i, center in enumerate(center_angles_wind):
    count = np.sum(kmeans_wind.labels_ == i)
    print(f"Cluster {i+1}: {center:.1f}° with {count} points")

# Find the cluster with the most points
best_cluster = np.argmax([np.sum(kmeans_wind.labels_ == i) for i in range(len(center_angles_wind))])
best_wind_estimate = center_angles_wind[best_cluster]
print(f"\nBest wind direction estimate: {best_wind_estimate:.1f}°")

if __name__ == "__main__":
    print("\nRun the main script with our new estimate:")
    print(f"python analyze_gpx.py /Users/wren_dougherty/strava-tracks-analyzer/strava-tracks-analyzer/data/3m_pocket_rocket_20_knots.gpx --wind {best_wind_estimate:.1f}")