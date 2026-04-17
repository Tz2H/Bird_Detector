"""Chart manager for updating the Matplotlib density chart."""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

class ChartManager:
    def __init__(self, fig, ax, canvas):
        self.fig = fig
        self.ax = ax
        self.canvas = canvas

    def update_density_chart(self, recognition_data, density_classes):
        """Redraw the density chart using buffered samples."""
        self.ax.clear()

        # Set dark theme styling
        self.ax.set_facecolor("#171A21")
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_color("#292D3E")
        self.ax.spines['bottom'].set_color("#292D3E")
        self.ax.tick_params(colors="#64748B")

        if not recognition_data or not density_classes:
            self.ax.set_title("数量密度分布（暂无数据）", fontsize=15, fontweight="600", color="#F8FAFC", pad=12)
            self.canvas.draw()
            return

        timestamps = [item[0] for item in recognition_data]
        plot_classes = sorted(list(density_classes))

        from collections import defaultdict
        class_time_count = defaultdict(list)
        for _, _, frame_classes in recognition_data:
            for cls in plot_classes:
                class_time_count[cls].append(frame_classes.get(cls, 0))

        valid_classes = [cls for cls in plot_classes if any(class_time_count[cls])]
        
        if not valid_classes:
            self.ax.set_title("数量密度分布（暂无数据）", fontsize=15, fontweight="600", color="#F8FAFC", pad=12)
            self.canvas.draw()
            return

        import matplotlib
        if hasattr(matplotlib, "colormaps"):
            color_map = matplotlib.colormaps.get_cmap("tab10").resampled(max(1, len(valid_classes)))
            for i, cls in enumerate(valid_classes):
                self.ax.plot(timestamps, class_time_count[cls], label=cls, linewidth=2.5, marker="o", markersize=7, color=color_map(i))
        else:
            import matplotlib.cm as cm
            color_map = cm.get_cmap("tab10", max(1, len(valid_classes)))
            for i, cls in enumerate(valid_classes):
                color = color_map(i) if hasattr(color_map, "__call__") else color_map.colors[i]
                self.ax.plot(timestamps, class_time_count[cls], label=cls, linewidth=2.5, marker="o", markersize=7, color=color)

        self.ax.set_xlabel("时间", fontsize=12, color="#94A3B8")
        self.ax.set_ylabel("数量", fontsize=12, color="#94A3B8")
        self.ax.set_title("数量密度分布", fontsize=15, fontweight="600", color="#F8FAFC", pad=12)
        self.ax.grid(True, linestyle=":", alpha=0.15, color="#F8FAFC")

        locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
        formatter = mdates.ConciseDateFormatter(locator)
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)
        self.fig.autofmt_xdate(rotation=30)

        legend = self.ax.legend(fontsize=12, loc="upper left", frameon=True, fancybox=True, shadow=True)
        if legend:
            legend.get_frame().set_facecolor("#1E2330")
            legend.get_frame().set_edgecolor("#292D3E")
            for text in legend.get_texts():
                text.set_color("#CBD5E1")

        self.fig.tight_layout()
        self.canvas.draw()
