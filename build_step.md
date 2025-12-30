# 第一阶段：环境搭建与PCT全局规划闭环

目标：在RViz2中加载building2_9点云地图，运行PCT-planner生成路径，并让一个简单的球体机器人沿着这条路径移动（暂不考虑局部避障）。

## 任务 1：创建仿真与集成功能包

Prompt给Cursor:
请在 src 目录下创建一个新的ROS2 python功能包，命名为 nav_integration。

这个包将作为整个项目的集成中心。

在包中创建 launch、config、urdf 和 rviz 文件夹。

编写一个简单的 robot.urdf，模型为一个半径0.3米的红色球体（代表地面机器人），Base Link命名为 base_link。

### robot.urdf:
/home/rizy/planner/3d-navi/3d-navi-ros2_v1/src/nav_integration/urdf/robot.urdf

## 任务 2：地图加载与TF树构建

Prompt给Cursor:
在 nav_integration 包中编写一个节点 map_server.py。

读取 PCT_planner_re/rsc/pcd/building2_9.pcd 文件（路径需参数化）。

将PCD文件转换为 sensor_msgs/PointCloud2 并发布到 /global_map 话题，Frame ID设为 map。

发布一个静态TF变换：map -> odom (0,0,0)。

编写 bringup_map.launch.py，启动该节点并加载RViz2，在RViz中显示点云。

### test————加载地图和机器人
ros2 launch nav_integration bringup_map.launch.py

## 任务 3：规范化PCT-planner接口

Prompt给Cursor:
我需要修改 PCT_planner_re 中的代码，使其适配ROS2导航标准。

检查 PCT-planner 的输出话题。如果它输出的是自定义消息或非 nav_msgs/Path，请编写一个适配器节点（或直接修改源码）。

确保它发布的话题为 /pct/global_path，消息类型为 nav_msgs/msg/Path，Frame ID为 map。

编写一个Launch文件 run_pct.launch.py，加载 building2_9 对应的参数配置，并启动PCT规划器。

### test————
我已执行以下操作：
代码审查：检查了 PCT_planner_re/planner/scripts/plan.py 和 utils/vis_ros.py。
    发现原始代码已经使用 nav_msgs/msg/Path 消息类型，Frame ID 为 map。
    原始话题名为 /pct_path，我已将其修改为 /pct/global_path 以符合您的要求。
    同时修改了相关日志输出。
创建 Launch 文件：编写了 src/nav_integration/launch/run_pct.launch.py。
    由于 PCT_planner_re 并非标准的 ROS 2 包（缺少 package.xml），我使用 ExecuteProcess 直接运行 python 脚本。
    设置了正确的工作目录 (cwd) 以确保脚本内部的相对导入（如 sys.path.append('../')）正常工作。
    配置了 LD_LIBRARY_PATH 环境变量，包含 GTSAM 库路径，确保依赖库能被加载。
    提供了 scene（默认 Building）和 robot_height 参数。

colcon build --packages-select nav_integration --symlink-install

您可以运行以下命令启动 PCT 规划器（请保持之前的 bringup_map.launch.py 在另一个终端运行）：

ros2 launch nav_integration run_pct.launch.py

启动后，您可以在 RViz 中使用 "Publish Point" 工具在地图上依次点击起点和终点，规划器应该会生成路径并在 /pct/global_path 话题上发布。


## 任务 4：实现简单的路径跟踪控制器 (Path Follower)

Prompt给Cursor:
在 nav_integration 包中编写一个节点 simple_path_follower.py。

订阅 /pct/global_path 话题。

当接收到路径时，模拟机器人运动：以 0.5m/s 的恒定速度，沿着路径点插值移动。

实时发布 odom -> base_link 的TF变换，使URDF模型在RViz中移动。

注意：虽然是3D路径，但机器人应紧贴路径坐标（PCT规划出的路径应当已经包含了楼层高度信息）。

### test————
我已执行以下操作：
创建 Path Follower 节点：编写了 src/nav_integration/nav_integration/simple_path_follower.py。
    它订阅 /pct/global_path。
    收到路径后，以 0.5 m/s 的速度进行插值运动。
    实时发布 odom -> base_link 的 TF 变换。
更新 Map Server：注释掉了 map_server.py 中 odom -> base_link 的静态变换发布，以避免冲突。
构建：更新了 setup.py 并重新编译了功能包。
    现在，您需要手动运行这个跟随节点。建议的操作流程如下：

终端 1（重启）：
    ros2 launch nav_integration bringup_map.launch.py
（此时 RViz 中可能暂时看不到红色球体，因为它等待 odom -> base_link 的变换）
终端 2（新开）：
    ros2 run nav_integration simple_path_follower
（运行后，机器人应该会出现在原点 (0,0,0) 或上一次的位置）
终端 3（PCT 规划器）：
    ros2 launch nav_integration run_pct.launch.py
在 RViz 中操作：
点击 "Publish Point" 设定起点。
点击 "Publish Point" 设定终点。
规划成功后，机器人应该会自动沿着路径移动。

## 任务 5：第一阶段联合调试

Prompt给Cursor:
编写一个总的 simulation_phase1.launch.py。

启动地图发布节点。

启动 PCT-planner 节点。

启动 simple_path_follower 节点。

启动 RViz2，并配置好显示 RobotModel, Path, PointCloud2。

此时我应该能在RViz中使用 "2D Goal Pose" (或其他方式) 设定终点，看到球体沿着PCT规划的路径移动。

### 我已编写了 src/nav_integration/launch/simulation_phase1.launch.py，它将按顺序启动：
地图环境：bringup_map.launch.py（加载地图、机器人模型、RViz）。
PCT 规划器：run_pct.launch.py（加载 PCT 算法）。
路径跟随器：simple_path_follower 节点。
并已重新编译功能包。
现在，您只需运行一条命令即可启动整个仿真环境：
ros2 launch nav_integration simulation_phase1.launch.py

操作步骤：
启动后，RViz 会自动打开。
使用 RViz 工具栏中的 "Publish Point" 工具。
第一次点击地图上的任意位置（作为起点）。
第二次点击地图上的另一个位置（作为终点）。
您应该能看到蓝色的圆柱体机器人沿着规划出的路径移动。

#### 例如：加载 Spiral 场景，并将最大步长设置为 0.3，速度设置为 1.0
ros2 launch nav_integration simulation_phase1.launch.py scene:=Building step_max:=0.3 speed:=3.0