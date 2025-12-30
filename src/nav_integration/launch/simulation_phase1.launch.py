import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def launch_setup(context, *args, **kwargs):
    pkg_nav_integration = get_package_share_directory('nav_integration')
    
    # Resolve scene name
    scene_name = LaunchConfiguration('scene').perform(context)
    scene_name_pre = scene_name.capitalize()
    step_max = LaunchConfiguration('step_max').perform(context)
    
    # Map scene name to PCD file
    # Paths are hardcoded based on project structure
    base_pcd_dir = '/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/rsc/pcd'
    scene_map = {
        'Spiral': 'spiral0.3_2.pcd',
        'Building': 'building2_9.pcd',
        'Building2': 'building2_10.pcd',
        'Plaza': 'plaza3_10.pcd',
        'Map': 'map.pcd'
    }
    
    pcd_filename = scene_map.get(scene_name_pre, 'building2_9.pcd') # Default fallback
    pcd_path = os.path.join(base_pcd_dir, pcd_filename)
    
    # 1. Bringup Map
    bringup_map_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav_integration, 'launch', 'bringup_map.launch.py')
        ),
        launch_arguments={'pcd_file': pcd_path}.items()
    )

    # 2. Start PCT Planner
    # We need to pass step_max if supported. 
    # But run_pct.launch.py currently only takes 'scene' and 'robot_height'.
    # I should check if run_pct.launch.py supports extra args or if I need to update it.
    # The prompt implies adding step_max setting. 
    # Since run_pct.launch.py calls plan.py, and plan.py might not have step_max argument exposed yet?
    # Wait, the user showed tomography.py has step_max. Does plan.py have it?
    # I should check plan.py arguments. If not, I might need to add it there too or just to run_pct.launch.py if it just passes it.
    # Let's assume for now I will pass it to run_pct.launch.py and update that file to handle it.
    
    run_pct_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav_integration, 'launch', 'run_pct.launch.py')
        ),
        launch_arguments={
            'scene': scene_name_pre,
            'robot_height': '0.05',
            'step_max': step_max
        }.items()
    )

    # 3. Start Path Follower
    path_follower_node = Node(
        package='nav_integration',
        executable='simple_path_follower',
        name='simple_path_follower',
        output='screen',
        parameters=[{'speed': LaunchConfiguration('speed')}]
    )
    
    return [bringup_map_launch, run_pct_launch, path_follower_node]

def generate_launch_description():
    # Arguments
    scene_arg = DeclareLaunchArgument(
        'scene',
        default_value='Building',
        description='Name of the scene (Spiral, Building, Building2, Plaza, Map)'
    )
    
    speed_arg = DeclareLaunchArgument(
        'speed',
        default_value='1.0',
        description='Speed of the robot (m/s)'
    )
    
    step_max_arg = DeclareLaunchArgument(
        'step_max',
        default_value='0.2',
        description='Maximum step size for robot'
    )

    return LaunchDescription([
        scene_arg,
        speed_arg,
        step_max_arg,
        OpaqueFunction(function=launch_setup)
    ])
