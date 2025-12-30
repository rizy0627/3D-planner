import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    # Define arguments
    scene_arg = DeclareLaunchArgument(
        'scene',
        default_value='Building',
        description='Name of the scene (Spiral, Building, Plaza, Map)'
    )
    
    robot_height_arg = DeclareLaunchArgument(
        'robot_height',
        default_value='0.05',
        description='Height of the robot'
    )
    
    step_max_arg = DeclareLaunchArgument(
        'step_max',
        default_value='0.2',
        description='Maximum step size for robot'
    )
    
    # Define the node
    # Note: PCT_planner_re is not a proper ROS2 package (no package.xml), so we execute the script directly
    # We assume the workspace structure is fixed as per previous context
    # Adjust path if necessary. Using absolute path for robustness given the non-package nature.
    
    pct_script_path = '/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/planner/scripts/plan.py'
    
    # We need to set PYTHONPATH to include the parent directories of the script so it can find 'lib', 'config' etc.
    # plan.py does `sys.path.append('../')`, so running it from its directory or setting cwd works best.
    # But ExecuteProcess doesn't easily set cwd in a way that Python imports always work if we just call python3 script.py
    # A better way is to wrap it in a Node but since it's not installed, we can't use package='pct_planner'.
    # We will use ExecuteProcess to run python3.
    
    # Environment variables
    env = os.environ.copy()
    # Add the necessary library path for gtsam if needed (from README)
    # export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/YOUR/DIRECTORY/TO/PCT_planner/planner/lib/3rdparty/gtsam-4.1.1/install/lib
    # The user path might vary, but I'll try to find where it is or skip if not critical/already set.
    # Assuming the user environment might already have it or the script handles it? 
    # The README says "export LD_LIBRARY_PATH...", so we should probably add it.
    
    gtsam_lib_path = '/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/planner/lib/3rdparty/gtsam-4.1.1/install/lib'
    current_ld_library_path = env.get('LD_LIBRARY_PATH', '')
    env['LD_LIBRARY_PATH'] = f"{current_ld_library_path}:{gtsam_lib_path}"
    
    pct_planner_cmd = ExecuteProcess(
        cmd=['python3', pct_script_path, 
             '--scene', LaunchConfiguration('scene'), 
             '--robot_height', LaunchConfiguration('robot_height'),
             '--step_max', LaunchConfiguration('step_max')],
        cwd='/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/planner/scripts', # Important for relative imports
        output='screen',
        env=env
    )
    
    return LaunchDescription([
        scene_arg,
        robot_height_arg,
        step_max_arg,
        pct_planner_cmd
    ])

