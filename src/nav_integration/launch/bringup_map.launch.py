import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    pkg_share = get_package_share_directory('nav_integration')
    
    # Map scene name to PCD file path
    # Default is Building -> building2_9.pcd as per prompt
    # But to support dynamic scene switching via 'scene' argument, we need logic.
    # However, LaunchConfiguration is resolved at runtime, so we can't use python dict lookup directly on it easily without OpaqueFunction.
    # For simplicity, we can pass the pcd_file path directly as argument to this launch file, 
    # and let the top-level launch file (simulation_phase1) handle the mapping logic or just pass the path.
    
    # But wait, bringing up map launch file currently takes 'pcd_file' argument. 
    # So if simulation_phase1 passes 'pcd_file', it works!
    
    default_pcd_path = '/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/rsc/pcd/building2_9.pcd'
    
    pcd_file = LaunchConfiguration('pcd_file')
    
    pcd_arg = DeclareLaunchArgument(
        'pcd_file',
        default_value=default_pcd_path,
        description='Path to the PCD file'
    )
    
    urdf_file = os.path.join(pkg_share, 'urdf', 'robot.urdf')
    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()
        
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}],
    )

    map_server_node = Node(
        package='nav_integration',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'pcd_file': pcd_file}]
    )
    
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'nav.rviz')
    # If file doesn't exist, rviz might complain or start empty.
    # Since I failed to copy it, I should create a minimal one or just launch without config if missing.
    # But I will try to use the one I referenced in the copy command.
    # Actually, I should check if I can point to the one in PCT_planner_re directly?
    # No, better to have a local one.
    # I'll try to use the path to the original rviz config for now if the local one is missing?
    # No, I should fix the copy or create a new one. 
    # Since I can't easily copy in launch file logic, I will rely on the fact that I will fix the copy manually via terminal or tools.
    
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        output='screen'
    )
    
    return LaunchDescription([
        pcd_arg,
        robot_state_publisher,
        map_server_node,
        rviz_node
    ])

