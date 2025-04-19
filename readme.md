# Video Creator

Ứng dụng tạo video từ ảnh và audio với hiệu ứng zoom, subtitle tự động.

## Tính năng
- Tạo video từ ảnh với hiệu ứng zoom tự động
- Tự động tạo subtitle từ audio bằng Whisper
- Hỗ trợ thêm nhạc nền
- Tùy chỉnh font chữ, màu sắc subtitle
- Tự động lặp video khi audio dài hơn

## Cài đặt

### 1. Clone repository
```bash
git clone https://github.com/cafe2404/nguyennhattruong.git
cd nguyennhattruong
```

### 2. Cài đặt môi trường
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Cài đặt ImageMagick
- Tải từ: https://imagemagick.org/script/download.php
- Chọn "Install legacy utilities" khi cài đặt
- Thêm vào PATH hệ thống

## Sử dụng

### 1. Chuẩn bị dữ liệu
- Tạo thư mục `images/` và đặt ảnh vào
- Tạo thư mục `audios/` và đặt file audio vào
- (Tùy chọn) Sử dụng `background-music.mp3`

### 2. Chạy chương trình
```bash
venv\Scripts\python.exe main.py
```

## Cấu trúc thư mục
nguyennhattruong/
│
├── images/ # Thư mục chứa ảnh
├── audios/ # Thư mục chứa audio
├── ffmpeg/ # FFmpeg (có sẵn)
├── output/ # Video đầu ra
│
├── main.py
├── video_processor.py
├── audio_processor.py
├── config.ini
├── background-music.mp3
└── requirements.txt
```

## Xử lý lỗi thường gặp

### 1. Lỗi ImageMagick
```
MoviePy Error: creation of None failed
```
➜ Kiểm tra cài đặt ImageMagick và PATH

### 2. Lỗi không tìm thấy file
```
FileNotFoundError: Không tìm thấy file
```
➜ Kiểm tra thư mục `images/` và `audios/`

### 3. Lỗi Whisper
```
Lỗi khi tạo subtitle
```
➜ Kiểm tra cài đặt whisper và kết nối mạng

## Yêu cầu hệ thống
- Windows 10/11
- Python 3.8+
- RAM: 8GB+
- Dung lượng trống: >2GB

## License
MIT License