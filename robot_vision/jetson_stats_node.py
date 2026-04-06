"""
jetson_stats_node.py
ROS2 node that reads Jetson hardware stats via jtop and publishes them as:

  /jetson/diagnostics   diagnostic_msgs/DiagnosticArray  (all stats, 1 Hz)
  /jetson/cpu_percent   std_msgs/Float32MultiArray        (per-core %, index = core #)
  /jetson/gpu_percent   std_msgs/Float32               (overall GPU load %)
  /jetson/memory_used_mb std_msgs/Float32              (used RAM in MB)
  /jetson/memory_total_mb std_msgs/Float32             (total RAM in MB)
  /jetson/temp/cpu      std_msgs/Float32               (CPU zone temp °C)
  /jetson/temp/gpu      std_msgs/Float32               (GPU zone temp °C)
  /jetson/temp/soc      std_msgs/Float32               (SoC zone temp °C)
  /jetson/power_mw      std_msgs/Float32               (total board power mW)
  /jetson/uptime_s      std_msgs/Float32               (system uptime seconds)

The jtop service must be running:
    sudo systemctl enable jtop
    sudo systemctl start jtop
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy

from std_msgs.msg import Float32, Float32MultiArray
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

from jtop import jtop, JtopException


class JetsonStatsNode(Node):
    def __init__(self):
        super().__init__('jetson_stats')

        # Parameters
        self.declare_parameter('publish_rate_hz', 1.0)
        rate_hz = self.get_parameter('publish_rate_hz').value
        period_s = 1.0 / rate_hz

        # Use BEST_EFFORT so slow stats don't block other nodes
        qos = QoSProfile(
            depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        # Publishers
        self._pub_diag    = self.create_publisher(DiagnosticArray,     '/jetson/diagnostics',    qos)
        self._pub_cpu     = self.create_publisher(Float32MultiArray,    '/jetson/cpu_percent',    qos)
        self._pub_gpu     = self.create_publisher(Float32,              '/jetson/gpu_percent',    qos)
        self._pub_mem_u   = self.create_publisher(Float32,              '/jetson/memory_used_mb', qos)
        self._pub_mem_t   = self.create_publisher(Float32,              '/jetson/memory_total_mb',qos)
        self._pub_t_cpu   = self.create_publisher(Float32,              '/jetson/temp/cpu',       qos)
        self._pub_t_gpu   = self.create_publisher(Float32,              '/jetson/temp/gpu',       qos)
        self._pub_t_soc   = self.create_publisher(Float32,              '/jetson/temp/soc',       qos)
        self._pub_t_tj    = self.create_publisher(Float32,              '/jetson/temp/tj',        qos)
        self._pub_power   = self.create_publisher(Float32,              '/jetson/power_mw',       qos)
        self._pub_uptime  = self.create_publisher(Float32,              '/jetson/uptime_s',       qos)

        # Run jtop at 2x publish rate so it always has fresh data ready when we publish.
        # We attach a callback so jtop calls _on_jtop_update() on every confirmed refresh;
        # a separate throttle counter ensures we only publish at the requested rate.
        jtop_interval = max(0.1, period_s / 2.0)
        self._publish_every_n = max(1, round(period_s / jtop_interval))  # e.g. 2 for 1 Hz / 0.5s
        self._jtop_tick = 0

        self._jetson = jtop(interval=jtop_interval)
        self._jetson.attach(self._on_jtop_update)
        try:
            self._jetson.start()
            self.get_logger().info(
                f'jtop started — board: {self._jetson.board.get("hardware", {}).get("Module", "Jetson")}, '
                f'interval={jtop_interval}s, publishing every {self._publish_every_n} ticks'
            )
        except JtopException as e:
            self.get_logger().error(f'Failed to connect to jtop service: {e}')
            raise

        self.get_logger().info(f'jetson_stats_node running at {rate_hz} Hz')

    # ------------------------------------------------------------------
    def _on_jtop_update(self, jetson):
        """Called by jtop on every confirmed data refresh — data is always valid here."""
        self._jtop_tick += 1
        if self._jtop_tick % self._publish_every_n != 0:
            return  # skip intermediate ticks; only publish at the requested rate

        now = self.get_clock().now().to_msg()
        stats = jetson.stats   # flat dict snapshot

        # ---- CPU -------------------------------------------------------
        cpu_data = jetson.cpu
        # cpu_data is a dict with keys: 'total' (dict) and core keys like 'cpu1', 'cpu2', ...
        total_cpu = cpu_data.get('total', {})
        core_loads = []
        for key in sorted(cpu_data.keys()):
            if key.startswith('cpu') and key != 'total':
                core = cpu_data[key]
                if isinstance(core, dict):
                    core_loads.append(float(core.get('val', 0.0)))

        cpu_msg = Float32MultiArray()
        cpu_msg.data = core_loads if core_loads else [float(total_cpu.get('val', 0.0))]
        self._pub_cpu.publish(cpu_msg)

        # ---- GPU -------------------------------------------------------
        gpu_data = jetson.gpu
        # gpu_data is a dict of named GPUs e.g. {'gpu': {'val': 42, ...}}
        gpu_val = 0.0
        for gname, ginfo in gpu_data.items():
            if isinstance(ginfo, dict) and 'val' in ginfo:
                gpu_val = float(ginfo['val'])
                break
        self._pub_gpu.publish(Float32(data=gpu_val))

        # ---- Memory ----------------------------------------------------
        mem = jetson.memory
        ram = mem.get('RAM', {})
        used_mb  = float(ram.get('used', 0)) / 1024.0
        total_mb = float(ram.get('tot',  0)) / 1024.0
        self._pub_mem_u.publish(Float32(data=used_mb))
        self._pub_mem_t.publish(Float32(data=total_mb))

        # ---- Temperatures ----------------------------------------------
        # jtop callback guarantees data is fresh — no caching needed
        temps = jetson.temperature
        def _get_temp(keys):
            for k in keys:
                if k in temps:
                    v = temps[k]
                    val = float(v.get('temp', 0.0)) if isinstance(v, dict) else float(v)
                    if val > 0.0:
                        return val
            return 0.0

        self._pub_t_cpu.publish(Float32(data=_get_temp(['cpu', 'CPU', 'cpu-thermal'])))
        self._pub_t_gpu.publish(Float32(data=_get_temp(['gpu', 'GPU', 'gpu-thermal'])))
        self._pub_t_soc.publish(Float32(data=_get_temp(['soc0', 'soc', 'SOC0', 'soc-thermal'])))
        self._pub_t_tj.publish(Float32(data=_get_temp(['tj', 'Tj', 'TJ'])))

        # ---- Power -----------------------------------------------------
        power = jetson.power
        # power['tot'] is total in mW
        total_power_mw = 0.0
        if isinstance(power, dict):
            tot = power.get('tot', {})
            if isinstance(tot, dict):
                total_power_mw = float(tot.get('power', 0.0))
            elif isinstance(tot, (int, float)):
                total_power_mw = float(tot)
        self._pub_power.publish(Float32(data=total_power_mw))

        # ---- Uptime ----------------------------------------------------
        uptime_val = stats.get('uptime', 0.0)
        if hasattr(uptime_val, 'total_seconds'):
            uptime_s = uptime_val.total_seconds()
        else:
            uptime_s = float(uptime_val)
        self._pub_uptime.publish(Float32(data=uptime_s))

        # ---- DiagnosticArray -------------------------------------------
        status = DiagnosticStatus()
        status.level   = DiagnosticStatus.OK
        status.name    = 'Jetson Stats'
        status.message = 'nominal'
        status.hardware_id = 'jetson_orin_nano'
        status.values = [
            KeyValue(key='cpu_total_%',        value=str(round(float(total_cpu.get('val', 0.0)), 1))),
            KeyValue(key='gpu_%',              value=str(round(gpu_val, 1))),
            KeyValue(key='ram_used_mb',        value=str(round(used_mb, 0))),
            KeyValue(key='ram_total_mb',       value=str(round(total_mb, 0))),
            KeyValue(key='temp_cpu_c',         value=str(round(_get_temp(['cpu', 'CPU', 'cpu-thermal']), 1))),
            KeyValue(key='temp_gpu_c',         value=str(round(_get_temp(['gpu', 'GPU', 'gpu-thermal']), 1))),
            KeyValue(key='temp_soc0_c',        value=str(round(_get_temp(['soc0', 'soc', 'SOC0']), 1))),
            KeyValue(key='temp_tj_c',          value=str(round(_get_temp(['tj', 'Tj', 'TJ']), 1))),
            KeyValue(key='power_total_mw',     value=str(round(total_power_mw, 0))),
            KeyValue(key='uptime_s',           value=str(round(uptime_s, 0))),
        ]
        # Warn if Tjunction > 85°C (Orin Nano thermal throttle threshold)
        tj_val = _get_temp(['tj', 'Tj', 'TJ'])
        if tj_val > 85.0:
            status.level   = DiagnosticStatus.WARN
            status.message = f'temp_tj_c = {round(tj_val, 1)}°C — approaching throttle'

        diag = DiagnosticArray()
        diag.header.stamp = now
        diag.status = [status]
        self._pub_diag.publish(diag)

    # ------------------------------------------------------------------
    def destroy_node(self):
        self.get_logger().info('Stopping jtop...')
        try:
            self._jetson.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = JetsonStatsNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
