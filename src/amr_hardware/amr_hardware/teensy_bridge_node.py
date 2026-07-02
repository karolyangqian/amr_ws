import math
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from std_msgs.msg import Bool
from tf2_ros import TransformBroadcaster
import serial


class TeensyBridgeNode(Node):
    """
    Bridge antara NUC dan Teensy via satu port serial.

    Protokol Teensy → NUC:
        I ax ay az gx gy gz\\n   — data IMU (float, m/s² dan rad/s)
        E left_ticks right_ticks\\n — encoder ticks (int)

    Protokol NUC → Teensy:
        V left_rpm right_rpm\\n  — perintah kecepatan motor (int)
    """

    def __init__(self):
        super().__init__('teensy_bridge_node')

        self.declare_parameter('port',             '/dev/ttyACM0')
        self.declare_parameter('baud',             115200)
        self.declare_parameter('wheel_radius',     0.105)
        self.declare_parameter('wheel_separation', 0.58)
        self.declare_parameter('max_rpm',          150.0)
        self.declare_parameter('cpr',              16385)
        self.declare_parameter('cmd_vel_timeout',  0.5)
        self.declare_parameter('odom_frame',       'odom')
        self.declare_parameter('base_frame',       'base_link')
        self.declare_parameter('imu_frame',        'imu_link')
        self.declare_parameter('publish_tf',       False)

        port             = self.get_parameter('port').value
        baud             = self.get_parameter('baud').value
        self.R           = self.get_parameter('wheel_radius').value
        self.b           = self.get_parameter('wheel_separation').value
        self.max_rpm     = self.get_parameter('max_rpm').value
        self.cpr         = self.get_parameter('cpr').value
        self.timeout     = self.get_parameter('cmd_vel_timeout').value
        self.odom_frame  = self.get_parameter('odom_frame').value
        self.base_frame  = self.get_parameter('base_frame').value
        self.imu_frame   = self.get_parameter('imu_frame').value
        self.publish_tf_ = self.get_parameter('publish_tf').value

        self.ser = serial.Serial(port, baudrate=baud, timeout=0.1)
        self.get_logger().info(f'teensy_bridge_node started on {port} @ {baud}')

        # Odometry state
        self.x              = 0.0
        self.y              = 0.0
        self.theta          = 0.0
        self.last_tick_L    = None
        self.last_tick_R    = None
        self.last_odom_time = self.get_clock().now()

        # Motor command state
        self._cmd_L         = 0
        self._cmd_R         = 0
        self._last_cmd_time = self.get_clock().now()
        self._estop         = False
        self._lock          = threading.Lock()

        # Publishers
        self.imu_pub  = self.create_publisher(Imu,      '/imu/data', 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom',     10)
        if self.publish_tf_:
            self.tf_broadcaster = TransformBroadcaster(self)

        # Subscriptions
        self.create_subscription(Twist, '/cmd_vel',        self._cmd_vel_cb, 10)
        self.create_subscription(Twist, '/cmd_vel_raw',    self._cmd_vel_cb, 10)
        self.create_subscription(Bool,  '/emergency_stop', self._estop_cb,   10)

        # Timers
        self.create_timer(0.02, self._send_cmd)     # 50 Hz kirim perintah motor
        self.create_timer(0.1,  self._safety_check) # timeout watchdog

        # Thread baca serial (non-blocking terhadap ROS spin)
        self._running     = True
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    # ------------------------------------------------------------------ cmd_vel

    def _cmd_vel_cb(self, msg: Twist):
        self._last_cmd_time = self.get_clock().now()
        if self._estop:
            return
        v_L = msg.linear.x - msg.angular.z * (self.b / 2.0)
        v_R = msg.linear.x + msg.angular.z * (self.b / 2.0)
        rpm_L = v_L / (2.0 * math.pi * self.R) * 60.0
        rpm_R = v_R / (2.0 * math.pi * self.R) * 60.0
        rpm_L = max(-self.max_rpm, min(self.max_rpm, rpm_L))
        rpm_R = max(-self.max_rpm, min(self.max_rpm, rpm_R))
        with self._lock:
            # Sign convention: maju = L negatif, R positif (sama seperti ZLAC sebelumnya)
            self._cmd_L = int(-rpm_L)
            self._cmd_R = int(rpm_R)

    def _estop_cb(self, msg: Bool):
        self._estop = msg.data
        if msg.data:
            with self._lock:
                self._cmd_L = 0
                self._cmd_R = 0

    def _safety_check(self):
        dt = (self.get_clock().now() - self._last_cmd_time).nanoseconds / 1e9
        if dt > self.timeout:
            with self._lock:
                self._cmd_L = 0
                self._cmd_R = 0

    def _send_cmd(self):
        with self._lock:
            cmd = f'V {self._cmd_L} {self._cmd_R}\n'
        try:
            self.ser.write(cmd.encode())
        except Exception as e:
            self.get_logger().warn(f'Serial write failed: {e}')

    # ------------------------------------------------------------------ serial reader

    def _read_loop(self):
        while self._running:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                parts = line.split()
                if not parts:
                    continue
                if parts[0] == 'I' and len(parts) == 7:
                    self._handle_imu(parts[1:])
                elif parts[0] == 'E' and len(parts) == 3:
                    self._handle_enc(parts[1:])
            except Exception as e:
                if self._running:
                    self.get_logger().warn(f'Serial read error: {e}')

    # ------------------------------------------------------------------ IMU

    def _handle_imu(self, parts):
        ax, ay, az, gx, gy, gz = map(float, parts)
        msg = Imu()
        msg.header.stamp    = self.get_clock().now().to_msg()
        msg.header.frame_id = self.imu_frame
        msg.linear_acceleration.x = ax
        msg.linear_acceleration.y = ay
        msg.linear_acceleration.z = az
        msg.angular_velocity.x    = gx
        msg.angular_velocity.y    = gy
        msg.angular_velocity.z    = gz
        msg.orientation.w = 1.0
        msg.orientation_covariance[0]       = -1.0
        msg.angular_velocity_covariance[0]  = 0.004
        msg.angular_velocity_covariance[4]  = 0.004
        msg.angular_velocity_covariance[8]  = 0.004
        msg.linear_acceleration_covariance[0] = 0.1
        msg.linear_acceleration_covariance[4] = 0.1
        msg.linear_acceleration_covariance[8] = 0.1
        self.imu_pub.publish(msg)

    # ------------------------------------------------------------------ Encoder / Odom

    def _handle_enc(self, parts):
        tick_L = int(parts[0])
        tick_R = int(parts[1])

        if self.last_tick_L is None:
            self.last_tick_L = tick_L
            self.last_tick_R = tick_R
            return

        now = self.get_clock().now()
        dt  = (now - self.last_odom_time).nanoseconds / 1e9
        if dt <= 0.0:
            return
        self.last_odom_time = now

        delta_L = tick_L - self.last_tick_L
        delta_R = tick_R - self.last_tick_R
        self.last_tick_L = tick_L
        self.last_tick_R = tick_R

        m_per_tick  = (2.0 * math.pi * self.R) / self.cpr
        dist_L      = -delta_L * m_per_tick   # sign: maju = L_tick turun
        dist_R      =  delta_R * m_per_tick

        delta_s     = (dist_L + dist_R) * 0.5
        delta_theta = (dist_R - dist_L) / self.b

        theta_mid  = self.theta + delta_theta * 0.5
        self.x    += delta_s * math.cos(theta_mid)
        self.y    += delta_s * math.sin(theta_mid)
        self.theta = theta_mid + delta_theta * 0.5

        v   = delta_s / dt
        w   = delta_theta / dt
        q_z = math.sin(self.theta * 0.5)
        q_w = math.cos(self.theta * 0.5)

        if self.publish_tf_:
            t = TransformStamped()
            t.header.stamp            = now.to_msg()
            t.header.frame_id         = self.odom_frame
            t.child_frame_id          = self.base_frame
            t.transform.translation.x = self.x
            t.transform.translation.y = self.y
            t.transform.translation.z = 0.0
            t.transform.rotation.z    = q_z
            t.transform.rotation.w    = q_w
            self.tf_broadcaster.sendTransform(t)

        odom = Odometry()
        odom.header.stamp    = now.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id  = self.base_frame
        odom.pose.pose.position.x    = self.x
        odom.pose.pose.position.y    = self.y
        odom.pose.pose.orientation.z = q_z
        odom.pose.pose.orientation.w = q_w
        odom.pose.covariance[0]  = 0.01
        odom.pose.covariance[7]  = 0.01
        odom.pose.covariance[14] = 1e9
        odom.pose.covariance[21] = 1e9
        odom.pose.covariance[28] = 1e9
        odom.pose.covariance[35] = 0.01
        odom.twist.twist.linear.x  = v
        odom.twist.twist.angular.z = w
        odom.twist.covariance[0]  = 0.01
        odom.twist.covariance[7]  = 1e9
        odom.twist.covariance[14] = 1e9
        odom.twist.covariance[21] = 1e9
        odom.twist.covariance[28] = 1e9
        odom.twist.covariance[35] = 0.01
        self.odom_pub.publish(odom)

    # ------------------------------------------------------------------ shutdown

    def destroy_node(self):
        self._running = False
        try:
            self.ser.write(b'V 0 0\n')
            self.ser.close()
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = TeensyBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
