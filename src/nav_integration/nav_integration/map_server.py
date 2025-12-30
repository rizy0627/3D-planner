#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2, PointField
from std_msgs.msg import Header
from geometry_msgs.msg import TransformStamped
import tf2_ros
import numpy as np
import open3d as o3d
import sensor_msgs_py.point_cloud2 as pc2
import os

class MapServer(Node):
    def __init__(self):
        super().__init__('map_server')
        
        # Declare parameters
        self.declare_parameter('pcd_file', '')
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('topic_name', 'global_points')
        
        self.pcd_file = self.get_parameter('pcd_file').get_parameter_value().string_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.topic_name = self.get_parameter('topic_name').get_parameter_value().string_value
        
        if not self.pcd_file:
            self.get_logger().error("No PCD file specified!")
            return

        self.get_logger().info(f"Loading PCD file: {self.pcd_file}")
        
        # Publisher
        self.map_pub = self.create_publisher(PointCloud2, self.topic_name, 10) # Transient local or reliable might be better
        from rclpy.qos import QoSProfile, QoSDurabilityPolicy
        qos = QoSProfile(depth=1, durability=QoSDurabilityPolicy.TRANSIENT_LOCAL)
        self.map_pub = self.create_publisher(PointCloud2, self.topic_name, qos)

        # Load and publish
        self.pcd_msg = self.load_pcd(self.pcd_file)
        
        # Timer to publish periodically (or just once if transient local, but keeping it simple)
        self.create_timer(1.0, self.publish_map)
        
        # TF Broadcaster (Static)
        self.tf_broadcaster = tf2_ros.StaticTransformBroadcaster(self)
        self.publish_tf()
        
    def load_pcd(self, file_path):
        if not os.path.exists(file_path):
            self.get_logger().error(f"File not found: {file_path}")
            return None
            
        pcd = o3d.io.read_point_cloud(file_path)
        points = np.asarray(pcd.points, dtype=np.float32)
        
        if points.size == 0:
            self.get_logger().warn("PCD file is empty or could not be read.")
            return None
            
        header = Header()
        header.frame_id = self.frame_id
        header.stamp = self.get_clock().now().to_msg()
        
        # Create PointCloud2 msg
        # pc2.create_cloud_xyz32 is efficient
        msg = pc2.create_cloud_xyz32(header, points)
        return msg

    def publish_map(self):
        if self.pcd_msg:
            # Update timestamp
            self.pcd_msg.header.stamp = self.get_clock().now().to_msg()
            self.map_pub.publish(self.pcd_msg)
            
    def publish_tf(self):
        t = TransformStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = 'map'
        t.child_frame_id = 'odom'
        t.transform.translation.x = 0.0
        t.transform.translation.y = 0.0
        t.transform.translation.z = 0.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = 0.0
        t.transform.rotation.w = 1.0
        
        self.tf_broadcaster.sendTransform(t)

        # Publish odom -> base_link (Static for now, just to show the robot)
        # REMOVED: Now handled by simple_path_follower
        # t2 = TransformStamped()
        # t2.header.stamp = self.get_clock().now().to_msg()
        # t2.header.frame_id = 'odom'
        # t2.child_frame_id = 'base_link'
        # t2.transform.translation.x = 0.0
        # t2.transform.translation.y = 0.0
        # t2.transform.translation.z = 0.0 
        # t2.transform.rotation.w = 1.0
        # self.tf_broadcaster.sendTransform(t2)

def main(args=None):
    rclpy.init(args=args)
    node = MapServer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

