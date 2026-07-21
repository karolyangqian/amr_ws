#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import time
import math

def create_pose(navigator, x, y, yaw_deg):
    """Fungsi bantuan untuk membuat koordinat pose dengan mudah"""
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = x
    pose.pose.position.y = y
    
    # Konversi manual Yaw (derajat) ke Quaternion
    yaw_rad = math.radians(yaw_deg)
    pose.pose.orientation.w = math.cos(yaw_rad / 2.0)
    pose.pose.orientation.x = 0.0
    pose.pose.orientation.y = 0.0
    pose.pose.orientation.z = math.sin(yaw_rad / 2.0)
    
    return pose

def main():
    rclpy.init()

    # Inisialisasi Navigator Nav2
    navigator = BasicNavigator()

    # print("Menunggu sistem Nav2 & SLAM stabil (5 detik)...")
    print("Waiting...")
    # Kita menggunakan sleep alih-alih waitUntilNav2Active() karena 
    # fungsi bawaan tersebut mencari 'amcl' (pembaca peta statis), padahal kita pakai SLAM.
    time.sleep(5.0)

    # print("Sistem Aktif! Memulai misi pemetaan otonom...")
    print("Ready!")
    
    # CATATAN PENTING:
    # Saat melakukan SLAM, robot SELALU mulai di koordinat (0, 0, 0)
    # Jadi kita TIDAK PERLU setInitialPose. Biarkan SLAM yang bekerja mengunci titik nol.

    # =========================================================
    # 1. DEFINISI TITIK STASIUN (Berdasarkan Peta Baru)
    # =========================================================
    stasiun = {
        'A': create_pose(navigator, x=6.8, y=-11.1, yaw_deg=0.0),    # Titik 1
        'B': create_pose(navigator, x=16.0,  y=-15.5,  yaw_deg=90.0),   # Titik 2
        'C': create_pose(navigator, x=-8.0,  y=18.0,  yaw_deg=180.0),  # Titik 3
        'G': create_pose(navigator, x=-24.6, y=-15.8, yaw_deg=-90.0)   # Titik 4 (Pulang/Akhir)
    }

    # =========================================================
    # 2. MISI HARI INI (URUTAN PENGIRIMAN)
    # =========================================================
    rute_misi = ['A', 'B', 'C', 'G']

    # print(f"Menerima rute misi: {rute_misi}")
    print("Mission Route: " + " -> ".join(rute_misi))

    for titik_tujuan in rute_misi:
        pose_tujuan = stasiun[titik_tujuan]
        
        # print(f"\n---> [MISI] Mengirim AMR ke Stasiun {titik_tujuan}...")
        print(f"Koordinat Target: (x: {pose_tujuan.pose.position.x:.2f}, y: {pose_tujuan.pose.position.y:.2f}, yaw: {math.degrees(math.atan2(pose_tujuan.pose.orientation.z, pose_tujuan.pose.orientation.w)):.1f}°)")
        navigator.goToPose(pose_tujuan)

        # Loop untuk memantau perjalanan robot
        while not navigator.isTaskComplete():
            feedback = navigator.getFeedback()
            if feedback:
                # print(f"Sisa Jarak ke {titik_tujuan}: {feedback.distance_remaining:.2f} meter", end='\r')
                print(f"Distance to {titik_tujuan}: {feedback.distance_remaining:.2f} m", end='\r')
                time.sleep(0.5)

        # Cek hasil setelah robot berhenti
        result = navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            # print(f"\n[SUKSES] AMR telah tiba di Stasiun {titik_tujuan}!")
            # print("Berhenti sejenak memindai area selama 5 detik...")
            print(f"\nArrived at Station {titik_tujuan}")
            time.sleep(5.0) # Simulasi robot berhenti bongkar muat sambil SLAM merapikan peta
        elif result == TaskResult.CANCELED:
            # print(f"\n[DIBATALKAN] Misi ke {titik_tujuan} dibatalkan.")
            print("\nMission Canceled")
            break
        elif result == TaskResult.FAILED:
            # print(f"\n[GAGAL] AMR tidak bisa mencapai Stasiun {titik_tujuan}. Jalur buntu!")
            print("\nMission Failed")
            break

    # print("\n[SELESAI] Semua misi rute telah dikerjakan! Peta siap di-save.")
    print("\nMission Completed")
    
    # Tutup node
    rclpy.shutdown()

if __name__ == '__main__':
    main()