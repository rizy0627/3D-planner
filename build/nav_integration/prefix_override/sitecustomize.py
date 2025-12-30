import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/rizy/planner/3d-navi/3d-navi-ros2_v1/install/nav_integration'
