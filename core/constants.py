"""
Constants for the Foil Lab application.

This module contains all the mathematical, algorithmic, and domain-specific
constants used throughout the codebase. Constants are grouped by their purpose
and documented with their units where applicable.
"""

# =============================================================================
# CONVERSION FACTORS
# =============================================================================

# Speed conversions
METERS_PER_SECOND_TO_KNOTS = 1.94384  # 1 m/s = 1.94384 knots
KNOTS_TO_METERS_PER_SECOND = 1 / METERS_PER_SECOND_TO_KNOTS

# Distance conversions
METERS_PER_KILOMETER = 1000

# =============================================================================
# ANGLE CONSTANTS (all in degrees)
# =============================================================================

# Fundamental angle values
FULL_CIRCLE_DEGREES = 360
ANGLE_WRAP_BOUNDARY_DEGREES = 180  # Used for angle wrapping calculations
UPWIND_DOWNWIND_BOUNDARY_DEGREES = 90  # Boundary between upwind and downwind

# Angle thresholds for sailing analysis
DEFAULT_SUSPICIOUS_ANGLE_THRESHOLD = 20  # Minimum realistic angle to wind
WARNING_ANGLE_TO_WIND_DEGREES = 15  # Warning threshold for small angles
DEBUG_ANGLE_TO_WIND_DEGREES = 30  # Debug logging threshold

# Wind estimation angle parameters
WIND_SEARCH_RANGE_DEGREES = 30  # Range to search around initial wind estimate
WIND_SEARCH_RANGE_WIDTH_DEGREES = 60  # Full width of search range
WIND_SEARCH_STEP_DEGREES = 10  # Step size for wind direction search
MAX_WIND_ADJUSTMENT_DEGREES = 60  # Maximum adjustment from initial estimate

# Angle clustering parameters
ANGLE_CLUSTER_RANGE_DEGREES = 15  # Default range for clustering similar angles
MIN_ANGLE_CLUSTER_RANGE_DEGREES = 5  # Minimum range for adaptive clustering

# Segment analysis angle parameters
DEFAULT_ANGLE_TOLERANCE_DEGREES = 15.0  # Default tolerance for consistent angles
MIN_ANGLE_TOLERANCE_DEGREES = 5.0  # Minimum angle tolerance
MAX_ANGLE_TOLERANCE_CAP_DEGREES = 30.0  # Maximum angle tolerance cap
MAX_BEARING_CHANGE_DEGREES = 45  # Maximum bearing change for valid segments

# VMG calculation parameters
DEFAULT_VMG_ANGLE_RANGE_DEGREES = 25  # Range around best angle for VMG calc

# =============================================================================
# DISTANCE AND TIME THRESHOLDS
# =============================================================================

# Segment detection thresholds
DEFAULT_MIN_SEGMENT_DISTANCE_METERS = 50  # Minimum distance for valid segment
MIN_RELIABLE_SEGMENT_LENGTH_METERS = 30.0  # Minimum for reliable segments
HIGH_CONFIDENCE_MIN_DISTANCE_METERS = 500  # Total distance for high confidence

# Nearby point detection
DEFAULT_NEARBY_DISTANCE_THRESHOLD_METERS = 10.0
DEFAULT_NEARBY_TIME_THRESHOLD_SECONDS = 5.0

# Time-based parameters
MIN_DISTANCE_BASE_METERS = 10.0  # Base minimum distance for scaling
MIN_TIME_BASE_SECONDS = 5.0  # Base minimum time for scaling

# =============================================================================
# WIND ESTIMATION CONFIDENCE THRESHOLDS
# =============================================================================

# Tack difference thresholds for confidence levels
HIGH_CONFIDENCE_TACK_DIFF_DEGREES = 10
MEDIUM_CONFIDENCE_TACK_DIFF_DEGREES = 20
MAX_TACK_DIFF_FOR_ADJUSTMENT_DEGREES = 30

# =============================================================================
# ALGORITHM PARAMETERS
# =============================================================================

# Segment requirements
MIN_SEGMENTS_FOR_ESTIMATION = 3  # Minimum segments for wind estimation
MIN_SEGMENTS_PERCENTAGE = 0.1  # Minimum percentage of segments to keep
MIN_ADAPTIVE_SEGMENTS = 3  # Minimum segments for adaptive calculations

# Clustering parameters
MAX_KMEANS_CLUSTERS = 4  # Maximum clusters for KMeans algorithm
KMEANS_N_INIT = 10  # Number of KMeans initializations

# Score thresholds
MIN_SCORE_FOR_USER_GUIDED = 0.4  # Minimum score to use user-guided wind
MIN_SCORE_FOR_MULTI_ANGLE = 0.3  # Minimum score for multi-angle testing

# Quality scoring weights (must sum to 1.0)
QUALITY_WEIGHT_DISTANCE = 0.5
QUALITY_WEIGHT_SPEED = 0.3
QUALITY_WEIGHT_DURATION = 0.2
QUALITY_SCORE_FACTOR = 10  # Scaling factor for quality scores

# Filtering and adjustment parameters
DISTANCE_QUANTILE_THRESHOLD = 0.25  # Quantile for distance filtering
MAX_FILTER_PERCENTAGE = 0.25  # Maximum percentage of segments to filter
SEGMENT_PERCENTAGE_FACTOR = 0.2  # Factor for adaptive range calculation
EFFICIENCY_SCORE_DIVISOR = 5  # Divisor for efficiency scoring

# Convergence parameters
WIND_CONVERGENCE_THRESHOLD_DEGREES = 1.0  # Convergence threshold for iterative

# =============================================================================
# BALANCE ANALYSIS THRESHOLDS
# =============================================================================

BALANCE_THRESHOLD_LOW = 0.33  # Below this = imbalanced toward one tack
BALANCE_THRESHOLD_HIGH = 0.67  # Above this = imbalanced toward other tack

# =============================================================================
# PARAMETER SCALING CONSTANTS
# =============================================================================

# Ideal segment parameters
IDEAL_SEGMENT_COUNT = 20  # Target number of segments
MINUTES_PER_IDEAL_SEGMENT = 15  # Minutes per ideal segment
MIN_TOTAL_SEGMENTS = 5  # Minimum total segments
MAX_TOTAL_SEGMENTS = 20  # Maximum total segments

# Scaling factors
ANGLE_TOLERANCE_SCALE_FACTOR = 0.5  # Factor for angle tolerance scaling
MIN_SCALING_FACTOR = 1.5  # Minimum scaling factor
OVER_SEGMENTATION_THRESHOLD = 0.7  # Threshold for over-segmentation
MAX_SEGMENTS_PER_TACK = 5  # Maximum segments per tack

# =============================================================================
# VALIDATION
# =============================================================================

# Ensure quality weights sum to 1.0
assert abs(QUALITY_WEIGHT_DISTANCE + QUALITY_WEIGHT_SPEED + QUALITY_WEIGHT_DURATION - 1.0) < 0.001, \
    "Quality weights must sum to 1.0"