"""Chart manager for updating the Matplotlib density chart."""

import matplotlib.dates as mdates


class ChartManager:
    def __init__(self, fig, ax, canvas):
        self.fig = fig
        self.ax = ax
        self.canvas = canvas

    def update_heatmap_chart(self, heatmap_points, heatmap_classes):
        """Redraw the spatial heatmap using detected object points."""
        self.ax.clear()

        # Set dark theme styling
        self.ax.set_facecolor("#171A21")
        self.fig.patch.set_facecolor("#171A21")
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_color("#292D3E")
        self.ax.spines["bottom"].set_color("#292D3E")
        self.ax.tick_params(colors="#64748B")

        self.ax.set_xlim(0, 640)
        self.ax.set_ylim(640, 0) # Real world image coordinates
        
        if not heatmap_points or not heatmap_classes:
            self.ax.set_title(
                "空间热力分布（暂无数据）",
                fontsize=15,
                fontweight="600",
                color="#F8FAFC",
                pad=12,
            )
            self.canvas.draw()
            return
            
        xs = []
        ys = []
        for point in heatmap_points:
            if point["class"] in heatmap_classes:
                xs.append(point["x"])
                ys.append(point["y"])
                
        if not xs:
            self.ax.set_title(
                "空间热力分布（暂无数据）",
                fontsize=15,
                fontweight="600",
                color="#F8FAFC",
                pad=12,
            )
            self.canvas.draw()
            return

        hb = self.ax.hexbin(xs, ys, gridsize=30, cmap='magma', mincnt=1, edgecolors='none')

        self.ax.set_xlabel("X 坐标", fontsize=12, color="#94A3B8")
        self.ax.set_ylabel("Y 坐标", fontsize=12, color="#94A3B8")
        self.ax.set_title(
            "空间热力分布", fontsize=15, fontweight="600", color="#F8FAFC", pad=12
        )
        self.ax.grid(True, linestyle=":", alpha=0.15, color="#F8FAFC")

        self.fig.tight_layout()
        self.canvas.draw()
