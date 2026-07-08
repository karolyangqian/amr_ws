import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool
import time
import math


class CmdVelInverterNode(Node):
    """
    Menerima perintah Nav2 di /cmd_vel_nav2 (konvensi ROS standar),
    membalik linear.x DAN angular.z dengan profil S-curve (karena Teensy firmware punya konvensi
    terbalik: +linear = mundur, +angular = kanan),
    lalu publish ke /cmd_vel yang disubscribe Teensy.

    Teleop tidak melewati node ini — teleop publish langsung ke /cmd_vel
    dengan konvensi yang sudah disesuaikan.

    Juga menerima /emergency_stop (Bool) — jika True, kirim zero Twist
    untuk menghentikan robot sampai estop dicabut.
    """

    def __init__(self):
        super().__init__('cmd_vel_inverter_node')

        self._estop = False

        # --- KONFIGURASI S-CURVE (Sesuaikan dengan beban AMR Anda) ---
        self.MAX_ACCEL = 0.5   # Maksimum akselerasi (m/s^2 atau rad/s^2)
        self.MAX_JERK  = 1.0   # Maksimum jerk (m/s^3 atau rad/s^3) -> Mengontrol kelembutan kurva S

        # State internal untuk profil kecepatan
        self.current_lin_v = 0.0
        self.current_lin_a = 0.0
        self.current_ang_v = 0.0
        self.current_ang_a = 0.0

        # Target velocities (setelah di-invert)
        self.target_lin_v = 0.0
        self.target_ang_v = 0.0

        # Subscriptions & Publishers
        self.create_subscription(Twist, '/cmd_vel_nav2',      self._cmd_cb,   10)
        self.create_subscription(Bool,  '/emergency_stop',    self._estop_cb, 10)
        self._pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Timer internal untuk kalkulasi berkala S-Curve (50 Hz = Jeda 0.02s)
        self.loop_rate = 50.0 
        self.last_time = self.get_clock().now()
        self.create_timer(1.0 / self.loop_rate, self._scurve_timer_cb)

        self.get_logger().info(
            'cmd_vel_inverter_node started dengan S-Curve Profiler (50Hz) — '
            '/cmd_vel_nav2 → S-Curve Invert → /cmd_vel')

    def _estop_cb(self, msg: Bool):
        self._estop = msg.data
        if self._estop:
            self.get_logger().warn("EMERGENCY STOP AKTIF! Menurunkan kecepatan dengan S-Curve ke 0.")
            # Langsung paksa target ke nol, S-curve timer yang akan melakukan deselerasi mulus
            self.target_lin_v = 0.0
            self.target_ang_v = 0.0

    def _cmd_cb(self, msg: Twist):
        if self._estop:
            self.target_lin_v = 0.0
            self.target_ang_v = 0.0
            return

        # Koreksi arah inversi ZLAC/Teensy di sini
        self.target_lin_v = msg.linear.x * -1.0
        self.target_ang_v = msg.angular.z * -1.0

    def _scurve_timer_cb(self):
        """Timer loop untuk update kecepatan berdasarkan kalkulasi matematika S-Curve"""
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        # Jika dt tidak valid atau terlalu besar (misal saat startup), skip satu frame
        if dt <= 0.0 or dt > 0.1:
            return

        # Hitung S-Curve terpisah untuk Linear dan Angular
        self.current_lin_v, self.current_lin_a = self._calculate_scurve_step(
            self.current_lin_v, self.current_lin_a, self.target_lin_v, dt
        )
        self.current_ang_v, self.current_ang_a = self._calculate_scurve_step(
            self.current_ang_v, self.current_ang_a, self.target_ang_v, dt
        )

        # Publish kecepatan hasil S-Curve ke Teensy
        out = Twist()
        out.linear.x  = self.current_lin_v
        out.angular.z = self.current_ang_v
        self._pub.publish(out)

    def _calculate_scurve_step(self, v_curr, a_curr, v_target, dt):
        """Kalkulator numerik S-Curve (Jerk -> Accel -> Velocity)"""
        # 1. Hitung sisa jarak kecepatan yang harus ditempuh
        v_diff = v_target - v_curr

        if abs(v_diff) < 1e-4 and abs(a_curr) < 1e-4:
            return v_target, 0.0

        # 2. Tentukan arah jerk ideal (apakah harus menambah akselerasi atau mengerem akselerasi)
        # Menghitung sisa waktu pengereman akselerasi yang aman sebelum menyentuh v_target
        stopping_v = (a_curr * a_curr) / (2.0 * self.MAX_JERK)

        if v_diff > 0:
            if v_diff > stopping_v:
                jerk = self.MAX_JERK if a_curr < self.MAX_ACCEL else 0.0
            else:
                jerk = -self.MAX_JERK if a_curr > 0.0 else 0.0
        else:
            if abs(v_diff) > stopping_v:
                jerk = -self.MAX_JERK if a_curr > -self.MAX_ACCEL else 0.0
            else:
                jerk = self.MAX_JERK if a_curr < 0.0 else 0.0

        # 3. Integrasikan Jerk ke Akselerasi
        a_next = a_curr + jerk * dt
        
        # Batasi sesuai batas batas MAX_ACCEL
        if a_next > self.MAX_ACCEL: a_next = self.MAX_ACCEL
        if a_next < -self.MAX_ACCEL: a_next = -self.MAX_ACCEL

        # 4. Integrasikan Akselerasi ke Kecepatan
        v_next = v_curr + a_next * dt

        # Antisipasi overshoot kecil akibat pembulatan numerik digital
        if (v_diff > 0 and v_next > v_target) or (v_diff < 0 and v_next < v_target):
            v_next = v_target
            a_next = 0.0

        return v_next, a_next

def main(args=None):
    rclpy.init(args=args)
    node = CmdVelInverterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Kirim zero twist saat node mati demi keamanan hardware
        node._pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
