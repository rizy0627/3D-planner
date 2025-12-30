PCT Planner 流程图说明
=====================

文件：
- [plan_flowchart.dot](plan_flowchart.dot)

渲染方法（需要安装 Graphviz）：

```bash
sudo apt update
sudo apt install -y graphviz
dot -Tpng /home/rizy/planner/pct_planner/PCT_planner-RC2026_Map_Planner/planner/docs/flowchart/plan_flowchart.dot -o /home/rizy/planner/pct_planner/PCT_planner-RC2026_Map_Planner/planner/docs/flowchart/plan_flowchart.png
dot -Tsvg planner/docs/flowchart/plan_flowchart.dot -o planner/docs/flowchart/plan_flowchart.svg
```

流程要点：
- 加载 tomogram（.pickle），解析可通行性与高度数据
- 初始化规划器并进行 gateway（台阶）检测
- 等待 RViz 点击获得起点/终点，将世界坐标转换为网格索引
- 调用 `planner.plan`（内部执行 A* 搜索）寻找路径
- 若未找到路径返回失败；若找到，获取轨迹优化器（GPMP 或 Quintic）
- 提取并组装轨迹数据，转换为地图坐标后返回 3D 路径

附：ASCII 版简要流程图

Start -> Load Tomogram -> Init Planner -> Wait for clicks -> pos2idx -> planner.plan (A*)
    -> [Found?] --No--> Fail (return None)
                     --Yes--> Get optimizer -> extract results -> assemble traj_3d
                                -> transTrajGrid2Map -> return traj_3d
