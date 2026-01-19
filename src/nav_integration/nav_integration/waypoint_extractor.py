#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped, Point
from visualization_msgs.msg import Marker, MarkerArray
from std_msgs.msg import String, ColorRGBA
import numpy as np
import math

class WaypointExtractor(Node):
    def __init__(self):
        super().__init__('waypoint_extractor')
        
        # Parameters
        self.declare_parameter('min_spacing', 3.0)  # meters
        self.declare_parameter('angle_threshold_deg', 30.0) # degrees
        self.declare_parameter('pitch_threshold_deg', 15.0) # degrees, for slope change detection
        self.declare_parameter('corner_min_distance', 0.3)  # meters, minimum distance to add a corner point
        self.declare_parameter('lookahead', 5)  # number of points to look ahead for curvature detection
        self.declare_parameter('z_change_threshold', 0.5)  # meters, height change to detect stairs/elevator

        self.min_spacing = self.get_parameter('min_spacing').get_parameter_value().double_value
        self.angle_threshold_rad = math.radians(self.get_parameter('angle_threshold_deg').get_parameter_value().double_value)
        self.pitch_threshold_rad = math.radians(self.get_parameter('pitch_threshold_deg').get_parameter_value().double_value)
        self.corner_min_distance = self.get_parameter('corner_min_distance').get_parameter_value().double_value
        self.lookahead = self.get_parameter('lookahead').get_parameter_value().integer_value
        self.z_change_threshold = self.get_parameter('z_change_threshold').get_parameter_value().double_value
        
        # Subscribers
        self.path_sub = self.create_subscription(
            Path,
            '/pct/global_path',
            self.path_callback,
            10
        )
        
        # Publishers
        # Note: Using nav_msgs/Path as it is the standard ROS2 message for a sequence of PoseStamped.
        # User requested /waypoint_sequence (geometry_msgs/PoseStampedArray), but that message type does not exist in standard ROS2.
        self.waypoints_pub = self.create_publisher(Path, '/waypoint_sequence', 10)
        self.vis_pub = self.create_publisher(MarkerArray, '/pct/waypoints_vis', 10)
        self.raw_vis_pub = self.create_publisher(MarkerArray, '/waypoint_extractor/raw_path_vis', 10)
        self.diag_pub = self.create_publisher(String, '/waypoint_extractor/diagnostics', 10)

        # Parameter to control visualization of raw path points
        self.declare_parameter('visualize_raw_points', True)
        self.visualize_raw_points = self.get_parameter('visualize_raw_points').get_parameter_value().bool_value
        
        # Internal state for loop publishing
        self.last_raw_poses = None
        self.last_extracted_waypoints = None
        self.last_frame_id = "map"
        
        # Create timer for loop publishing (1 Hz)
        self.vis_timer = self.create_timer(1.0, self.timer_callback)
        
        self.get_logger().info(f"Waypoint Extractor initialized. Spacing: {self.min_spacing}m, Corner Thresh: {math.degrees(self.angle_threshold_rad):.1f}deg")

    def path_callback(self, msg: Path):
        raw_count = len(msg.poses)
        if raw_count < 2:
            self.get_logger().warn("Received path with less than 2 points.")
            return

        # Perform downsampling
        extracted_waypoints = self.extract_waypoints(msg.poses)

        # Store for loop publishing
        self.last_raw_poses = msg.poses
        self.last_extracted_waypoints = extracted_waypoints
        self.last_frame_id = msg.header.frame_id

        # Publish extracted waypoints
        output_msg = Path()
        output_msg.header = msg.header
        output_msg.poses = extracted_waypoints
        self.waypoints_pub.publish(output_msg)

        # Publish visualization (both raw points and extracted waypoints)
        self.publish_visualization(msg.poses, extracted_waypoints, msg.header.frame_id)

        # Diagnostics
        diag_msg = String()
        diag_msg.data = f"Extracted {len(extracted_waypoints)} waypoints from {raw_count} raw points."
        self.diag_pub.publish(diag_msg)

        self.get_logger().info(diag_msg.data)
        self._log_waypoints(extracted_waypoints)

    def extract_waypoints(self, poses):
        if not poses:
            return []

        waypoints = []

        # Strategy:
        # 1. Identify "Geometric Corners" based on look-ahead curvature (more robust)
        # 2. Detect height changes (stairs/elevators)
        # 3. Iterate through the path, adding points if:
        #    a) Distance from last waypoint > min_spacing
        #    b) It is a Geometric Corner or Stair Point (and not too close to last point)

        # Convert poses to numpy array for faster computation
        path_points = np.array([[p.pose.position.x, p.pose.position.y, p.pose.position.z] for p in poses])

        # Pass 1: Identify geometric corners and stair points
        corner_indices = set()

        # Detect height change (stairs/elevator) - look ahead for Z delta
        for i in range(0, len(poses)):
            lookahead_idx = min(i + self.lookahead, len(poses) - 1)

            # Calculate Z change lookahead
            z_before = path_points[i][2]
            z_after = path_points[lookahead_idx][2]
            z_delta = abs(z_after - z_before)

            # If significant height change detected, mark the start of slope
            if z_delta >= self.z_change_threshold:
                # Find the actual start point of the slope
                for j in range(i, lookahead_idx + 1):
                    if j < len(poses):
                        corner_indices.add(j)
                    else:
                        break
                i = lookahead_idx + 1  # Skip ahead to avoid duplicates
            else:
                # Check curvature with lookahead window
                if i < self.lookahead or i >= len(poses) - self.lookahead:
                    continue

                # Use a window of points to calculate direction
                p_before = path_points[i - self.lookahead]
                p_curr = path_points[i]
                p_after = path_points[i + self.lookahead]

                v1 = p_before - p_curr
                v2 = p_curr - p_after

                norm1 = np.linalg.norm(v1)
                norm2 = np.linalg.norm(v2)

                # Avoid division by zero or extremely short segments
                if norm1 < 0.1 or norm2 < 0.1:
                    continue

                # Calculate angle (3D Direction Change)
                cos_angle = np.dot(v1, v2) / (norm1 * norm2)
                cos_angle = max(min(cos_angle, 1.0), -1.0)
                angle = math.acos(cos_angle)  # Result in [0, pi]

                # Calculate Pitch Change (Slope Change)
                # Pitch = angle between vector and XY plane
                xy_norm1 = np.sqrt(v1[0]**2 + v1[1]**2)
                xy_norm2 = np.sqrt(v2[0]**2 + v2[1]**2)

                if xy_norm1 > 0.01 and xy_norm2 > 0.01:
                    # Use arctan2(z, xy) to get pitch
                    pitch1 = math.atan2(v1[2], xy_norm1)
                    pitch2 = math.atan2(v2[2], xy_norm2)

                    pitch_diff = abs(pitch2 - pitch1)

                    # If angle > threshold OR pitch change > threshold, it's a key point
                    if angle > self.angle_threshold_rad or pitch_diff > self.pitch_threshold_rad:
                        corner_indices.add(i)

        # Pass 2: Select waypoints
        # Always add the first point
        waypoints.append(poses[0])
        last_added_pose_np = np.array([poses[0].pose.position.x, poses[0].pose.position.y, poses[0].pose.position.z])

        curr_idx = 1
        while curr_idx < len(poses) - 1:
            curr_pose_np = np.array([poses[curr_idx].pose.position.x, poses[curr_idx].pose.position.y, poses[curr_idx].pose.position.z])
            dist = np.linalg.norm(curr_pose_np - last_added_pose_np)

            is_forced_corner = curr_idx in corner_indices

            should_add = False

            # Condition 1: Distance limit
            if dist >= self.min_spacing:
                should_add = True

            # Condition 2: Corner (with smaller minimum distance)
            # This allows adding corner points even if they're closer than min_spacing
            elif is_forced_corner and dist >= self.corner_min_distance:
                should_add = True

            if should_add:
                waypoints.append(poses[curr_idx])
                last_added_pose_np = curr_pose_np

            curr_idx += 1
            
        # Always add the last point
        # Check distance to avoid adding if too close to the previous one (e.g. < 0.1m)
        final_pose_np = np.array([poses[-1].pose.position.x, poses[-1].pose.position.y, poses[-1].pose.position.z])
        dist_final = np.linalg.norm(final_pose_np - last_added_pose_np)
        
        if dist_final > 0.1:
             waypoints.append(poses[-1])
        else:
             # If too close, replace the last one with the actual goal to be precise
             waypoints.pop()
             waypoints.append(poses[-1])
             
        return waypoints

    def timer_callback(self):
        """Periodically republish visualization markers and path"""
        if self.last_raw_poses is not None and self.last_extracted_waypoints is not None:
            # Republish visualization
            self.publish_visualization(self.last_raw_poses, self.last_extracted_waypoints, self.last_frame_id)
            
            # Republish waypoints path
            output_msg = Path()
            output_msg.header.stamp = self.get_clock().now().to_msg()
            output_msg.header.frame_id = self.last_frame_id
            output_msg.poses = self.last_extracted_waypoints
            self.waypoints_pub.publish(output_msg)

    def publish_visualization(self, raw_poses, waypoints, frame_id):
        # 1. Publish Raw Points (on separate topic)
        raw_marker_array = MarkerArray()
        
        # Clear old markers
        delete_marker = Marker()
        delete_marker.action = Marker.DELETEALL
        raw_marker_array.markers.append(delete_marker)

        if self.visualize_raw_points:
            for i, pose in enumerate(raw_poses):
                marker = Marker()
                marker.header.frame_id = frame_id
                marker.header.stamp = self.get_clock().now().to_msg()
                marker.ns = "raw_path_points"
                marker.id = i
                marker.type = Marker.SPHERE
                marker.action = Marker.ADD
                marker.pose = pose.pose
                marker.scale.x = 0.1
                marker.scale.y = 0.1
                marker.scale.z = 0.1
                marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=0.5)  # Red, semi-transparent
                raw_marker_array.markers.append(marker)
        
        self.raw_vis_pub.publish(raw_marker_array)

        # 2. Publish Extracted Waypoints
        marker_array = MarkerArray()

        # Clear old markers
        marker_array.markers.append(delete_marker)

        # Visualize extracted waypoints (large spheres with labels)
        for i, wp in enumerate(waypoints):
            # Sphere Marker
            marker = Marker()
            marker.header.frame_id = frame_id
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = "waypoints"
            marker.id = i + 10000  # Offset to avoid collision with raw points
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD
            marker.pose = wp.pose
            marker.scale.x = 0.3
            marker.scale.y = 0.3
            marker.scale.z = 0.3
            marker.color = ColorRGBA(r=0.0, g=1.0, b=0.0, a=0.8)  # Green
            marker_array.markers.append(marker)

            # Text Marker (waypoint index)
            text_marker = Marker()
            text_marker.header.frame_id = frame_id
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.ns = "waypoint_ids"
            text_marker.id = i + 20000  # Offset to avoid collision
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            text_marker.pose.position.x = wp.pose.position.x
            text_marker.pose.position.y = wp.pose.position.y
            text_marker.pose.position.z = wp.pose.position.z + 0.3
            text_marker.scale.z = 0.2
            text_marker.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)  # White
            text_marker.text = str(i)
            marker_array.markers.append(text_marker)

        self.vis_pub.publish(marker_array)

    def _log_waypoints(self, waypoints):
        # Log first few
        log_str = "Waypoints: "
        count = min(3, len(waypoints))
        for i in range(count):
            p = waypoints[i].pose.position
            log_str += f"[{p.x:.1f}, {p.y:.1f}, {p.z:.1f}], "
        if len(waypoints) > 3:
            log_str += "..."
        self.get_logger().info(log_str)

def main(args=None):
    rclpy.init(args=args)
    node = WaypointExtractor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
