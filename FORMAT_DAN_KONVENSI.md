# STRUKTUR DIREKTORI, FORMAT, DAN KONVENSI

## Struktur Direktori SRC
```
./src
├── bringup         # Bringup launch (`launch/`) dan yaml params final robot (`config/<nama_subsistem>/`)
├── client          # Protokol komunikasi jaringan untuk telemetry dan akses robot ke aplikasi Flutter
├── description     # Deskripsi fisik robot (transforms, URDF, STL, dll)
├── drivers         # Packages yang mengelola komunikasi dengan hardware dan preprocessing data hardware
├── interfaces      # .msg, .action, .srv
├── missions        # Konfigurasi misi robot
└── subsystems      # Subsistem robot: lokalisasi, navigasi, SLAM, odom, vision, safety, dll.
```

## Hirarki Direktori
```
./src
├── <folder_kategori_package>
│   └── <nama_package>
```

## Format Penamaan
| Folder Location | Package Name (package.xml) | Example
| --- | --- | --- | 
| `interfaces/` | `<robot>_<domain>_interfaces` | `amr_mission_interfaces` |
| `drivers/` | `<vendor>_<device>_driver` or `<protocol>_bridge` | `teensy_mcu_driver` or `socketcan_bridge` |
| `subsystems/` | `<robot>_<subsystem>` | `amr_navigation` |
| `bringup/` | `<robot>_bringup` | `amr_bringup` |
