#!/usr/bin/env python3
import sys
import time

# Memasukkan path library bawaan amr_hardware
sys.path.append('/home/rein/Documents/amr_ws-main/src/amr_hardware')
from amr_hardware.zlac8015d.ZLAC8015D import Controller

def main():
    # GANTI PORT INI SESUAI DENGAN PORT USB RS485 KAMU!
    # Biasanya /dev/ttyUSB0, /dev/ttyUSB1, atau /dev/ttyUSB2
    PORT = "/dev/ttyUSB0" 
    
    print(f"Mencoba connect ke ZLAC8015D di {PORT}...")
    
    try:
        motor = Controller(port=PORT)
        
        # Inisialisasi awal
        motor.clear_alarm()
        time.sleep(0.3)
        motor.set_accel_time(200, 200)
        motor.set_decel_time(200, 200)
        motor.set_mode(3) # Mode 3 = Kontrol Kecepatan (RPM)
        time.sleep(0.2)
        motor.enable_motor()
        print("✅ Motor berhasil di-enable!")
        
        # 1. WRITE KECEPATAN (Misal kiri 30 RPM, kanan -30 RPM)
        target_rpm_kiri = 30
        target_rpm_kanan = -30
        print(f"\n🚀 Menulis kecepatan: Kiri {target_rpm_kiri} RPM, Kanan {target_rpm_kanan} RPM")
        motor.set_rpm(target_rpm_kiri, target_rpm_kanan)
        
        # 2. BACA KECEPATAN & ENCODER (Looping selama 5 detik)
        print("\n🔍 Membaca feedback motor selama 5 detik:")
        for _ in range(10):
            # Membaca RPM
            l_rpm, r_rpm = motor.get_rpm()
            # Membaca jarak encoder (travelled in meters)
            l_travel, r_travel = motor.get_wheels_travelled()
            
            print(f"RPM -> Kiri: {l_rpm:6.1f} | Kanan: {r_rpm:6.1f}  ||  Jarak -> Kiri: {l_travel:6.3f}m | Kanan: {r_travel:6.3f}m")
            time.sleep(0.5)
            
        # Menghentikan motor
        print("\n🛑 Menghentikan motor...")
        motor.set_rpm(0, 0)
        time.sleep(0.5)
        motor.disable_motor()
        print("Selesai.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Pastikan port USB sudah benar dan sudah di 'sudo chmod 666'.")

if __name__ == '__main__':
    main()
