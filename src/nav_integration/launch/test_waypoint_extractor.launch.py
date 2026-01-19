import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def launch_setup(context, *args, **kwargs):
    pkg_nav_integration = get_package_share_directory('nav_integration')
    
    # Resolve scene name
    scene_name = LaunchConfiguration('scene').perform(context)
    scene_name_pre = scene_name.capitalize()
    
    # Map scene name to PCD file (Hardcoded based on project structure)
    base_pcd_dir = '/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/rsc/pcd'
    scene_map = {
        'Spiral': 'spiral0.3_2.pcd',
        'Building': 'building2_9.pcd',
        'Building2': 'building2_10.pcd',
        'Plaza': 'plaza3_10.pcd',
        'Map': 'map.pcd',
        'Company': 'dense_full_map.pcd'
    }
    
    pcd_filename = scene_map.get(scene_name_pre, 'building2_9.pcd')
    pcd_path = os.path.join(base_pcd_dir, pcd_filename)
    
    # 1. Bringup Map (Visual only)
    bringup_map_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav_integration, 'launch', 'bringup_map.launch.py')
        ),
        launch_arguments={'pcd_file': pcd_path}.items()
    )

    # 2. Start PCT Planner (Global Planner)
    run_pct_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav_integration, 'launch', 'run_pct.launch.py')
        ),
        launch_arguments={
            'scene': scene_name_pre,
            'robot_height': '0.05'
        }.items()
    )

    # 3. Start Waypoint Extractor (The node we want to test)
    # Use parameters from config file
    config_file = os.path.join(pkg_nav_integration, 'config', 'waypoint_extractor_params.yaml')
    
    waypoint_extractor_node = Node(
        package='nav_integration',
        executable='waypoint_extractor',
        name='waypoint_extractor',
        output='screen',
        parameters=[config_file]
    )

    # 4. Start Tomography (Required for PCT Planner visualization and function)
    tomography_script_path = '/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/tomography/scripts/tomography.py'
    env = os.environ.copy()
    
    tomography_cmd = ExecuteProcess(
        cmd=['python3', tomography_script_path, 
             '--scene', scene_name_pre, 
             '--step_max', '0.2'], # Default step_max
        cwd='/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/tomography/scripts',
        output='screen',
        env=env
    )
    
    # 5. Static TF for Robot (Since we removed the path follower which published TF)
    # Publish 0 transform from map to base_link to make robot visible
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'base_link']
    )
    
    return [bringup_map_launch, run_pct_launch, waypoint_extractor_node, tomography_cmd, static_tf]

def generate_launch_description():
    scene_arg = DeclareLaunchArgument(
        'scene',
        default_value='Building',
        description='Name of the scene'
    )

    return LaunchDescription([
        scene_arg,
        OpaqueFunction(function=launch_setup)
    ])