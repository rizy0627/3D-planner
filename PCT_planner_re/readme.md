# env
Ubuntu 22.04.5 LTS
ROS2 humble
CuPy version: 13.6.0
CUDA available: True
GPU: b'NVIDIA GeForce RTX 5060 Laptop GPU'
NumPy: 1.26.4
SciPy: 1.11.4
Python: 3.10.12
cuda: 12.8
Open3D: 0.19.0

# build & install
cd ~/planner/pct_planner/PCT_planner-RC2026_Map_Planner/planner/

./build_thirdparty.sh

./build.sh

# rviz2
cd ~/planner/pct_planner/PCT_planner-RC2026_Map_Planner/rsc/rviz/

rviz2 -d /home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/rsc/rviz/pct_ros2.rviz

# 创建栅格地图，并传入机器人单步可达高度
cd /home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/tomography/scripts/

python tomography.py --scene building --step_max 0.40
python tomography.py --scene MAP --step_max 0.05

# 启动规划器planner
cd /home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/planner/scripts/

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/rizy/planner/pct_planner/PCT_planner-RC2026_Map_Planner/planner/lib/3rdparty/gtsam-4.1.1/install/lib

python plan.py --scene building
python plan.py --scene Map

# 使用rviz的publish point功能
导航，可在终端看到规划时间
