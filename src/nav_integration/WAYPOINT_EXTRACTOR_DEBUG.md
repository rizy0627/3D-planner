# Waypoint Extractor 调试指南

## 问题诊断

你遇到的问题是：不可以在楼梯前和拐角处添加采样点。

## 修改内容

### 1. 新增参数

```python
'corner_min_distance': 0.3  # 拐角点的最小添加距离（从0.5降到0.3）
'lookahead': 5              # 曲率检测前视野（原来只检查相邻点，现在检查5个点）
'z_change_threshold': 0.5   # 高度变化阈值（检测楼梯/电梯）
```

### 2. 算法改进

**原算法局限：**
- 只检查 `i-1, i, i+1` 三个点，对高密度路径（0.05m间隔）不够
- 拐点距离要求 0.5m，很多楼梯起点和尖拐角被忽略
- 只有局部pitch变化检测，楼梯（连续斜坡）难以识别

**新算法改进：**
1. **Lookahead 窗口**：检查 `i-5, i, i+5` 的向量角度，检测真正的曲线拐角
2. **高度变化检测**：检查前后5个点的Z轴差值，超过0.5m标记为楼梯起点
3. **降低拐点距离**：从0.5m降到0.3m，捕获更多关键点

## 测试方法

### 方法1：启动完整测试

```bash
cd /home/rizy/planner/3d-navi/3d-navi-ros2_v1
source install/setup.bash

# 启动测试
ros2 launch nav_integration test_waypoint_extractor.launch.py scene:=Building
```

### 方法2：单独测试航路点提取器

```bash
# 终端1：启动PCT planner发布路径
cd /home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/planner/scripts
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/rizy/planner/3d-navi/3d-navi-ros2_v1/PCT_planner_re/planner/lib/3rdparty/gtsam-4.1.1/install/lib
python3 plan.py --scene Building

# 终端2：测试不同参数
ros2 run nav_integration waypoint_extractor __params:=src/nav_integration/config/waypoint_extractor_params.yaml
```

## 调试策略

### 调试参数1：降低 min_spacing
如果航路点太少，降低最小间距：

```bash
ros2 param set /waypoint_extractor min_spacing 2.0
```

### 调试参数2：降低 corner_min_distance
如果拐角仍无航路点，进一步降低：

```bash
ros2 param set /waypoint_extractor corner_min_distance 0.2
```

### 调试参数3：降低 z_change_threshold
如果楼梯检测不到，降低高度阈值：

```bash
ros2 param set /waypoint_extractor z_change_threshold 0.3
```

### 调试参数4：增加 lookahead
如果拐角检测不准确，增加前视野：

```bash
ros2 param set /waypoint_extractor lookahead 10
```

## 验证步骤

### 1. 观察RViz可视化

在RViz中应该看到：
- 红色线：原始全局路径（PCT输出，密集）
- 绿色球：提取的航路点
- 文字标记：航路点编号

### 2. 检查终端输出

终端应该显示：
```
[waypoint_extractor]: Extracted X waypoints from Y raw points.
[waypoint_extractor]: Waypoints: [x1, y1, z1], [x2, y2, z2], ...
```

### 3. 对比关键点

在RViz中测量：
- 楼梯起点前是否有航路点
- 拐角处是否有航路点
- 平直段航路点间距是否合理

## 常见问题

### Q1: 楼梯前仍然没有航路点

**可能原因：**
1. 高度变化太小（<0.5m）
2. 路径过于平滑

**解决方法：**
```bash
# 降低阈值到0.2m
ros2 param set /waypoint_extractor z_change_threshold 0.2

# 或者直接修改 launch 文件
```

### Q2: 航路点太多

**可能原因：**
1. min_spacing 设置过小
2. 频繁的小拐角被检测

**解决方法：**
```bash
# 增加最小间距
ros2 param set /waypoint_extractor min_spacing 5.0

# 增加拐角限制
ros2 param set /waypoint_extractor corner_min_distance 1.0
```

### Q3: 航路点分布不均匀

**可能原因：**
1. 拐角检测过于敏感
2. 高度变化阈值过小

**解决方法：**
```bash
# 检查日志中的拐角检测结果
ros2 topic echo /waypoint_extractor/diagnostics --once
```

## 推荐参数配置

### 场景1：多层建筑（楼梯多）
```yaml
min_spacing: 2.5
angle_threshold_deg: 30.0
pitch_threshold_deg: 15.0
corner_min_distance: 0.25
lookahead: 5
z_change_threshold: 0.4
```

### 场景2：单层平地（拐角多）
```yaml
min_spacing: 3.0
angle_threshold_deg: 25.0
pitch_threshold_deg: 20.0
corner_min_distance: 0.3
lookahead: 8
z_change_threshold: 0.5
```

### 场景3：复杂环境（楼梯+拐角）
```yaml
min_spacing: 2.0
angle_threshold_deg: 20.0
pitch_threshold_deg: 10.0
corner_min_distance: 0.2
lookahead: 5
z_change_threshold: 0.3
```

## 高级调试：查看中间结果

添加临时调试代码查看哪些点被标记为拐点：

在 `extract_waypoints` 函数中添加：

```python
# 在 Pass 1 结束后添加
self.get_logger().info(f"Detected {len(corner_indices)} corner points")
for idx in sorted(list(corner_indices))[:5]:  # 打印前5个
    p = path_points[idx]
    self.get_logger().info(f"  Corner at index {idx}: [{p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}]")
```

重新编译并运行：
```bash
colcon build --packages-select nav_integration
source install/setup.bash
ros2 launch nav_integration test_waypoint_extractor.launch.py
```

## 预期效果

### 正常情况

```
[waypoint_extractor]: Received path with 123 points
[waypoint_extractor]: Detected 15 corner points (including 3 stair starts)
[waypoint_extractor]: Extracted 8 waypoints from 123 raw points.
[waypoint_extractor]: Waypoints: [0.0, 0.0, 0.5], [2.8, 1.2, 0.5], [5.1, 2.8, 1.0], ...
```

### 在RViz中观察

- 平直段：每2.5-3m一个航路点
- 楼梯起点：高度突变处有绿色球
- 拐角处：方向变化大处有绿色球
- 终点：最后一个绿色球在目标位置

## 下一步

如果这个版本仍然不满足需求，可以考虑：

1. **Douglas-Peucker算法**：更智能的曲线简化
2. **基于曲率的自适应采样**：高曲率区域增加采样
3. **语义信息**：利用地图的分层数据，在楼层切换处强制添加航路点

请先测试当前版本，并告诉我：
- 航路点数量是否合理？
- 楼梯前是否有航路点？
- 拐角处是否有航路点？
