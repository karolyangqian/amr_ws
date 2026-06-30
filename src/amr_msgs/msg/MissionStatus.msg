std_msgs/Header header

# State constants
uint8 IDLE       = 0
uint8 NAVIGATING = 1
uint8 ARRIVED    = 2
uint8 COMPLETED  = 3
uint8 FAILED     = 4

uint8  state             # State misi saat ini (gunakan konstanta di atas)
string current_station   # Stasiun yang sedang/terakhir dituju
string[] remaining       # Stasiun yang belum dikunjungi
uint8  stations_done     # Berapa stasiun sudah selesai
string message           # Pesan error atau info tambahan
