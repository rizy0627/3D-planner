cd /home/rizy/planner/ego-planner-swarm/ego-planner-swarm-ros2_version
rm -rf build/ install/ log/
colcon build --symlink-install

#运行
source install/setup.bash
ros2 launch ego_planner rviz.launch.py 

# 新开一个终端，输入以下指令

## 单机
ros2 launch ego_planner single_run_in_sim.launch.py 

## swarm
ros2 launch ego_planner swarm.launch.py 

## large swarm
ros2 launch ego_planner swarm_large.launch.py  

## 附加参数，可以选择地图生成模式以及是否考虑动力学
### use_mockamap:地图生成方式，默认为False，False时使用Random Forest, True时使用mockamap
### use_dynamic:是否考虑动力学，默认为False, False时不考虑, True时考虑
ros2 launch ego_planner single_run_in_sim.launch.py use_mockamap:=True use_dynamic:=False

ros2 launch nav_integration simulation_phase1.launch.py