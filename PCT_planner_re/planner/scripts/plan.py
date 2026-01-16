import sys
import argparse
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy

from nav_msgs.msg import Path
from geometry_msgs.msg import PointStamped, PoseWithCovarianceStamped, PoseStamped  # 修改

from utils import traj2ros
from planner_wrapper import TomogramPlanner

sys.path.append('../')
from config import Config

class PCTPlanner(Node):
    def __init__(self, cfg, tomo_file, robot_height, step_max):
        super().__init__('pct_planner')
        self.cfg = cfg
        self.tomo_file = tomo_file
        self.robot_height = robot_height
        self.step_max = step_max

        qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL
        )

        self.path_pub = self.create_publisher(Path, "/pct/global_path", qos)
        # self.click_sub = self.create_subscription(PointStamped, "/clicked_point", self.clicked_point_callback, 10)
        
        # New subscribers for 2D Pose Estimate and 2D Goal Pose
        self.initial_pose_sub = self.create_subscription(PoseWithCovarianceStamped, "/initialpose", self.initial_pose_callback, 10)
        self.goal_pose_sub = self.create_subscription(PoseStamped, "/goal_pose", self.goal_pose_callback, 10)

        self.planner = TomogramPlanner(cfg)
        self.planner.loadTomogram(self.tomo_file, self.step_max)

        self.start_pos = None
        self.start_layer = None
        self.end_pos = None
        self.end_layer = None

        self.get_logger().info("Waiting for 2D Pose Estimate (Start) and 2D Goal Pose (End) in RViz...")

    def initial_pose_callback(self, msg):
        """Handle 2D Pose Estimate from RViz for Start Pose"""
        point = np.array([msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z], dtype=np.float32)
        
        self.start_pos = point[:2]
        self.start_layer = self.planner.height2layer(point[2])
        self.get_logger().info(f"🟢 Start pose set to: {self.start_pos}, Layer: {self.start_layer}")
        
        # Reset end pose when new start is set
        self.end_pos = None
        self.end_layer = None

    def goal_pose_callback(self, msg):
        """Handle 2D Goal Pose from RViz for End Pose"""
        point = np.array([msg.pose.position.x, msg.pose.position.y, msg.pose.position.z], dtype=np.float32)
        
        if self.start_pos is None:
            self.get_logger().warn("⚠️ Please set Initial Pose (Start) first using '2D Pose Estimate' tool.")
            return

        self.end_pos = point[:2]
        self.end_layer = self.planner.height2layer(point[2])
        self.get_logger().info(f"🔴 End pose set to: {self.end_pos}, Layer: {self.end_layer}")
        
        self.pct_plan()

    # def clicked_point_callback(self, msg):
    #     point = np.array([msg.point.x, msg.point.y, msg.point.z], dtype=np.float32)
    #
    #     if self.start_pos is None:
    #         self.start_pos = point[:2]
    #         self.start_layer = self.planner.height2layer(point[2])
    #         self.get_logger().info(f"🟢 Start point set to: {self.start_pos}")
    #     elif self.end_pos is None:
    #         self.end_pos = point[:2]
    #         self.end_layer = self.planner.height2layer(point[2])
    #         self.get_logger().info(f"🔴 End point set to: {self.end_pos}")
    #         self.pct_plan()
    #     else:
    #         self.get_logger().info("♻️ Resetting start/end points...")
    #         self.start_pos = point[:2]
    #         self.start_layer = self.planner.height2layer(point[2])
    #         self.end_pos = None

    def pct_plan(self):

        traj_3d = self.planner.plan(self.start_pos, self.end_pos, self.start_layer, self.end_layer, self.robot_height)
        if traj_3d is not None:
            self.path_pub.publish(traj2ros(traj_3d))
            self.get_logger().info("✅ Trajectory published to /pct/global_path")
        else:
            self.get_logger().warn("❌ Planning failed!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', type=str, default='Spiral', help='Name of the scene. Available: [\'Spiral\', \'Building\', \'Plaza\', \'Map\', \'Company\']')
    parser.add_argument('--robot_height', type=float, default=0.05, help='Height of the robot')
    parser.add_argument('--step_max', type=float, default=0.2, help='Maximum step size')
    args = parser.parse_args()

    cfg = Config()

    input_scene = args.scene.capitalize()

    match input_scene:
        case "Spiral":
            tomo_file = "spiral0.3_2"
        case 'Building':
            tomo_file = 'building2_9'
        case 'Building2':
            tomo_file = 'building2_10'
        case 'Plaza':
            tomo_file = 'plaza3_10'
        case "Map":
            tomo_file = "map"
        case "Company":
            tomo_file = "dense_full_map"
        case _:
            raise ValueError('Invalid scene name')

    rclpy.init(args=None)
    node = PCTPlanner(cfg, tomo_file, args.robot_height, args.step_max)
    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()
