# amr_discovery

Service discovery robot AMR di LAN via UDP broadcast/unicast, dipakai app
kontrol (mis. Flutter) untuk menemukan IP + status ringkas semua robot yang
menyala di jaringan yang sama, tanpa perlu tahu IP di awal.

## Cara kerja

1. Client (app) mengirim **UDP broadcast** 1 paket JSON kecil ke subnet
   (mis. `10.42.0.255:41234`).
2. Setiap robot yang menjalankan `discovery_node` menerima broadcast
   tersebut, lalu membalas dengan **UDP unicast** langsung ke IP:port
   pengirim — bukan broadcast balik.
3. Client mengumpulkan semua reply yang masuk dalam sebuah time window
   (mis. 2–3 detik), lalu menampilkannya sebagai daftar robot yang aktif.

Node hanya membalas apa yang sudah tersedia saat itu. Field yang datanya
belum/tidak tersedia (mis. `/robot/status` belum pernah publish, atau data
terakhir sudah basi/stale) dikirim sebagai `null`, bukan angka
karangan — supaya client bisa membedakan "0" beneran vs "tidak diketahui".

Sumber data status diambil dari topic `/robot/status`
(`amr_msgs/msg/RobotStatus`). Jika belum ada pesan masuk sama sekali, atau
pesan terakhir sudah lebih tua dari `status_stale_timeout` (default 10 detik),
semua field status dibalas `null`.

## Payload

### Request (client → broadcast)

```json
{
  "type": "AMR_DISCOVER",
  "nonce": "optional-string-bebas"
}
```

- `type` **wajib** persis `"AMR_DISCOVER"` — selain itu paket diabaikan.
- `nonce` opsional, sekadar di-echo balik di reply supaya client bisa
  mencocokkan reply dengan request mana (berguna kalau kirim broadcast
  berkali-kali beruntun).

### Reply (robot → unicast ke pengirim)

```json
{
  "type": "AMR_DISCOVER_REPLY",
  "schema": 1,
  "nonce": "optional-string-bebas",
  "robot_id": "amr-01",
  "ip": "10.42.0.100",
  "timestamp": 1752716123.45,
  "mode": "AUTO",
  "error_code": "NONE",
  "battery_percent": 30.0,
  "battery_voltage": 39.5,
  "battery_voltage_max": 43.8,
  "is_charging": false,
  "status_message": "OK"
}
```

| Field | Tipe | Keterangan |
|---|---|---|
| `type` | string | selalu `"AMR_DISCOVER_REPLY"` |
| `schema` | int | versi bentuk payload ini (saat ini `1`), naikkan kalau ada breaking change |
| `nonce` | string \| null | echo dari request |
| `robot_id` | string | dari parameter `robot_id`, fallback ke hostname kalau kosong |
| `ip` | string \| null | IP LAN robot hasil auto-detect; `null` kalau gagal deteksi |
| `timestamp` | float | unix timestamp (detik) saat reply dibuat |
| `mode` | string \| null | `IDLE` / `MANUAL` / `AUTO` / `EMERGENCY`, `null` kalau status belum ada |
| `error_code` | string \| null | `NONE` / `MOTOR` / `LIDAR` / `IMU` / `NAV`, `null` kalau status belum ada |
| `battery_percent` | float \| null | `null` kalau sensor belum tersedia (sentinel `-1` di `RobotStatus` diterjemahkan jadi `null`) |
| `battery_voltage` | float \| null | idem |
| `battery_voltage_max` | float \| null | dari parameter `battery_voltage_max`; `null` kalau belum dikonfigurasi |
| `is_charging` | bool \| null | `null` kalau status belum ada |
| `status_message` | string \| null | `null` kalau kosong atau status belum ada |

## Menjalankan di robot

```bash
ros2 launch amr_discovery discovery.launch.py robot_id:=amr-01
```

Parameter yang bisa di-override: `robot_id`, `port` (default `41234`),
`status_topic` (default `/robot/status`), `battery_voltage_max`,
`status_stale_timeout`.

## Test cepat sebagai client (tanpa app)

Broadcast dari mesin manapun di subnet yang sama:

```bash
python3 - <<'EOF'
import json, socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(2.0)

req = json.dumps({"type": "AMR_DISCOVER", "nonce": "test"}).encode()
sock.sendto(req, ("255.255.255.255", 41234))

try:
    while True:
        data, addr = sock.recvfrom(2048)
        print(addr, json.loads(data))
except socket.timeout:
    pass
EOF
```

Kalau `255.255.255.255` diblokir router, ganti ke broadcast address subnet
lokal (mis. `10.42.0.255`).
