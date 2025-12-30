#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Path
from geometry_msgs.msg import TransformStamped
import tf2_ros
import math
import numpy as np

class SimplePathFollower(Node):
    def __init__(self):
        super().__init__('simple_path_follower')
        
        # Parameters
        self.declare_parameter('speed', 1.0) # m/s
        self.speed = self.get_parameter('speed').get_parameter_value().double_value
        
        # State
        self.path = None
        self.current_path_index = 0
        self.current_pose = np.zeros(3) # x, y, z
        self.is_moving = False
        self.last_time = self.get_clock().now()
        
        # Subscribers
        self.create_subscription(Path, '/pct/global_path', self.path_callback, 10)
        
        # TF Broadcaster
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)
        
        # Timer for control loop (e.g., 30 Hz)
        self.dt = 0.033
        self.create_timer(self.dt, self.control_loop)
        
        self.get_logger().info("Simple Path Follower initialized. Waiting for path...")

        # Publish initial transform
        self.publish_tf(self.current_pose)

    def path_callback(self, msg):
        self.get_logger().info(f"Received path with {len(msg.poses)} points.")
        if len(msg.poses) < 2:
            return
            
        self.path = msg
        self.current_path_index = 0
        
        # Set start position to the first point of the path
        start_pt = msg.poses[0].pose.position
        self.current_pose = np.array([start_pt.x, start_pt.y, start_pt.z])
        
        self.is_moving = True
        self.last_time = self.get_clock().now()

    def control_loop(self):
        if not self.is_moving or self.path is None:
            # Just publish the current static pose
            self.publish_tf(self.current_pose)
            return
            
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now
        
        # If dt is too large (e.g. after a pause), clamp it
        if dt > 0.1:
            dt = 0.1
            
        dist_to_move = self.speed * dt
        
        while dist_to_move > 0 and self.current_path_index < len(self.path.poses) - 1:
            # Get current target point
            target_pt_msg = self.path.poses[self.current_path_index + 1].pose.position
            target_pt = np.array([target_pt_msg.x, target_pt_msg.y, target_pt_msg.z])
            
            # Vector to target
            direction = target_pt - self.current_pose
            dist_to_target = np.linalg.norm(direction)
            
            if dist_to_target <= dist_to_move:
                # We reached (or passed) the target point
                self.current_pose = target_pt
                dist_to_move -= dist_to_target
                self.current_path_index += 1
            else:
                # Move towards target
                self.current_pose += (direction / dist_to_target) * dist_to_move
                dist_to_move = 0
                
        # Check if finished
        if self.current_path_index >= len(self.path.poses) - 1:
            self.is_moving = False
            self.get_logger().info("Target reached!")
            
        self.publish_tf(self.current_pose)

    def publish_tf(self, pose):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        
        t.transform.translation.x = pose[0]
        t.transform.translation.y = pose[1]
        t.transform.translation.z = pose[2]
        
        # Identity rotation for sphere (or calculate orientation if needed)
        # t.transform.rotation.w = 1.0

        # Calculate orientation based on movement direction (Yaw) and path slope (Pitch)
        if self.path and self.current_path_index < len(self.path.poses) - 1:
             # Look ahead to get direction
             current_pt = self.current_pose
             next_pt_msg = self.path.poses[self.current_path_index + 1].pose.position
             next_pt = np.array([next_pt_msg.x, next_pt_msg.y, next_pt_msg.z])
             
             direction = next_pt - current_pt
             if np.linalg.norm(direction) > 1e-3: # Avoid division by zero
                 # Yaw (rotation around Z)
                 yaw = math.atan2(direction[1], direction[0])
                 
                 # Pitch (rotation around Y, for slope)
                 # Calculate pitch based on Z change over XY distance
                 xy_dist = math.sqrt(direction[0]**2 + direction[1]**2)
                 pitch = -math.atan2(direction[2], xy_dist) # Negative because pitch up is usually negative rotation around Y in standard aircraft frames, but check ROS convention: RPY. 
                 # In ROS: Roll (X), Pitch (Y), Yaw (Z).
                 # Pitching nose up corresponds to negative rotation around Y axis if X is forward? No.
                 # Let's check standard conversion.
                 # Pitch is angle between vector and XY plane.
                 pitch = -math.atan2(direction[2], xy_dist)
                 
                 # Construct Quaternion from Euler (Roll=0, Pitch, Yaw)
                 # We need a helper or use scipy/tf_transformations. 
                 # Since we don't want extra heavy dependencies if possible, let's do basic math or use a simple conversion.
                 
                 cy = math.cos(yaw * 0.5)
                 sy = math.sin(yaw * 0.5)
                 cp = math.cos(pitch * 0.5)
                 sp = math.sin(pitch * 0.5)
                 cr = math.cos(0 * 0.5) # Roll = 0
                 sr = math.sin(0 * 0.5)

                 q_w = cr * cp * cy + sr * sp * sy
                 q_x = sr * cp * cy - cr * sp * sy
                 q_y = cr * sp * cy + sr * cp * sy
                 q_z = cr * cp * sy - sr * sp * cy

                 t.transform.rotation.x = q_x
                 t.transform.rotation.y = q_y
                 t.transform.rotation.z = q_z
                 t.transform.rotation.w = q_w
             else:
                 t.transform.rotation.w = 1.0
        else:
             t.transform.rotation.w = 1.0
        
        self.tf_broadcaster.sendTransform(t)

def main(args=None):
    rclpy.init(args=args)
    node = SimplePathFollower()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

