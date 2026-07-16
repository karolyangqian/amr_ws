import minimalmodbus
import time
import keyboard

# ==========================================
# KONFIGURASI AMR & MODBUS
# ==========================================
RS485_PORT   = 'COM14'      # Port USB TTL to RS485
SLAVE_ADDR   = 1
 
# Modbus Registers (ZLAC8015D)
OPR_MODE_REG = 0x200D
CTRL_REG     = 0x200E 
CMD_RPM_REG  = 0x2088       # Address awal untuk Left & Right CMD

# Parameter Kecepatan WASD
BASE_RPM     = 4.7       # Kecepatan saat tombol ditekan (Ubah jika kurang cepat/terlalu cepat)

# ==========================================
# INISIALISASI MODBUS
# ==========================================
print("[INFO] Menginisialisasi Modbus...")
try:
    driver = minimalmodbus.Instrument(RS485_PORT, SLAVE_ADDR)
    driver.serial.baudrate = 115200
    driver.serial.timeout  = 0.1
    driver.mode = minimalmodbus.MODE_RTU
    
    # Set Mode ke Velocity (3) & Enable Motor (8)
    driver.write_register(OPR_MODE_REG, 3, functioncode=6)
    driver.write_register(CTRL_REG, 8, functioncode=6)
    print(f"[OK] Driver ZLAC8015D Terhubung di {RS485_PORT}")
except Exception as e:
    print(f"[ERROR] Gagal inisialisasi Modbus: {e}")
    exit()

# ==========================================
# KONTROL WASD TELEOP
# ==========================================
print("\n==========================================")
print("[INFO] Mode Teleop WASD Aktif!")
print("Tekan dan tahan tombol berikut:")
print(" [W] -> Maju")
print(" [S] -> Mundur")
print(" [A] -> Belok Kiri (Pivot)")
print(" [D] -> Belok Kanan (Pivot)")
print(" [Q] -> Keluar dari program dan hentikan motor")
print("==========================================\n")

try:
    while True:
        left_rpm = 0.0
        right_rpm = 0.0
        
        # Cek tombol apa yang sedang ditekan
        if keyboard.is_pressed('w'):
            left_rpm = BASE_RPM
            right_rpm = BASE_RPM
        elif keyboard.is_pressed('s'):
            left_rpm = -BASE_RPM
            right_rpm = -BASE_RPM
        elif keyboard.is_pressed('a'):
            left_rpm = -BASE_RPM   # Roda kiri mundur
            right_rpm = BASE_RPM   # Roda kanan maju (Robot muter ke kiri)
        elif keyboard.is_pressed('d'):
            left_rpm = BASE_RPM    # Roda kiri maju
            right_rpm = -BASE_RPM  # Roda kanan mundur (Robot muter ke kanan)
        elif keyboard.is_pressed('q'):
            print("[INFO] Keluar dari program...")
            break
            
        # Siapkan data RPM untuk dikirim (Driver ZLAC membaca format 0.1 RPM)
        left_cmd = int(left_rpm * 10)
        right_cmd = int(-right_rpm * 10) # Roda kanan di-reverse sesuai setup perangkatmu
        
        # Konversi ke 16-bit Two's Complement agar tidak error saat kirim nilai negatif
        left_cmd_modbus = left_cmd & 0xFFFF
        right_cmd_modbus = right_cmd & 0xFFFF
        
        # Berikan perintah ke motor
        driver.write_registers(CMD_RPM_REG, [left_cmd_modbus, right_cmd_modbus])
        
        # Jeda sedikit agar CPU tidak 100% dan pengiriman data serial stabil
        time.sleep(0.05)

except Exception as e:
    print(f"[ERROR] Terjadi kesalahan saat loop kontrol: {e}")

finally:
    # 4. Pastikan motor BERHENTI setelah test selesai atau jika program dihentikan
    try:
        driver.write_registers(CMD_RPM_REG, [0 & 0xFFFF, 0 & 0xFFFF])
        print("[OK] Motor berhasil dihentikan.")
    except:
        print("[WARN] Gagal mengirim perintah stop ke motor!")