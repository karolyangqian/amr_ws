std_msgs/Header header

# Mode constants
uint8 MODE_IDLE      = 0
uint8 MODE_MANUAL    = 1
uint8 MODE_AUTO      = 2
uint8 MODE_EMERGENCY = 3

# Error code constants
uint8 ERROR_NONE  = 0
uint8 ERROR_MOTOR = 1
uint8 ERROR_LIDAR = 2
uint8 ERROR_IMU   = 3
uint8 ERROR_NAV   = 4

uint8   mode              # Mode robot saat ini
uint8   error_code        # Kode error aktif
float32 battery_percent   # Persentase baterai (0.0 – 100.0)
float32 battery_voltage   # Tegangan baterai (Volt)
bool    is_charging       # Sedang di-charge?
string  status_message    # Pesan status bebas / keterangan error
