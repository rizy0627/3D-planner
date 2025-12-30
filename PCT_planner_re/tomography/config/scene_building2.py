from .scene import Scene


class SceneBuilding2(Scene):
    def __init__(self):
        self.pcd.file_name = 'building2_10.pcd'

        self.map.resolution = 0.10
        self.map.ground_h = 0.0
        self.map.slice_dh = 0.5

        self.trav.kernel_size = 7
        self.trav.interval_min = 0.50
        self.trav.interval_free = 0.65
        self.trav.slope_max = 0.40
        self.trav.step_max = 0.3
        self.trav.standable_ratio = 0.50
        self.trav.cost_barrier = 50.0
        self.trav.safe_margin = 0.2
        self.trav.inflation = 0.2

